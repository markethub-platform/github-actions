#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Review to GitHub Issues Converter - Enhanced with Fingerprinting
Prevents duplicates using:
- Issue fingerprints (file + problem pattern)
- Fuzzy title matching
- Historical tracking (reopens closed issues)
"""
import re
import sys
import os
import requests
import json
import hashlib
from difflib import SequenceMatcher
from datetime import datetime

# ============================================
# ISSUE FINGERPRINTING
# ============================================

def extract_problem_pattern(current_code, suggested_fix):
    """
    Extract the core problem pattern from code snippets with weighted priorities
    Returns a normalized pattern string for fingerprinting
    """
    if not current_code:
        return ""
    
    # Normalize code: remove whitespace, comments, lowercase
    pattern = current_code.lower()
    pattern = re.sub(r'//.*?\n', '', pattern)
    pattern = re.sub(r'/\*.*?\*/', '', pattern, flags=re.DOTALL)
    pattern = re.sub(r'\s+', ' ', pattern)
    pattern = pattern.strip()
    
    # Extract patterns by priority
    key_patterns = []
    
    # HIGH PRIORITY: React hooks
    hooks = re.findall(r'use\w+\s*\(', pattern)
    if hooks:
        key_patterns.extend([f"HOOK:{h}" for h in sorted(set(hooks))])
    
    # HIGH PRIORITY: Critical browser APIs
    critical_apis = re.findall(
        r'(window\.|document\.|addEventListener|removeEventListener|setInterval|clearInterval|setTimeout|clearTimeout|AbortController)\s*[\(\.]',
        pattern
    )
    if critical_apis:
        key_patterns.extend([f"API:{api}" for api in sorted(set(critical_apis))[:5]])
    
    # MEDIUM PRIORITY: Async patterns
    async_patterns = re.findall(
        r'(async|await|fetch|axios|promise|\.then|\.catch)\s*[\(\.]',
        pattern,
        re.IGNORECASE
    )
    if async_patterns:
        key_patterns.extend([f"ASYNC:{ap}" for ap in sorted(set(async_patterns))[:3]])
    
    # MEDIUM PRIORITY: State management
    state_patterns = re.findall(
        r'(useState|useReducer|useContext|state\.|setState)\s*[\(\.]',
        pattern
    )
    if state_patterns:
        key_patterns.extend([f"STATE:{sp}" for sp in sorted(set(state_patterns))[:3]])
    
    # LOW PRIORITY: General function calls
    if len(key_patterns) < 3:
        functions = re.findall(r'\w+\s*\(', pattern)
        key_patterns.extend([f"FN:{fn}" for fn in sorted(set(functions))[:3]])
    
    # LOW PRIORITY: Variable assignments
    if len(key_patterns) < 5:
        assignments = re.findall(r'(const|let|var)\s+\w+\s*=', pattern)
        key_patterns.extend([f"VAR:{a}" for a in sorted(set(assignments))[:2]])
    
    return '|'.join(key_patterns[:10])

def categorize_issue(issue_title, problem_description, code):
    """
    Categorize the issue type for better matching
    Enhanced with aliases for better detection
    """
    combined_text = f"{issue_title} {problem_description} {code}".lower()
    
    categories = {
        'memory-leak': [
            'memory leak', 'missing cleanup', 'cleanup in useeffect', 'effect cleanup',
            'remove event listener', 'clearinterval', 'cleartimeout',
            'unsubscribe', 'abort controller', 'cleanup function',
            'listener not removed', 'timer not cleared', 'subscription leak'
        ],
        'type-error': [
            'type error', 'typescript', 'any type', 'type safety',
            'missing type', 'implicit any', 'type annotation',
            'type definition', 'interface', 'type assertion'
        ],
        'security': [
            'xss', 'injection', 'sql injection', 'security vulnerability',
            'csrf', 'authentication', 'authorization', 'sanitize',
            'escape', 'validation', 'untrusted input', 'security risk'
        ],
        'performance': [
            'performance', 'unnecessary re-render', 'usememo', 'usecallback',
            'react.memo', 'optimization', 'bundle size', 'slow',
            'inefficient', 'expensive operation', 'render optimization'
        ],
        'race-condition': [
            'race condition', 'async', 'promise', 'concurrent',
            'timing issue', 'synchronization', 'async timing',
            'parallel execution', 'concurrency', 'race'
        ],
        'infinite-loop': [
            'infinite loop', 'infinite redirect', 'recursion',
            'dependency array', 'useeffect loop', 'endless loop',
            'circular dependency', 'infinite recursion'
        ],
        'error-handling': [
            'error handling', 'try catch', 'error boundary',
            'exception', 'validation', 'error check',
            'missing error', 'unhandled error', 'catch block'
        ],
        'api-usage': [
            'api', 'fetch', 'axios', 'http', 'request',
            'endpoint', 'rest', 'graphql', 'api call',
            'network request', 'http client'
        ]
    }
    
    category_scores = {}
    for category, keywords in categories.items():
        score = sum(1 for keyword in keywords if keyword in combined_text)
        if score > 0:
            category_scores[category] = score
    
    if category_scores:
        return max(category_scores, key=category_scores.get)
    
    return 'general'

def generate_issue_fingerprint(file_path, issue_title, problem, current_code, suggested_fix):
    """
    Generate unique fingerprint for an issue
    """
    normalized_file = re.sub(r':\d+', '', file_path)
    problem_pattern = extract_problem_pattern(current_code, suggested_fix)
    category = categorize_issue(issue_title, problem, current_code)
    normalized_title = normalize_title(issue_title)
    
    components = [
        normalized_file,
        category,
        problem_pattern[:100],
        normalized_title[:50]
    ]
    
    fingerprint_str = '|'.join(components)
    fingerprint = hashlib.sha256(fingerprint_str.encode()).hexdigest()[:12]
    simple_id = hashlib.md5(f"{file_path}:{issue_title}".encode()).hexdigest()[:8]
    
    return {
        'fingerprint': fingerprint,
        'simple_id': simple_id,
        'category': category,
        'pattern': problem_pattern,
        'file': normalized_file
    }

# ============================================
# FUZZY MATCHING
# ============================================

def normalize_title(title):
    """Normalize title for comparison"""
    title = re.sub(r'^\[AI\]\s*🔴\s*', '', title)
    title = title.lower()
    title = re.sub(r'[^\w\s-]', '', title)
    return ' '.join(title.split())

def titles_are_similar(title1, title2, threshold=0.85, same_context=False):
    """Check if two titles are similar"""
    norm1 = normalize_title(title1)
    norm2 = normalize_title(title2)
    
    if not norm1 or not norm2:
        return False
    
    effective_threshold = 0.75 if same_context else threshold
    similarity = SequenceMatcher(None, norm1, norm2).ratio()
    
    return similarity >= effective_threshold

# ============================================
# ISSUE SEARCHING
# ============================================

def get_all_ai_issues(repo, token, limit=200):
    """Get all AI review issues (open and closed)"""
    all_issues = []
    
    for state in ["open", "closed"]:
        url = f"https://api.github.com/repos/{repo}/issues"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        params = {
            "state": state,
            "labels": "ai-review",
            "per_page": 100,
            "sort": "updated",
            "direction": "desc"
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            issues = response.json()
            all_issues.extend(issues)
            
            if len(all_issues) >= limit:
                break
                
        except Exception as e:
            print(f"Warning: Error fetching {state} issues: {e}")
    
    return all_issues[:limit]

def extract_issue_metadata(issue):
    """Extract metadata from existing issue"""
    body = issue.get('body', '')
    
    simple_id_match = re.search(r'AI-ID:\s*(\w+)', body)
    simple_id = simple_id_match.group(1) if simple_id_match else None
    
    fingerprint_match = re.search(r'FINGERPRINT:\s*(\w+)', body)
    fingerprint = fingerprint_match.group(1) if fingerprint_match else None
    
    file_match = re.search(r'\*\*File:\*\*\s*`([^`]+)`', body)
    file_path = file_match.group(1) if file_match else ''
    
    category_match = re.search(r'CATEGORY:\s*(\w+[-\w]*)', body)
    category = category_match.group(1) if category_match else 'general'
    
    reopen_match = re.search(r'Reopened:\s*(\d+)\s*times', body)
    reopen_count = int(reopen_match.group(1)) if reopen_match else 0
    
    return {
        'number': issue['number'],
        'title': issue['title'],
        'state': issue['state'],
        'simple_id': simple_id,
        'fingerprint': fingerprint,
        'file_path': file_path,
        'category': category,
        'body': body,
        'created_at': issue.get('created_at'),
        'closed_at': issue.get('closed_at'),
        'labels': [label['name'] for label in issue.get('labels', [])],
        'reopen_count': reopen_count
    }

def find_matching_issue(all_issues, new_issue_data):
    """
    Find matching issue using multiple strategies
    """
    new_fp = new_issue_data['fingerprint_data']
    
    exact_match = None
    simple_match = None
    fuzzy_matches = []
    
    for issue in all_issues:
        metadata = extract_issue_metadata(issue)
        
        # Strategy 1: Exact fingerprint match
        if metadata['fingerprint'] and metadata['fingerprint'] == new_fp['fingerprint']:
            exact_match = metadata
            break
        
        # Strategy 2: Simple ID match
        if metadata['simple_id'] and metadata['simple_id'] == new_fp['simple_id']:
            simple_match = metadata
        
        # Strategy 3: Fuzzy match
        same_context = (metadata['file_path'] == new_fp['file'] and 
                       metadata['category'] == new_fp['category'])
        
        if (metadata['file_path'] == new_fp['file'] and
            metadata['category'] == new_fp['category'] and
            titles_are_similar(metadata['title'], new_issue_data['title'], 
                             threshold=0.85, same_context=same_context)):
            fuzzy_matches.append(metadata)
    
    if exact_match:
        return exact_match, 'exact'
    elif simple_match:
        return simple_match, 'simple'
    elif fuzzy_matches:
        fuzzy_matches.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return fuzzy_matches[0], 'fuzzy'
    
    return None, None

# ============================================
# ISSUE MANAGEMENT
# ============================================

def add_comment(repo, token, issue_number, comment_body):
    """Add a comment to an issue"""
    url = f"https://api.github.com/repos/{repo}/issues/{issue_number}/comments"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    data = {"body": comment_body}
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Warning: Failed to comment on issue #{issue_number}: {e}")
        return False

def remove_label(repo, token, issue_number, label):
    """Remove a label from an issue"""
    encoded_label = requests.utils.quote(label)
    url = f"https://api.github.com/repos/{repo}/issues/{issue_number}/labels/{encoded_label}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        response = requests.delete(url, headers=headers)
        if response.status_code not in [200, 204, 404]:
            response.raise_for_status()
        return True
    except Exception as e:
        print(f"Warning: Failed to remove label {label}: {e}")
        return False

def add_label(repo, token, issue_number, label):
    """Add a label to an issue"""
    url = f"https://api.github.com/repos/{repo}/issues/{issue_number}/labels"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        response = requests.post(url, headers=headers, json={"labels": [label]})
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Warning: Failed to add label {label}: {e}")
        return False

def reopen_issue(repo, token, existing_issue, match_type, pr_number):
    """Reopen a closed issue when problem reappears"""
    issue_number = existing_issue['number']
    url = f"https://api.github.com/repos/{repo}/issues/{issue_number}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    reopen_count = existing_issue.get('reopen_count', 0) + 1
    
    try:
        response = requests.patch(url, headers=headers, json={"state": "open"})
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to reopen issue #{issue_number}: {e}")
        return False
    
    for label in ["ai-not-seen-1x", "ai-not-seen-2x", "ai-not-seen-3x"]:
        remove_label(repo, token, issue_number, label)
    
    if reopen_count >= 3 and "recurring" not in existing_issue.get('labels', []):
        add_label(repo, token, issue_number, "recurring")
        print(f"   Flagged as recurring (reopened {reopen_count}x)")
    
    match_explanations = {
        'exact': 'exact code fingerprint match',
        'simple': 'issue ID match',
        'fuzzy': 'similar title and code pattern'
    }
    match_explanation = match_explanations.get(match_type, 'pattern match')
    
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    
    if reopen_count >= 3:
        severity_warning = f"""
