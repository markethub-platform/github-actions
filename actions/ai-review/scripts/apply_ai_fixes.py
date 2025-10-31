#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Fix Applier - Automatically applies AI-suggested fixes from GitHub issues
Parses issue bodies, extracts code suggestions, applies them, and creates PRs
"""
import re
import sys
import os
import requests
import json
from pathlib import Path
import subprocess
import hashlib

def get_ai_issues_with_fixes(repo, token):
    """Fetch all open AI issues that contain code suggestions"""
    url = f"https://api.github.com/repos/{repo}/issues"
    headers = {"Authorization": f"token {token}"}
    params = {
        "state": "open",
        "labels": "ai-review",
        "per_page": 100
    }
    
    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        print(f"Error fetching issues: {response.status_code}")
        return []
    
    issues = response.json()
    
    # Filter issues that have suggested fixes (contain code blocks)
    issues_with_fixes = []
    for issue in issues:
        body = issue.get('body', '')
        if '### ✅ Suggested Fix' in body and '```' in body:
            issues_with_fixes.append(issue)
    
    return issues_with_fixes

def extract_fix_info(issue_body):
    """Extract file path, current code, and suggested fix from issue"""
    fix_info = {
        'file_path': None,
        'current_code': None,
        'suggested_fix': None,
        'description': None
    }
    
    # Extract file path
    file_match = re.search(r'File:\s+`?([^`\n]+)`?', issue_body)
    if file_match:
        fix_info['file_path'] = file_match.group(1).strip()
    
    # Extract problem description
    desc_match = re.search(r'### 🔴 Problem Description\n\n(.+?)(?:\n\n###|\n\n---)', issue_body, re.DOTALL)
    if desc_match:
        fix_info['description'] = desc_match.group(1).strip()
    
    # Extract current code
    current_match = re.search(r'### 📄 Current Code\n\n```(?:\w+)?\n(.*?)```', issue_body, re.DOTALL)
    if current_match:
        fix_info['current_code'] = current_match.group(1).strip()
    
    # Extract suggested fix
    suggested_match = re.search(r'### ✅ Suggested Fix\n\n```(?:\w+)?\n(.*?)```', issue_body, re.DOTALL)
    if suggested_match:
        fix_info['suggested_fix'] = suggested_match.group(1).strip()
    
    return fix_info

def apply_fix_to_file(file_path, current_code, suggested_fix, repo_path):
    """Apply the suggested fix to the file"""
    full_path = Path(repo_path) / file_path
    
    if not full_path.exists():
        print(f"  ⚠️  File not found: {full_path}")
        return False
    
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Normalize whitespace for matching
        current_normalized = current_code.strip()
        
        if current_normalized not in content:
            # Try with different indentation
            lines = current_normalized.split('\n')
            # Try to find by first line
            first_line = lines[0].strip()
            if first_line in content:
                print(f"  ⚠️  Partial match found, manual review needed")
                return False
            else:
                print(f"  ⚠️  Current code not found in file")
                return False
        
        # Apply the fix
        new_content = content.replace(current_normalized, suggested_fix.strip())
        
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"  ✅ Applied fix to {file_path}")
        return True
    
    except Exception as e:
        print(f"  ❌ Error applying fix: {e}")
        return False

def create_fix_branch_and_pr(repo_path, repo_name, token, fixed_issues):
    """Create a branch with all fixes and open a PR"""
    os.chdir(repo_path)
    
    # Create unique branch name
    branch_name = f"ai-fixes/auto-apply-{len(fixed_issues)}-fixes"
    
    # Create and checkout branch
    subprocess.run(["git", "checkout", "-b", branch_name], check=True)
    
    # Stage all changes
    subprocess.run(["git", "add", "."], check=True)
    
    # Create commit message
    commit_msg = f"fix: Auto-apply {len(fixed_issues)} AI-suggested fixes\n\n"
    commit_msg += "Automatically applied fixes for:\n"
    for issue in fixed_issues:
        commit_msg += f"- #{issue['number']}: {issue['title']}\n"
    
    subprocess.run(["git", "commit", "-m", commit_msg], check=True)
    
    # Push branch
    subprocess.run(["git", "push", "-u", "origin", branch_name], check=True)
    
    # Create PR
    pr_title = f"🤖 Auto-apply {len(fixed_issues)} AI-suggested fixes"
    pr_body = f"""## 🤖 Automated Fix PR

