#!/usr/bin/env python3#!/usr/bin/env python3

""""""

AI Review to GitHub Issues Converter - Enhanced with Advanced FingerprintingAI Review to GitHub Issues Converter

Prevents duplicates using:Parses AI review and creates GitHub issues for critical findings

- Issue fingerprints (file + problem pattern)"""

- Fuzzy title matching with tiered thresholdsimport re

- Historical tracking (reopens closed issues)import sys

- Recurring issue detectionimport os

"""import requests

import reimport json

import sysimport hashlib

import os

import requestsdef generate_issue_id(file_path, issue_title):

import json    """Generate unique ID for issue to prevent duplicates"""

import hashlib    content = f"{file_path}:{issue_title}"

from difflib import SequenceMatcher    return hashlib.md5(content.encode()).hexdigest()[:8]

from datetime import datetime

def parse_ai_review(review_text):

# ============================================    """

# ISSUE FINGERPRINTING    Parse AI review text and extract critical issues

# ============================================    Returns list of issues with metadata

    """

def extract_problem_pattern(current_code, suggested_fix):    issues = []

    """    

    Extract the core problem pattern from code snippets with weighted priorities    # Pattern to match critical issues: **🔴 CRITICAL: Title**

    Returns a normalized pattern string for fingerprinting    critical_pattern = r'\*\*🔴 CRITICAL:\s*([^\*\n]+)\*\*'

    """    

    if not current_code:    # Split review into file sections

        return ""    sections = review_text.split('## File:')

        

    # Normalize code: remove whitespace, comments, lowercase    for section in sections[1:]:  # Skip first empty section

    pattern = current_code.lower()        # Extract file path

    pattern = re.sub(r'//.*?\n', '', pattern)  # Remove single-line comments        file_match = re.search(r'`([^`]+)`', section)

    pattern = re.sub(r'/\*.*?\*/', '', pattern, flags=re.DOTALL)  # Remove multi-line comments        if not file_match:

    pattern = re.sub(r'\s+', ' ', pattern)  # Normalize whitespace            continue

    pattern = pattern.strip()        file_path = file_match.group(1)

            

    # Extract patterns by priority (more stable indicators of the issue)        # Find all critical issues in this file

    key_patterns = []        for match in re.finditer(critical_pattern, section, re.IGNORECASE):

                issue_title = match.group(1).strip()

    # HIGH PRIORITY: React hooks (most stable, issue-defining patterns)            

    hooks = re.findall(r'use\w+\s*\(', pattern)            # Extract the full issue block

    if hooks:            start_pos = match.start()

        key_patterns.extend([f"HOOK:{h}" for h in sorted(set(hooks))])            

                # Find next issue marker or end of section

    # HIGH PRIORITY: Critical browser APIs (memory leak indicators)            next_issue = section.find('**🔴', start_pos + 10)

    critical_apis = re.findall(            next_perf = section.find('**🟡', start_pos)

        r'(window\.|document\.|addeventlistener|removeeventlistener|setinterval|clearinterval|settimeout|cleartimeout|abortcontroller)\s*[\(\.]',            next_enhance = section.find('**🔵', start_pos)

        pattern            next_file = len(section)

    )            

    if critical_apis:            end_pos = min([p for p in [next_issue, next_perf, next_enhance, next_file] if p > start_pos])

        key_patterns.extend([f"API:{api}" for api in sorted(set(critical_apis))[:5]])            issue_block = section[start_pos:end_pos].strip()

                

    # MEDIUM PRIORITY: Async patterns (race condition indicators)            # Extract problem description

    async_patterns = re.findall(            problem_match = re.search(r'\*\*Problem:\*\*\s*([^\n]+)', issue_block)

        r'(async|await|fetch|axios|promise|\.then|\.catch)\s*[\(\.]',            problem = problem_match.group(1).strip() if problem_match else 'See AI review for details'

        pattern,            

        re.IGNORECASE            # Extract current code

    )            current_code = ''

    if async_patterns:            current_match = re.search(r'\*\*Current Code:\*\*\s*```[\w]*\n(.*?)```', issue_block, re.DOTALL)

        key_patterns.extend([f"ASYNC:{ap}" for ap in sorted(set(async_patterns))[:3]])            if current_match:

                    current_code = current_match.group(1).strip()

    # MEDIUM PRIORITY: State management            

    state_patterns = re.findall(            # Extract suggested fix

        r'(usestate|usereducer|usecontext|state\.|setstate)\s*[\(\.]',            suggested_fix = ''

        pattern            fix_match = re.search(r'\*\*(?:Suggested Fix|Fix):\*\*\s*```[\w]*\n(.*?)```', issue_block, re.DOTALL)

    )            if fix_match:

    if state_patterns:                suggested_fix = fix_match.group(1).strip()

        key_patterns.extend([f"STATE:{sp}" for sp in sorted(set(state_patterns))[:3]])            

                # Extract reasoning

    # LOW PRIORITY: General function calls (only if nothing else found)            why_match = re.search(r'\*\*Why:\*\*\s*([^\n]+)', issue_block)

    if len(key_patterns) < 3:            reasoning = why_match.group(1).strip() if why_match else ''

        functions = re.findall(r'\w+\s*\(', pattern)            

        key_patterns.extend([f"FN:{fn}" for fn in sorted(set(functions))[:3]])            # Determine labels from file path

                labels = ['ai-review', 'critical', 'bug']

    # LOW PRIORITY: Variable assignments            if 'frontend' in file_path or any(ext in file_path for ext in ['.tsx', '.jsx', '.ts', '.js']):

    if len(key_patterns) < 5:                labels.append('frontend')

        assignments = re.findall(r'(const|let|var)\s+\w+\s*=', pattern)            if 'component' in file_path.lower():

        key_patterns.extend([f"VAR:{a}" for a in sorted(set(assignments))[:2]])                labels.append('component')

                if 'api' in file_path.lower() or 'service' in file_path.lower():

    return '|'.join(key_patterns[:10])  # Max 10 patterns for stable fingerprints                labels.append('api')

            if 'hook' in file_path.lower():

def categorize_issue(issue_title, problem_description, code):                labels.append('hooks')

    """            

    Categorize the issue type for better matching            # Generate unique ID for this issue

    Enhanced with aliases for better detection            issue_id = generate_issue_id(file_path, issue_title)

                

    Returns: category string (e.g., "memory-leak", "type-error", "security")            # Build issue

    """            issues.append({

    combined_text = f"{issue_title} {problem_description} {code}".lower()                'id': issue_id,

                    'title': f"[AI] 🔴 {issue_title}",

    # Define category patterns with aliases                'file_path': file_path,

    categories = {                'problem': problem,

        'memory-leak': [                'current_code': current_code,

            'memory leak', 'missing cleanup', 'cleanup in useeffect', 'effect cleanup',                'suggested_fix': suggested_fix,

            'remove event listener', 'clearinterval', 'cleartimeout',                'reasoning': reasoning,

            'unsubscribe', 'abort controller', 'cleanup function',                'labels': labels

            'listener not removed', 'timer not cleared', 'subscription leak'            })

        ],    

        'type-error': [    return issues

            'type error', 'typescript', 'any type', 'type safety',

            'missing type', 'implicit any', 'type annotation',def find_existing_issue(repo, token, issue_id):

            'type definition', 'interface', 'type assertion'    """Check if issue already exists by searching for unique ID"""

        ],    url = f"https://api.github.com/repos/{repo}/issues"

        'security': [    headers = {

            'xss', 'injection', 'sql injection', 'security vulnerability',        "Authorization": f"Bearer {token}",

            'csrf', 'authentication', 'authorization', 'sanitize',        "Accept": "application/vnd.github.v3+json"

            'escape', 'validation', 'untrusted input', 'security risk'    }

        ],    

        'performance': [    params = {

            'performance', 'unnecessary re-render', 'usememo', 'usecallback',        "state": "open",

            'react.memo', 'optimization', 'bundle size', 'slow',        "labels": "ai-review",

            'inefficient', 'expensive operation', 'render optimization'        "per_page": 100

        ],    }

        'race-condition': [    

            'race condition', 'async', 'promise', 'concurrent',    try:

            'timing issue', 'synchronization', 'async timing',        response = requests.get(url, headers=headers, params=params)

            'parallel execution', 'concurrency', 'race'        response.raise_for_status()

        ],        issues = response.json()

        'infinite-loop': [        

            'infinite loop', 'infinite redirect', 'recursion',        # Check if any issue contains this ID

            'dependency array', 'useeffect loop', 'endless loop',        for issue in issues:

            'circular dependency', 'infinite recursion'            if f"AI-ID: {issue_id}" in issue.get('body', ''):

        ],                return issue['number']

        'error-handling': [        

            'error handling', 'try catch', 'error boundary',        return None

            'exception', 'validation', 'error check',    except Exception as e:

            'missing error', 'unhandled error', 'catch block'        print(f"⚠️ Error checking existing issues: {e}")

        ],        return None

        'api-usage': [

            'api', 'fetch', 'axios', 'http', 'request',def create_github_issue(issue_data, repo, token, pr_number=None):

            'endpoint', 'rest', 'graphql', 'api call',    """Create a GitHub issue"""

            'network request', 'http client'    url = f"https://api.github.com/repos/{repo}/issues"

        ]    headers = {

    }        "Authorization": f"Bearer {token}",

            "Accept": "application/vnd.github.v3+json"

    # Find matching category (with scoring for multiple matches)    }

    category_scores = {}    

    for category, keywords in categories.items():    # Build issue body

        score = sum(1 for keyword in keywords if keyword in combined_text)    body = f"""## 🤖 AI-Detected Critical Issue

        if score > 0:

            category_scores[category] = score**File:** `{issue_data['file_path']}`

    

    # Return category with highest score**Problem:**

    if category_scores:{issue_data['problem']}

        return max(category_scores, key=category_scores.get)"""

        

    return 'general'    if issue_data['current_code']:

        body += f"""