### ⚠️ **RECURRING ISSUE - {reopen_count}x DETECTION**

This issue has been **reopened {reopen_count} times**, indicating a **recurring problem** that requires deeper investigation.

**Recommended Actions:**
1. **Root Cause Analysis:** Don't just fix symptoms, find the underlying cause
2. **Code Review:** Review recent changes that might reintroduce this pattern
3. **Architectural Review:** Consider if code structure encourages this bug
4. **Tests:** Add regression tests to prevent future reoccurrences
5. **Team Discussion:** Discuss with team why this keeps coming back
"""
    elif reopen_count == 2:
        severity_warning = f"""
### ⚠️ Second Detection

This is the **second time** this issue has been reopened. If it occurs again (3+ times), it will be flagged as **recurring** and may need architectural changes.
"""
    else:
        severity_warning = ""
    
    comment = f"""## 🔄 Issue Automatically Reopened ({reopen_count}x)

**Detected:** {timestamp}  
**Match Type:** {match_explanation.title()}  
**Reopen Count:** This issue has been reopened **{reopen_count} time(s)**  
**Context:** PR #{pr_number if pr_number else 'Push to main'}

**Reopened:** {reopen_count} times

---
{severity_warning}

### 📊 What Happened

This issue was previously resolved and closed after 3 confirmations. However, the **same problem pattern has been re-detected** in the codebase.