This PR automatically applies AI-suggested fixes from open issues.

### Fixed Issues ({len(fixed_issues)})

"""
    
    for issue in fixed_issues:
        pr_body += f"- Closes #{issue['number']}: {issue['title']}\n"
    
    pr_body += """

### How This Works

1. AI Code Review detects issues
2. AI suggests fixes in issue body  
3. This script automatically:
   - Extracts suggested fixes
   - Applies them to the code
   - Creates this PR

### Review Notes

- ✅ All fixes are AI-suggested
- 🔍 Please review each change carefully
- 🧪 All CI/CD checks will run automatically
- 📝 Original issues will auto-close on merge

"""
    
    # Create PR via GitHub API
    url = f"https://api.github.com/repos/{repo_name}/pulls"
    headers = {
        "Authorization": f"token {token}",
        "Content-Type": "application/json"
    }
    data = {
        "title": pr_title,
        "body": pr_body,
        "head": branch_name,
        "base": "main"
    }
    
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 201:
        pr_url = response.json()['html_url']
        print(f"\n✅ Created PR: {pr_url}")
        return pr_url
    else:
        print(f"\n❌ Failed to create PR: {response.status_code}")
        print(response.json())
        return None

def main(repo_path, repo_name, token):
    """Main function"""
    print("="*70)
    print("AI FIX APPLIER - Automatic Code Fix Application")
    print("="*70)
    
    print(f"\n📋 Fetching AI issues with suggested fixes from {repo_name}...")
    issues = get_ai_issues_with_fixes(repo_name, token)
    
    if not issues:
        print("✅ No issues with suggested fixes found!")
        return
    
    print(f"Found {len(issues)} issue(s) with suggested fixes\n")
    
    fixed_issues = []
    skipped_issues = []
    
    for issue in issues:
        print(f"\n{'='*70}")
        print(f"Issue #{issue['number']}: {issue['title']}")
        print(f"{'='*70}")
        
        fix_info = extract_fix_info(issue['body'])
        
        if not all([fix_info['file_path'], fix_info['current_code'], fix_info['suggested_fix']]):
            print("  ⚠️  Missing required info, skipping")
            skipped_issues.append(issue)
            continue
        
        print(f"  📁 File: {fix_info['file_path']}")
        print(f"  📝 Description: {fix_info['description'][:60]}...")
        
        success = apply_fix_to_file(
            fix_info['file_path'],
            fix_info['current_code'],
            fix_info['suggested_fix'],
            repo_path
        )
        
        if success:
            fixed_issues.append(issue)
        else:
            skipped_issues.append(issue)
    
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"✅ Fixed: {len(fixed_issues)} issues")
    print(f"⚠️  Skipped: {len(skipped_issues)} issues")
    
    if fixed_issues:
        print(f"\n🚀 Creating PR with {len(fixed_issues)} fixes...")
        pr_url = create_fix_branch_and_pr(repo_path, repo_name, token, fixed_issues)
        if pr_url:
            print(f"\n🎉 Success! Review the PR at: {pr_url}")
    else:
        print("\n⚠️  No fixes applied, no PR created")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python apply_ai_fixes.py <repo_path>")
        print("Example: python apply_ai_fixes.py /path/to/markethub-web")
        sys.exit(1)
    
    repo_path = sys.argv[1]
    repo_name = os.getenv("GITHUB_REPOSITORY")
    token = os.getenv("GITHUB_TOKEN")
    
    if not repo_name or not token:
        print("Error: GITHUB_REPOSITORY and GITHUB_TOKEN environment variables required")
        sys.exit(1)
    
    main(repo_path, repo_name, token)