def generate_issue_fingerprint(file_path, issue_title, problem, current_code, suggested_fix):**Current Code:**

    """```typescript

    Generate unique fingerprint for an issue based on:{issue_data['current_code']}

    - File path```

    - Problem category"""

    - Code pattern    

    - Normalized title    if issue_data['suggested_fix']:

    """        body += f"""

    # Normalize file path (remove line numbers, etc.)**Suggested Fix:**

    normalized_file = re.sub(r':\d+', '', file_path)```typescript

    {issue_data['suggested_fix']}

    # Extract problem pattern from code```

    problem_pattern = extract_problem_pattern(current_code, suggested_fix)"""

        

    # Categorize issue    if issue_data['reasoning']:

    category = categorize_issue(issue_title, problem, current_code)        body += f"""

    **Why this matters:**

    # Normalize title{issue_data['reasoning']}

    normalized_title = normalize_title(issue_title)"""

        

    # Create fingerprint components    body += f"""

    components = [

        normalized_file,---

        category,

        problem_pattern[:100],  # First 100 chars of pattern**Context:**

        normalized_title[:50]   # First 50 chars of title- 🤖 Detected by: AI Code Review (Claude Sonnet 4.5)

    ]- 🔴 Severity: Critical

    - 🆔 AI-ID: {issue_data['id']}

    # Generate hash"""

    fingerprint_str = '|'.join(components)    

    fingerprint = hashlib.sha256(fingerprint_str.encode()).hexdigest()[:12]    if pr_number:

            body += f"\n- 📋 Related PR: #{pr_number}"

    # Also create a simple ID for backwards compatibility    

    simple_id = hashlib.md5(f"{file_path}:{issue_title}".encode()).hexdigest()[:8]    body += """

    

    return {**Status:**

        'fingerprint': fingerprint,- ⏳ Waiting for fix

        'simple_id': simple_id,- 🔍 AI will verify when fixed

        'category': category,

        'pattern': problem_pattern,**Next Steps:**

        'file': normalized_file1. Review the suggested fix

    }2. Implement the solution

3. Commit and push your changes

# ============================================4. AI will automatically verify and close this issue if fixed

# FUZZY MATCHING

# ============================================---

*This issue was automatically created from an AI code review and will auto-close when AI verifies the fix.*

def normalize_title(title):"""

    """Normalize title for comparison"""    

    # Remove [AI] prefix and emoji    payload = {

    title = re.sub(r'^\[AI\]\s*🔴\s*', '', title)        'title': issue_data['title'],

    # Lowercase        'body': body,

    title = title.lower()        'labels': issue_data['labels']

    # Remove special chars    }

    title = re.sub(r'[^\w\s-]', '', title)    

    # Normalize whitespace    # Check if issue already exists

    return ' '.join(title.split())    existing_issue = find_existing_issue(repo, token, issue_data['id'])

    if existing_issue:

def titles_are_similar(title1, title2, threshold=0.85, same_context=False):        print(f"ℹ️ Issue already exists: #{existing_issue} - {issue_data['title']}")

    """        return existing_issue

    Check if two titles are similar using sequence matching    

        try:

    Args:        response = requests.post(url, headers=headers, json=payload)

        title1: First title        response.raise_for_status()

        title2: Second title        issue = response.json()

        threshold: Base similarity threshold (0.0-1.0)        print(f"✅ Created issue #{issue['number']}: {issue_data['title']}")

        same_context: True if same file AND same category (more lenient)        return issue['number']

        except requests.exceptions.RequestException as e:

    Returns:        print(f"❌ Failed to create issue: {e}")

        bool: True if titles are similar enough        if hasattr(e, 'response') and e.response:

    """            print(f"   Response: {e.response.text}")

    norm1 = normalize_title(title1)        return None

    norm2 = normalize_title(title2)

    def post_summary_to_pr(repo, token, pr_number, created_issues, existing_issues):

    if not norm1 or not norm2:    """Post summary comment to PR"""

        return False    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"

        headers = {"Authorization": f"Bearer {token}"}

    # Adjust threshold based on context    

    # Same file + category = more likely to be duplicate, be more lenient    total_issues = len(created_issues) + len(existing_issues)

    effective_threshold = threshold    

    if same_context:    if total_issues == 0:

        effective_threshold = 0.75  # More lenient (catches more variations)        return

        

    similarity = SequenceMatcher(None, norm1, norm2).ratio()    issue_links = []

        if created_issues:

    return similarity >= effective_threshold        issue_links.append("**New Issues Created:**")

        for num in created_issues:

# ============================================            issue_links.append(f"- 🆕 Issue #{num}: https://github.com/{repo}/issues/{num}")

# ISSUE SEARCHING    

# ============================================    if existing_issues:

        issue_links.append("\n**Existing Issues (Still Open):**")

def get_all_ai_issues(repo, token, limit=200):        for num in existing_issues:

    """Get all AI review issues (open and closed)"""            issue_links.append(f"- ⏳ Issue #{num}: https://github.com/{repo}/issues/{num}")

    all_issues = []    

        comment = f"""## 🚨 Critical Issues Detected by AI Review

    for state in ["open", "closed"]:

        url = f"https://api.github.com/repos/{repo}/issues"AI found **{total_issues} critical issue(s)** that require attention.

        headers = {

            "Authorization": f"Bearer {token}",{chr(10).join(issue_links)}

            "Accept": "application/vnd.github.v3+json"

        }**What happens next:**

        1. Fix the issues in your code

        params = {2. Commit and push your changes

            "state": state,3. AI will automatically re-review and verify fixes

            "labels": "ai-review",4. Issues will auto-close when AI confirms they're resolved ✅

            "per_page": 100,

            "sort": "updated",**Note:** These issues are tracked for code quality but won't block your merge.

            "direction": "desc"

        }---

        *AI-powered issue tracking with smart verification*

        try:"""

            response = requests.get(url, headers=headers, params=params)    

            response.raise_for_status()    data = {"body": comment}

            issues = response.json()    

            all_issues.extend(issues)    try:

                    response = requests.post(url, headers=headers, json=data)

            # Stop if we hit the limit        response.raise_for_status()

            if len(all_issues) >= limit:        print("✅ Posted summary to PR")

                break    except requests.exceptions.RequestException as e:

                        print(f"⚠️ Failed to post summary: {e}")

        except Exception as e:

            print(f"⚠️ Error fetching {state} issues: {e}")def main(review_file, pr_number):

        """Main function"""

    return all_issues[:limit]    # Read AI review

    try:

def extract_issue_metadata(issue):        with open(review_file, 'r') as f:

    """Extract metadata from existing issue"""            review_text = f.read()

    body = issue.get('body', '')    except FileNotFoundError:

            print(f"❌ Review file not found: {review_file}")

    # Extract AI-ID (simple ID)        return

    simple_id_match = re.search(r'AI-ID:\s*(\w+)', body)    

    simple_id = simple_id_match.group(1) if simple_id_match else None    if not review_text.strip():

            print("ℹ️ No review content found")

    # Extract fingerprint (new system)        return

    fingerprint_match = re.search(r'FINGERPRINT:\s*(\w+)', body)    

    fingerprint = fingerprint_match.group(1) if fingerprint_match else None    # Parse critical issues

        print("🔍 Parsing AI review for critical issues...")

    # Extract file path    issues = parse_ai_review(review_text)

    file_match = re.search(r'\*\*File:\*\*\s*`([^`]+)`', body)    

    file_path = file_match.group(1) if file_match else ''    if not issues:

            print("✅ No critical issues found! Code looks good.")

    # Extract category        return

    category_match = re.search(r'CATEGORY:\s*(\w+[-\w]*)', body)    

    category = category_match.group(1) if category_match else 'general'    print(f"📋 Found {len(issues)} critical issue(s)")

        

    return {    # Get GitHub info

        'number': issue['number'],    repo = os.getenv("GITHUB_REPOSITORY")

        'title': issue['title'],    token = os.getenv("GITHUB_TOKEN")

        'state': issue['state'],    

        'simple_id': simple_id,    if not repo or not token:

        'fingerprint': fingerprint,        print("⚠️ Missing GitHub repository or token")

        'file_path': file_path,        print("📄 Issues that would be created:")

        'category': category,        for i, issue in enumerate(issues, 1):

        'body': body,            print(f"\n{i}. {issue['title']}")

        'created_at': issue.get('created_at'),            print(f"   File: {issue['file_path']}")

        'closed_at': issue.get('closed_at'),            print(f"   Labels: {', '.join(issue['labels'])}")

        'labels': [label['name'] for label in issue.get('labels', [])]        return

    }    

    # Create issues

def find_matching_issue(all_issues, new_issue_data):    created_issues = []

    """    existing_issues = []

    Find matching issue using multiple strategies:    

    1. Exact fingerprint match (best)    for issue in issues:

    2. Simple ID match (backwards compatibility)        issue_num = create_github_issue(issue, repo, token, pr_number)

    3. Fuzzy match (same file + similar title + same category)        if issue_num:

    """            # Check if it was newly created or existing

    new_fp = new_issue_data['fingerprint_data']            existing = find_existing_issue(repo, token, issue['id'])

                if existing and existing == issue_num:

    exact_match = None                existing_issues.append(issue_num)

    simple_match = None            else:

    fuzzy_matches = []                created_issues.append(issue_num)

        

    for issue in all_issues:    # Summary

        metadata = extract_issue_metadata(issue)    if created_issues:

                print(f"\n🎉 Created {len(created_issues)} new GitHub issue(s):")

        # Strategy 1: Exact fingerprint match        for num in created_issues:

        if metadata['fingerprint'] and metadata['fingerprint'] == new_fp['fingerprint']:            print(f"   - Issue #{num}: https://github.com/{repo}/issues/{num}")

            exact_match = metadata    

            break    if existing_issues:

                print(f"\nℹ️ {len(existing_issues)} issue(s) already exist (still open)")

        # Strategy 2: Simple ID match (backwards compatibility)    

        if metadata['simple_id'] and metadata['simple_id'] == new_fp['simple_id']:    # Post summary to PR

            simple_match = metadata    if pr_number and not pr_number.startswith(('manual', 'push')):

                post_summary_to_pr(repo, token, pr_number, created_issues, existing_issues)

        # Strategy 3: Fuzzy match (same file + similar title + same category)

        same_context = (metadata['file_path'] == new_fp['file'] and metadata['category'] == new_fp['category'])if __name__ == "__main__":

        if (metadata['file_path'] == new_fp['file'] and    if len(sys.argv) < 3:

            metadata['category'] == new_fp['category'] and        print("Usage: python ai_review_to_issues.py <review_file> <pr_number>")

            titles_are_similar(metadata['title'], new_issue_data['title'], same_context=same_context)):        sys.exit(1)

            fuzzy_matches.append(metadata)    

        review_file = sys.argv[1]

    # Return best match    pr_number = sys.argv[2]

    if exact_match:    main(review_file, pr_number)

        return exact_match, 'exact'
    elif simple_match:
        return simple_match, 'simple'
    elif fuzzy_matches:
        # Return most recently updated fuzzy match
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
        print(f"⚠️ Failed to comment on issue #{issue_number}: {e}")
        return False