### 🔍 Detection Method

The AI code review system identified this issue using **{match_explanation}**, indicating:
- Same file location
- Same problem category
- Similar or identical code pattern

### 🤔 Possible Causes

1. **Code Regression:** Recent changes reintroduced the bug
2. **Refactoring:** Code was restructured and issue came back
3. **Copy-Paste:** Pattern repeated in same file
4. **Incomplete Fix:** Original fix didn't address root cause
5. **Conflicting Changes:** Parallel work overwrote the fix

### ✅ Next Steps

1. **Review Original Fix:** Check what was done before (see issue history)
2. **Analyze Recent Changes:** Review commits since last closure
3. **Implement Comprehensive Fix:** Address root cause, not just symptoms
4. **Add Tests:** Prevent future regressions
5. **Verify:** Commit changes and AI will re-verify
6. **Auto-Close:** Issue closes automatically after 3 confirmations

### 📈 Tracking

**Verification Counter:** Reset to 0/3  
**Status:** Waiting for fix  
**Auto-closes:** After 3 consecutive clean reviews  
**History:** Reopened {reopen_count} time(s)

---
*Automated reopening by AI code review fingerprint system*  
*Reopen tracking helps identify recurring issues that need deeper fixes*"""
    
    add_comment(repo, token, issue_number, comment)
    
    print(f"Reopened issue #{issue_number} (match: {match_type}, count: {reopen_count}x)")
    
    return True

def create_new_issue(repo, token, issue_data, pr_number):
    """Create a brand new GitHub issue"""
    url = f"https://api.github.com/repos/{repo}/issues"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    fp = issue_data['fingerprint_data']
    
    body = f"""## 🤖 AI-Detected Critical Issue

