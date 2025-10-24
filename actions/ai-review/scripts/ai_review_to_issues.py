#!/usr/bin/env python3
"""
AI Review to GitHub Issues Converter
Parses AI review and creates GitHub issues for critical findings
"""
import re
import sys
import os
import requests
import json
import hashlib

def generate_issue_id(file_path, issue_title):
    """Generate unique ID for issue to prevent duplicates"""
    content = f"{file_path}:{issue_title}"
    return hashlib.md5(content.encode()).hexdigest()[:8]

def parse_ai_review(review_text):
    """
    Parse AI review text and extract critical issues
    Returns list of issues with metadata
    """
    issues = []
    
    # Pattern to match critical issues: **🔴 CRITICAL: Title**
    critical_pattern = r'\*\*🔴 CRITICAL:\s*([^\*\n]+)\*\*'
    
    # Split review into file sections
    sections = review_text.split('## File:')
    
    for section in sections[1:]:  # Skip first empty section
        # Extract file path
        file_match = re.search(r'`([^`]+)`', section)
        if not file_match:
            continue
        file_path = file_match.group(1)
        
        # Find all critical issues in this file
        for match in re.finditer(critical_pattern, section, re.IGNORECASE):
            issue_title = match.group(1).strip()
            
            # Extract the full issue block
            start_pos = match.start()
            
            # Find next issue marker or end of section
            next_issue = section.find('**🔴', start_pos + 10)
            next_perf = section.find('**🟡', start_pos)
            next_enhance = section.find('**🔵', start_pos)
            next_file = len(section)
            
            end_pos = min([p for p in [next_issue, next_perf, next_enhance, next_file] if p > start_pos])
            issue_block = section[start_pos:end_pos].strip()
            
            # Extract problem description
            problem_match = re.search(r'\*\*Problem:\*\*\s*([^\n]+)', issue_block)
            problem = problem_match.group(1).strip() if problem_match else 'See AI review for details'
            
            # Extract current code
            current_code = ''
            current_match = re.search(r'\*\*Current Code:\*\*\s*```[\w]*\n(.*?)```', issue_block, re.DOTALL)
            if current_match:
                current_code = current_match.group(1).strip()
            
            # Extract suggested fix
            suggested_fix = ''
            fix_match = re.search(r'\*\*(?:Suggested Fix|Fix):\*\*\s*```[\w]*\n(.*?)```', issue_block, re.DOTALL)
            if fix_match:
                suggested_fix = fix_match.group(1).strip()
            
            # Extract reasoning
            why_match = re.search(r'\*\*Why:\*\*\s*([^\n]+)', issue_block)
            reasoning = why_match.group(1).strip() if why_match else ''
            
            # Determine labels from file path
            labels = ['ai-review', 'critical', 'bug']
            if 'frontend' in file_path or any(ext in file_path for ext in ['.tsx', '.jsx', '.ts', '.js']):
                labels.append('frontend')
            if 'component' in file_path.lower():
                labels.append('component')
            if 'api' in file_path.lower() or 'service' in file_path.lower():
                labels.append('api')
            if 'hook' in file_path.lower():
                labels.append('hooks')
            
            # Generate unique ID for this issue
            issue_id = generate_issue_id(file_path, issue_title)
            
            # Build issue
            issues.append({
                'id': issue_id,
                'title': f"[AI] 🔴 {issue_title}",
                'file_path': file_path,
                'problem': problem,
                'current_code': current_code,
                'suggested_fix': suggested_fix,
                'reasoning': reasoning,
                'labels': labels
            })
    
    return issues