def remove_label(repo, token, issue_number, label):
    """Remove a label from an issue"""
    url = f"https://api.github.com/repos/{repo}/issues/{issue_number}/labels/{label}"
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
        print(f"⚠️ Failed to remove label {label} from issue #{issue_number}: {e}")
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
        print(f"⚠️ Failed to add label {label} to issue #{issue_number}: {e}")
        return False

def get_reopen_history(issue_body):
    """Extract reopen history from issue body"""
    reopen_match = re.search(r'Reopened:\s*(\d+)\s*times', issue_body)
    if reopen_match:
        return int(reopen_match.group(1))
    return 0

def create_meta_issue_for_recurring(repo, token, original_issue_number, reopen_count):
    """
    Create a meta-issue for deeply recurring problems (5+ reopens)
    This signals need for architectural review
    """
    url = f"https://api.github.com/repos/{repo}/issues"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # Get original issue details
    issue_url = f"https://api.github.com/repos/{repo}/issues/{original_issue_number}"
    try:
        response = requests.get(issue_url, headers=headers)
        response.raise_for_status()
        original_issue = response.json()
    except Exception as e:
        print(f"⚠️ Could not fetch issue #{original_issue_number}: {e}")
        return
    
    # Create meta-issue
    title = f"[META] Recurring Issue: {original_issue['title']}"
    body = f"""## 🔁 Recurring Issue Alert

**Original Issue:** #{original_issue_number}  
**Reopen Count:** {reopen_count} times  
**Status:** Critical - Requires Architectural Review

---

### 🚨 Problem

Issue #{original_issue_number} has been **reopened {reopen_count} times**, indicating a **systemic problem** that cannot be solved with simple bug fixes.

### 📊 Pattern Analysis

This issue keeps recurring despite multiple fixes, suggesting:
- **Architectural Issue:** Code structure encourages this bug
- **Inadequate Testing:** No regression tests to catch reoccurrences
- **Knowledge Gap:** Team doesn't understand root cause
- **Competing Priorities:** Fixes get overwritten by other work
- **Copy-Paste:** Old problematic code being reused

### 🎯 Required Actions

**This requires more than a bug fix:**

1. **Team Discussion**
   - Schedule meeting to discuss why this keeps happening
   - Review all historical fixes and why they failed
   - Document institutional knowledge

2. **Architectural Review**
   - Consider if current architecture encourages this bug
   - Evaluate refactoring options
   - Design patterns to prevent this class of issue

3. **Testing Strategy**
   - Add comprehensive regression tests
   - Update CI/CD to catch this pattern
   - Document test cases for code reviewers

4. **Documentation**
   - Create wiki page explaining issue and fix
   - Add comments in code explaining constraints
   - Update coding guidelines

5. **Code Review Process**
   - Add this pattern to review checklist
   - Train team on why this is problematic
   - Consider pair programming for this area

### 🔗 Related Issues

- Original Issue: #{original_issue_number}
- Reopened: {reopen_count} times

### 📝 Next Steps

**Do not close this meta-issue until:**
- [ ] Team discussion completed
- [ ] Root cause fully understood and documented
- [ ] Architectural changes implemented (if needed)
- [ ] Regression tests added
- [ ] Original issue stays closed for 30+ days
- [ ] No similar issues appear in codebase

---

*This meta-issue was automatically created because #{original_issue_number} was reopened {reopen_count} times.*  
*Recurring issues indicate systemic problems that need deeper solutions.*"""
    
    payload = {
        'title': title,
        'body': body,
        'labels': ['meta', 'recurring', 'architectural', 'priority:high']
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        meta_issue = response.json()
        print(f"   🚨 Created META issue #{meta_issue['number']} for recurring problem")
        
        # Link back to original issue
        comment_url = f"{issue_url}/comments"
        link_comment = f"""## 🔁 Meta-Issue Created

Due to {reopen_count} reopenings, a **meta-issue** has been created for architectural review: #{meta_issue['number']}

This indicates the problem requires more than a simple bug fix.

See #{meta_issue['number']} for next steps."""
        
        requests.post(comment_url, headers=headers, json={"body": link_comment})
        
    except Exception as e:
        print(f"   ⚠️ Failed to create meta-issue: {e}")

def reopen_issue(repo, token, issue_number, match_type, pr_number):
    """
    Reopen a closed issue when problem reappears
    Tracks reopen count and flags recurring issues
    """
    url = f"https://api.github.com/repos/{repo}/issues/{issue_number}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # Get current issue to check reopen history
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        existing_issue = response.json()
        existing_body = existing_issue.get('body', '')
        existing_labels = [label['name'] for label in existing_issue.get('labels', [])]
    except Exception as e:
        print(f"⚠️ Error fetching issue #{issue_number}: {e}")
        existing_body = ''
        existing_labels = []
    
    # Calculate reopen count
    reopen_count = get_reopen_history(existing_body) + 1
    
    # Reopen the issue
    try:
        response = requests.patch(url, headers=headers, json={"state": "open"})
        response.raise_for_status()
    except Exception as e:
        print(f"❌ Failed to reopen issue #{issue_number}: {e}")
        return False
    
    # Remove old confirmation labels
    for label in ["ai-not-seen-1x", "ai-not-seen-2x", "ai-not-seen-3x"]:
        remove_label(repo, token, issue_number, label)
    
    # Add "recurring" label if reopened 3+ times
    if reopen_count >= 3 and "recurring" not in existing_labels:
        add_label(repo, token, issue_number, "recurring")
        print(f"   ⚠️ Flagged as recurring (reopened {reopen_count}x)")
    
    # Determine match explanation
    match_explanations = {
        'exact': 'exact code fingerprint match',
        'simple': 'issue ID match',
        'fuzzy': 'similar title and code pattern'
    }
    match_explanation = match_explanations.get(match_type, 'pattern match')
    
    # Build reopening comment with enhanced context
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    
    # Different messages based on reopen count
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

**Pattern Analysis:**
This oscillating behavior (fixed → reintroduced → fixed → reintroduced) suggests:
- Insufficient test coverage
- Unclear documentation of previous fix
- Copy-paste from old code
- Missing architectural constraints
- Competing refactors

**Consider Creating Subtasks:**
- [ ] Investigate why issue keeps recurring
- [ ] Add regression tests
- [ ] Document the fix and why it matters
- [ ] Update code review checklist to catch this pattern
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
- ✅ Same file location
- ✅ Same problem category
- ✅ Similar or identical code pattern

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
    
    print(f"✅ Reopened issue #{issue_number} (match: {match_type}, count: {reopen_count}x)")
    
    # If reopened 5+ times, consider creating a new meta-issue
    if reopen_count >= 5:
        create_meta_issue_for_recurring(repo, token, issue_number, reopen_count)
    
    return True

def create_new_issue(repo, token, issue_data, pr_number):
    """Create a brand new GitHub issue"""
    url = f"https://api.github.com/repos/{repo}/issues"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    fp = issue_data['fingerprint_data']
    
    # Build comprehensive issue body
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

**Reopened:** 0 times

---

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
        print(f"✅ Created NEW issue #{issue['number']}: {issue_data['title']}")
        return issue['number']
    except Exception as e:
        print(f"❌ Failed to create issue: {e}")
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
    
    # Reset verification counter if exists
    for label in ["ai-not-seen-1x", "ai-not-seen-2x"]:
        remove_label(repo, token, existing_issue['number'], label)
    
    add_comment(repo, token, existing_issue['number'], comment)
    print(f"ℹ️ Issue #{existing_issue['number']} still open - added update comment")
    return existing_issue['number']

# ============================================
# MAIN PROCESSING
# ============================================

def parse_ai_review(review_text):
    """Parse AI review and extract critical issues with all metadata"""
    issues = []
    
    critical_pattern = r'\*\*🔴 CRITICAL:\s*([^\*\n]+)\*\*'
    sections = review_text.split('## File:')
    
    for section in sections[1:]:
        # Extract file path
        file_match = re.search(r'`([^`]+)`', section)
        if not file_match:
            continue
        file_path = file_match.group(1)
        
        # Find all critical issues
        for match in re.finditer(critical_pattern, section, re.IGNORECASE):
            issue_title = match.group(1).strip()
            
            # Extract issue block
            start_pos = match.start()
            next_issue = section.find('**🔴', start_pos + 10)
            next_perf = section.find('**🟡', start_pos)
            next_enhance = section.find('**🔵', start_pos)
            next_file = len(section)
            
            end_pos = min([p for p in [next_issue, next_perf, next_enhance, next_file] if p > start_pos])
            issue_block = section[start_pos:end_pos].strip()
            
            # Extract metadata
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
            
            # Generate fingerprint
            fingerprint_data = generate_issue_fingerprint(
                file_path, issue_title, problem, current_code, suggested_fix
            )
            
            # Determine labels
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
                'labels': list(set(labels)),  # Remove duplicates
                'fingerprint_data': fingerprint_data
            })
    
    return issues