**File:** `{issue_data['file_path']}`  
**Category:** {fp['category'].replace('-', ' ').title()}

---

### 🔴 Problem Description

{issue_data['problem']}
"""
    
    if issue_data['current_code']:
        body += f"""
### 📄 Current Code
```typescript
{issue_data['current_code']}
```
"""
    
    if issue_data['suggested_fix']:
        body += f"""
### ✅ Suggested Fix
```typescript
{issue_data['suggested_fix']}
```
"""
    
    if issue_data['reasoning']:
        body += f"""
### 💡 Why This Matters

{issue_data['reasoning']}
"""
    
    body += f"""

---

### 📊 Issue Metadata

**Detection Info:**
- 🤖 **Detected by:** AI Code Review (Claude Sonnet 4.5)
- 🔴 **Severity:** Critical
- 📁 **Category:** `{fp['category']}`
- 🔍 **Pattern:** `{fp['pattern'][:50]}...` 

**Tracking IDs:**
- 🆔 **AI-ID:** `{fp['simple_id']}`
- 🔐 **FINGERPRINT:** `{fp['fingerprint']}`
- 📂 **CATEGORY:** `{fp['category']}`
"""
    
    if pr_number:
        body += f"\n- 📋 **Related PR:** #{pr_number}"
    
    body += """