def find_existing_issue(repo, token, issue_id):
    """Check if issue already exists by searching for unique ID"""
    url = f"https://api.github.com/repos/{repo}/issues"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    params = {
        "state": "open",
        "labels": "ai-review",
        "per_page": 100
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        issues = response.json()
        
        # Check if any issue contains this ID
        for issue in issues:
            if f"AI-ID: {issue_id}" in issue.get('body', ''):
                return issue['number']
        
        return None
    except Exception as e:
        print(f"⚠️ Error checking existing issues: {e}")
        return None

def create_github_issue(issue_data, repo, token, pr_number=None):
    """Create a GitHub issue"""
    url = f"https://api.github.com/repos/{repo}/issues"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # Build issue body
    body = f"""## 🤖 AI-Detected Critical Issue

**File:** `{issue_data['file_path']}`

**Problem:**
{issue_data['problem']}
"""
    
    if issue_data['current_code']:
        body += f"""
**Current Code:**
```typescript
{issue_data['current_code']}
```
"""
    
    if issue_data['suggested_fix']:
        body += f"""
**Suggested Fix:**
```typescript
{issue_data['suggested_fix']}
```
"""
    
    if issue_data['reasoning']:
        body += f"""
**Why this matters:**
{issue_data['reasoning']}
"""
    
    body += f"""

---

**Context:**
- 🤖 Detected by: AI Code Review (Claude Sonnet 4.5)
- 🔴 Severity: Critical
- 🆔 AI-ID: {issue_data['id']}
"""
    
    if pr_number:
        body += f"\n- 📋 Related PR: #{pr_number}"
    
    body += """

**Status:**
- ⏳ Waiting for fix
- 🔍 AI will verify when fixed

**Next Steps:**
1. Review the suggested fix
2. Implement the solution
3. Commit and push your changes
4. AI will automatically verify and close this issue if fixed

---
*This issue was automatically created from an AI code review and will auto-close when AI verifies the fix.*
"""
    
    payload = {
        'title': issue_data['title'],
        'body': body,
        'labels': issue_data['labels']
    }
    
    # Check if issue already exists
    existing_issue = find_existing_issue(repo, token, issue_data['id'])
    if existing_issue:
        print(f"ℹ️ Issue already exists: #{existing_issue} - {issue_data['title']}")
        return existing_issue
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        issue = response.json()
        print(f"✅ Created issue #{issue['number']}: {issue_data['title']}")
        return issue['number']
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to create issue: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"   Response: {e.response.text}")
        return None

def post_summary_to_pr(repo, token, pr_number, created_issues, existing_issues):
    """Post summary comment to PR"""
    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    headers = {"Authorization": f"Bearer {token}"}
    
    total_issues = len(created_issues) + len(existing_issues)
    
    if total_issues == 0:
        return
    
    issue_links = []
    if created_issues:
        issue_links.append("**New Issues Created:**")
        for num in created_issues:
            issue_links.append(f"- 🆕 Issue #{num}: https://github.com/{repo}/issues/{num}")
    
    if existing_issues:
        issue_links.append("\n**Existing Issues (Still Open):**")
        for num in existing_issues:
            issue_links.append(f"- ⏳ Issue #{num}: https://github.com/{repo}/issues/{num}")
    
    comment = f"""## 🚨 Critical Issues Detected by AI Review

AI found **{total_issues} critical issue(s)** that require attention.

{chr(10).join(issue_links)}

**What happens next:**
1. Fix the issues in your code
2. Commit and push your changes
3. AI will automatically re-review and verify fixes
4. Issues will auto-close when AI confirms they're resolved ✅

**Note:** These issues are tracked for code quality but won't block your merge.

---
*AI-powered issue tracking with smart verification*
"""
    
    data = {"body": comment}
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        print("✅ Posted summary to PR")
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Failed to post summary: {e}")

def main(review_file, pr_number):
    """Main function"""
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
    
    # Parse critical issues
    print("🔍 Parsing AI review for critical issues...")
    issues = parse_ai_review(review_text)
    
    if not issues:
        print("✅ No critical issues found! Code looks good.")
        return
    
    print(f"📋 Found {len(issues)} critical issue(s)")
    
    # Get GitHub info
    repo = os.getenv("GITHUB_REPOSITORY")
    token = os.getenv("GITHUB_TOKEN")
    
    if not repo or not token:
        print("⚠️ Missing GitHub repository or token")
        print("📄 Issues that would be created:")
        for i, issue in enumerate(issues, 1):
            print(f"\n{i}. {issue['title']}")
            print(f"   File: {issue['file_path']}")
            print(f"   Labels: {', '.join(issue['labels'])}")
        return
    
    # Create issues
    created_issues = []
    existing_issues = []
    
    for issue in issues:
        issue_num = create_github_issue(issue, repo, token, pr_number)
        if issue_num:
            # Check if it was newly created or existing
            existing = find_existing_issue(repo, token, issue['id'])
            if existing and existing == issue_num:
                existing_issues.append(issue_num)
            else:
                created_issues.append(issue_num)
    
    # Summary
    if created_issues:
        print(f"\n🎉 Created {len(created_issues)} new GitHub issue(s):")
        for num in created_issues:
            print(f"   - Issue #{num}: https://github.com/{repo}/issues/{num}")
    
    if existing_issues:
        print(f"\nℹ️ {len(existing_issues)} issue(s) already exist (still open)")
    
    # Post summary to PR
    if pr_number and not pr_number.startswith(('manual', 'push')):
        post_summary_to_pr(repo, token, pr_number, created_issues, existing_issues)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python ai_review_to_issues.py <review_file> <pr_number>")
        sys.exit(1)
    
    review_file = sys.argv[1]
    pr_number = sys.argv[2]
    main(review_file, pr_number)