def main(review_file, pr_number):
    """Main function with advanced duplicate prevention"""
    # Read AI review
    try:
        with open(review_file, 'r') as f:
            review_text = f.read()
    except FileNotFoundError:
        print(f"❌ Review file not found: {review_file}")
        return
    
    if not review_text.strip():
        print("ℹ️ No review content found")
        return
    
    # Parse issues
    print("🔍 Parsing AI review for critical issues...")
    new_issues = parse_ai_review(review_text)
    
    if not new_issues:
        print("✅ No critical issues found! Code looks good.")
        return
    
    print(f"📋 Found {len(new_issues)} critical issue(s) in review")
    
    # Get GitHub credentials
    repo = os.getenv("GITHUB_REPOSITORY")
    token = os.getenv("GITHUB_TOKEN")
    
    if not repo or not token:
        print("⚠️ Missing GitHub repository or token")
        print("\n📄 Issues that would be created:")
        for i, issue in enumerate(new_issues, 1):
            fp = issue['fingerprint_data']
            print(f"\n{i}. {issue['title']}")
            print(f"   File: {issue['file_path']}")
            print(f"   Category: {fp['category']}")
            print(f"   Fingerprint: {fp['fingerprint']}")
        return
    
    # Get all existing AI issues (both open and closed)
    print("\n🔍 Fetching existing AI issues (open and closed)...")
    all_existing_issues = get_all_ai_issues(repo, token, limit=200)
    print(f"📊 Found {len(all_existing_issues)} existing AI issue(s)")
    
    # Process each new issue
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
        
        # Find matching issue
        existing, match_type = find_matching_issue(all_existing_issues, issue_data)
        
        if existing:
            print(f"   Match found: #{existing['number']} (type: {match_type})")
            
            if existing['state'] == 'open':
                # Issue already open - add comment
                handle_existing_open_issue(repo, token, existing, pr_number)
                updated_count += 1
            else:
                # Issue was closed - reopen it
                reopen_issue(repo, token, existing['number'], match_type, pr_number)
                reopened_count += 1
        else:
            # No match - create new issue
            print("   No match found - creating new issue")
            issue_num = create_new_issue(repo, token, issue_data, pr_number)
            if issue_num:
                created_count += 1
    
    # Summary
    print("\n" + "="*70)
    print("📊 PROCESSING SUMMARY")
    print("="*70)
    print(f"   🆕 New issues created: {created_count}")
    print(f"   🔄 Closed issues reopened: {reopened_count}")
    print(f"   📝 Open issues updated: {updated_count}")
    print(f"   📋 Total processed: {len(new_issues)}")
    print("="*70)
    
    if created_count > 0:
        print(f"\n🎉 Created {created_count} new issue(s)")
    if reopened_count > 0:
        print(f"\n🔄 Reopened {reopened_count} previously closed issue(s)")
    if updated_count > 0:
        print(f"\n📝 Updated {updated_count} existing open issue(s)")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python ai_review_to_issues.py <review_file> <pr_number>")
        sys.exit(1)
    
    review_file = sys.argv[1]
    pr_number = sys.argv[2]
    main(review_file, pr_number)