---

### 🎯 Resolution Process

**Current Status:** ⏳ Waiting for fix  
**Verification:** 🔍 AI will auto-verify when fixed  
**Auto-close:** ✅ After 3 consecutive confirmations

**Your Action Items:**
1. Review the suggested fix above
2. Implement the solution in your code
3. Commit and push your changes
4. AI will automatically:
   - Re-review the code
   - Track fix confirmation (1/3, 2/3, 3/3)
   - Auto-close when verified

**If Issue Persists:**
- Counter resets to 0/3 if issue re-detected
- Ensures real fix before closing

---

### 🏷️ Issue Fingerprinting

This issue uses **advanced fingerprinting** to prevent duplicates:
- Tracks code patterns, not just titles
- Reopens closed issues if problem returns
- Links related issues across time

---

**Reopened:** 0 times

*This issue was automatically created by AI code review with fingerprint-based duplicate prevention*"""
    
    payload = {
        'title': issue_data['title'],
        'body': body,
        'labels': issue_data['labels']
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        issue = response.json()
        print(f"Created NEW issue #{issue['number']}: {issue_data['title']}")
        return issue['number']
    except Exception as e:
        print(f"Failed to create issue: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"   Response: {e.response.text}")
        return None

def handle_existing_open_issue(repo, token, existing_issue, pr_number):
    """Add comment to existing open issue"""
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    
    comment = f"""## 🔄 Issue Still Present

**Re-detected:** {timestamp}  
**Context:** PR #{pr_number if pr_number else 'Push to main'}

---

This issue is **still present** in the latest code review.

### 📊 Status

**Current State:** Open (not yet fixed)  
**Detection Count:** Multiple detections  
**Verification:** Counter reset (if was tracking)

### 💡 Recommended Actions

1. **Prioritize This Fix:** Issue detected multiple times
2. **Review Suggested Solution:** See original issue description above
3. **Implement Fix:** Apply the recommended changes
4. **Test Thoroughly:** Ensure fix addresses root cause
5. **Commit & Push:** AI will verify on next review

---
*Automated detection by AI code review system*"""
    
    for label in ["ai-not-seen-1x", "ai-not-seen-2x"]:
        remove_label(repo, token, existing_issue['number'], label)
    
    add_comment(repo, token, existing_issue['number'], comment)
    print(f"Issue #{existing_issue['number']} still open - added update comment")
    return existing_issue['number']

# ============================================
# MAIN PROCESSING
# ============================================

def parse_ai_review(review_text):
    """Parse AI review and extract critical issues"""
    issues = []
    
    critical_pattern = r'\*\*🔴 CRITICAL:\s*([^\*\n]+)\*\*'
    sections = review_text.split('## File:')
    
    for section in sections[1:]:
        file_match = re.search(r'`([^`]+)`', section)
        if not file_match:
            continue
        file_path = file_match.group(1)
        
        for match in re.finditer(critical_pattern, section, re.IGNORECASE):
            issue_title = match.group(1).strip()
            
            start_pos = match.start()
            next_issue = section.find('**🔴', start_pos + 10)
            next_perf = section.find('**🟡', start_pos)
            next_enhance = section.find('**🔵', start_pos)
            next_file = len(section)
            
            end_pos = min([p for p in [next_issue, next_perf, next_enhance, next_file] if p > start_pos])
            issue_block = section[start_pos:end_pos].strip()
            
            problem_match = re.search(r'\*\*Problem:\*\*\s*([^\n]+)', issue_block)
            problem = problem_match.group(1).strip() if problem_match else 'See AI review for details'
            
            current_code = ''
            current_match = re.search(r'\*\*Current Code:\*\*\s*```[\w]*\n(.*?)```', issue_block, re.DOTALL)
            if current_match:
                current_code = current_match.group(1).strip()
            
            suggested_fix = ''
            fix_match = re.search(r'\*\*(?:Suggested Fix|Fix):\*\*\s*```[\w]*\n(.*?)```', issue_block, re.DOTALL)
            if fix_match:
                suggested_fix = fix_match.group(1).strip()
            
            why_match = re.search(r'\*\*Why:\*\*\s*([^\n]+)', issue_block)
            reasoning = why_match.group(1).strip() if why_match else ''
            
            fingerprint_data = generate_issue_fingerprint(
                file_path, issue_title, problem, current_code, suggested_fix
            )
            
            labels = ['ai-review', 'critical', 'bug', fingerprint_data['category']]
            if 'frontend' in file_path or any(ext in file_path for ext in ['.tsx', '.jsx', '.ts', '.js']):
                labels.append('frontend')
            if 'component' in file_path.lower():
                labels.append('component')
            if 'api' in file_path.lower() or 'service' in file_path.lower():
                labels.append('api')
            if 'hook' in file_path.lower():
                labels.append('hooks')
            
            issues.append({
                'title': f"[AI] 🔴 {issue_title}",
                'file_path': file_path,
                'problem': problem,
                'current_code': current_code,
                'suggested_fix': suggested_fix,
                'reasoning': reasoning,
                'labels': list(set(labels)),
                'fingerprint_data': fingerprint_data
            })
    
    return issues

def main(review_file, pr_number):
    """Main function with advanced duplicate prevention"""
    try:
        with open(review_file, 'r', encoding='utf-8') as f:
            review_text = f.read()
    except FileNotFoundError:
        print(f"Review file not found: {review_file}")
        return
    
    if not review_text.strip():
        print("No review content found")
        return
    
    print("Parsing AI review for critical issues...")
    new_issues = parse_ai_review(review_text)
    
    if not new_issues:
        print("No critical issues found! Code looks good.")
        return
    
    print(f"Found {len(new_issues)} critical issue(s) in review")
    
    repo = os.getenv("GITHUB_REPOSITORY")
    token = os.getenv("GITHUB_TOKEN")
    
    if not repo or not token:
        print("Missing GitHub repository or token")
        print("\nIssues that would be created:")
        for i, issue in enumerate(new_issues, 1):
            fp = issue['fingerprint_data']
            print(f"\n{i}. {issue['title']}")
            print(f"   File: {issue['file_path']}")
            print(f"   Category: {fp['category']}")
            print(f"   Fingerprint: {fp['fingerprint']}")
        return
    
    print("\nFetching existing AI issues (open and closed)...")
    all_existing_issues = get_all_ai_issues(repo, token, limit=200)
    print(f"Found {len(all_existing_issues)} existing AI issue(s)")
    
    created_count = 0
    reopened_count = 0
    updated_count = 0
    
    print("\n" + "="*70)
    print("PROCESSING ISSUES WITH FINGERPRINT MATCHING")
    print("="*70)
    
    for idx, issue_data in enumerate(new_issues, 1):
        print(f"\n[{idx}/{len(new_issues)}] Processing: {issue_data['title']}")
        print(f"   File: {issue_data['file_path']}")
        print(f"   Category: {issue_data['fingerprint_data']['category']}")
        
        existing, match_type = find_matching_issue(all_existing_issues, issue_data)
        
        if existing:
            print(f"   Match found: #{existing['number']} (type: {match_type})")
            
            if existing['state'] == 'open':
                handle_existing_open_issue(repo, token, existing, pr_number)
                updated_count += 1
            else:
                reopen_issue(repo, token, existing, match_type, pr_number)
                reopened_count += 1
        else:
            print("   No match found - creating new issue")
            issue_num = create_new_issue(repo, token, issue_data, pr_number)
            if issue_num:
                created_count += 1
    
    print("\n" + "="*70)
    print("PROCESSING SUMMARY")
    print("="*70)
    print(f"   New issues created: {created_count}")
    print(f"   Closed issues reopened: {reopened_count}")
    print(f"   Open issues updated: {updated_count}")
    print(f"   Total processed: {len(new_issues)}")
    print("="*70)
    
    if created_count > 0:
        print(f"\nCreated {created_count} new issue(s)")
    if reopened_count > 0:
        print(f"\nReopened {reopened_count} previously closed issue(s)")
    if updated_count > 0:
        print(f"\nUpdated {updated_count} existing open issue(s)")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python ai_review_to_issues.py <review_file> <pr_number>")
        sys.exit(1)
    
    review_file = sys.argv[1]
    pr_number = sys.argv[2]
    main(review_file, pr_number)