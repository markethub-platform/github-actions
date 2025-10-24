#!/usr/bin/env python3
"""
AI Fix Verification with Confirmation Counter
Re-reviews code and auto-closes issues only after 3 consecutive confirmations
"""
import sys
import os
import requests
import re
import hashlib

def generate_issue_id(file_path, issue_title):
    """Generate same unique ID used in creation"""
    # Extract just the issue title without [AI] prefix and emoji
    clean_title = re.sub(r'^\[AI\]\s*🔴\s*', '', issue_title)
    content = f"{file_path}:{clean_title}"
    return hashlib.md5(content.encode()).hexdigest()[:8]

def get_open_ai_issues(repo, token):
    """Get all open AI review issues"""
    url = f"https://api.github.com/repos/{repo}/issues"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    params = {
        "state": "open",
        "labels": "ai-review,critical",
        "per_page": 100
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        issues = response.json()
        
        # Extract issue metadata
        issue_list = []
        for issue in issues:
            # Extract AI-ID from body
            ai_id_match = re.search(r'AI-ID:\s*(\w+)', issue.get('body', ''))
            if ai_id_match:
                ai_id = ai_id_match.group(1)
                
                # Extract file path
                file_match = re.search(r'\*\*File:\*\*\s*`([^`]+)`', issue.get('body', ''))
                file_path = file_match.group(1) if file_match else ''
                
                # Get current labels
                labels = [label['name'] for label in issue.get('labels', [])]
                
                issue_list.append({
                    'number': issue['number'],
                    'title': issue['title'],
                    'ai_id': ai_id,
                    'file_path': file_path,
                    'body': issue.get('body', ''),
                    'labels': labels
                })
        
        return issue_list
    except Exception as e:
        print(f"❌ Error fetching issues: {e}")
        return []

def parse_current_review_issues(review_text):
    """Parse current AI review to see what issues still exist"""
    current_issue_ids = set()
    
    # Pattern to match critical issues
    critical_pattern = r'\*\*🔴 CRITICAL:\s*([^\*\n]+)\*\*'
    
    # Split review into file sections
    sections = review_text.split('## File:')
    
    for section in sections[1:]:
        # Extract file path
        file_match = re.search(r'`([^`]+)`', section)
        if not file_match:
            continue
        file_path = file_match.group(1)
        
        # Find all critical issues in this file
        for match in re.finditer(critical_pattern, section, re.IGNORECASE):
            issue_title = match.group(1).strip()
            issue_id = generate_issue_id(file_path, issue_title)
            current_issue_ids.add(issue_id)
    
    return current_issue_ids

def extract_files_reviewed(review_text):
    """Extract which specific files were reviewed"""
    reviewed_files = set()
    
    # Find all file sections
    for match in re.finditer(r'## File:\s*`([^`]+)`', review_text):
        reviewed_files.add(match.group(1))
    
    return reviewed_files

def should_verify_issue(issue, reviewed_files):
    """
    Only verify (and potentially close) an issue if:
    1. The file containing the issue was actually reviewed
    2. We have high confidence the issue is gone
    """
    issue_file = issue.get('file_path', '')
    
    if not issue_file:
        # No file path - can't verify, keep open
        return False
    
    if issue_file not in reviewed_files:
        # File wasn't reviewed - can't verify, keep open
        return False
    
    # File was reviewed - we can verify this issue
    return True

def get_not_seen_count(issue):
    """Extract count from label like 'ai-not-seen-2x'"""
    for label in issue.get('labels', []):
        if label.startswith('ai-not-seen-'):
            try:
                count_str = label.replace('ai-not-seen-', '').replace('x', '')
                return int(count_str)
            except (IndexError, ValueError):
                continue
    return 0

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

def remove_label(repo, token, issue_number, label):
    """Remove a label from an issue"""
    url = f"https://api.github.com/repos/{repo}/issues/{issue_number}/labels/{label}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        response = requests.delete(url, headers=headers)
        # 404 is OK (label didn't exist)
        if response.status_code not in [200, 204, 404]:
            response.raise_for_status()
        return True
    except Exception as e:
        print(f"⚠️ Failed to remove label {label} from issue #{issue_number}: {e}")
        return False

def update_not_seen_label(repo, token, issue_number, new_count, old_count):
    """Update the not-seen count label"""
    # Remove old label if exists
    if old_count > 0:
        old_label = f"ai-not-seen-{old_count}x"
        remove_label(repo, token, issue_number, old_label)
    
    # Add new label
    new_label = f"ai-not-seen-{new_count}x"
    add_label(repo, token, issue_number, new_label)

def comment_on_issue(repo, token, issue_number, comment_body):
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

def close_fixed_issue(repo, token, issue_number, issue_title):
    """Close an issue that AI confirmed is fixed (after 3 confirmations)"""
    url = f"https://api.github.com/repos/{repo}/issues/{issue_number}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # Post verification comment
    comment_body = """## ✅ Issue Verified as Fixed

🤖 **AI Verification Result:** RESOLVED (High Confidence)

This issue has been verified as fixed after **3 consecutive code reviews** without detection.

**Verification History:**
- ✅ Review 1: Issue not detected
- ✅ Review 2: Issue not detected  
- ✅ Review 3: Issue not detected → **Auto-closed**

**Confidence Level:** HIGH
- Issue's file was reviewed multiple times
- Issue pattern consistently not found
- High probability of successful fix

**What This Means:**
The problematic code has been successfully fixed or removed from the codebase.

**If This Closure is Incorrect:**
If you believe this issue still exists:
1. Reopen this issue with explanation
2. Reference specific code/file showing the problem
3. The next AI review will re-verify
4. Counter will reset and track again

**Great work!** This critical issue has been successfully resolved.

---
*Automated verification with 3-confirmation safety system*
*Prevents false positives while maintaining automation*"""
    
    try:
        # Post comment
        comment_on_issue(repo, token, issue_number, comment_body)
        
        # Close issue
        close_data = {"state": "closed"}
        response = requests.patch(url, headers=headers, json=close_data)
        response.raise_for_status()
        
        print(f"✅ Closed issue #{issue_number} after 3 confirmations: {issue_title}")
        return True
    except Exception as e:
        print(f"❌ Failed to close issue #{issue_number}: {e}")
        return False

def verify_with_confirmation(repo, token, issue, current_issue_ids, reviewed_files):
    """Verify with confirmation counter - only close after 3 consecutive non-detections"""
    
    # Only verify if file was reviewed
    if not should_verify_issue(issue, reviewed_files):
        return "skipped"
    
    issue_number = issue['number']
    
    # Check if issue still detected
    if issue['ai_id'] in current_issue_ids:
        # Issue still exists - reset counter if it was tracking
        old_count = get_not_seen_count(issue)
        if old_count > 0:
            # Remove not-seen label
            remove_label(repo, token, issue_number, f"ai-not-seen-{old_count}x")
            
            # Add comment about reset
            comment_on_issue(repo, token, issue_number,
                "⚠️ **Issue Still Detected - Counter Reset**\n\n"
                "This issue is still present in the latest code review.\n\n"
                f"**Previous Progress:** {old_count}/3 confirmations\n"
                "**Status:** Reset to 0/3 (issue still exists)\n\n"
                "The verification counter has been reset. "
                "The issue will be tracked again once it's no longer detected.")
            
            print(f"⚠️  Issue #{issue_number} still exists - reset counter (was {old_count}/3)")
        
        return "still_exists"
    
    # Issue not detected - increment counter
    old_count = get_not_seen_count(issue)
    new_count = old_count + 1
    
    # Update label
    update_not_seen_label(repo, token, issue_number, new_count, old_count)
    
    if new_count >= 3:
        # Close with high confidence!
        close_fixed_issue(repo, token, issue_number, issue['title'])
        return "closed"
    else:
        # Keep open, add progress comment
        remaining = 3 - new_count
        comment_on_issue(repo, token, issue_number,
            f"⏳ **Verification Progress: {new_count}/3**\n\n"
            f"This issue was not detected in the latest code review.\n\n"
            f"**Status:** Possibly fixed (needs {remaining} more {'confirmation' if remaining == 1 else 'confirmations'})\n\n"
            f"**What Happens Next:**\n"
            f"- If not detected in {remaining} more consecutive {'review' if remaining == 1 else 'reviews'} → Auto-closes ✅\n"
            f"- If detected again → Counter resets ⚠️\n\n"
            f"This confirmation system ensures issues are truly fixed before closing.")
        
        print(f"⏳ Issue #{issue_number} tracking: {new_count}/3 confirmations")
        return "tracking"

def main(review_file):
    """Main verification function"""
    # Read latest AI review
    try:
        with open(review_file, 'r') as f:
            review_text = f.read()
    except FileNotFoundError:
        print(f"❌ Review file not found: {review_file}")
        return
    
    if not review_text.strip():
        print("ℹ️ No review content found")
        return
    
    # Get GitHub credentials
    repo = os.getenv("GITHUB_REPOSITORY")
    token = os.getenv("GITHUB_TOKEN")
    
    if not repo or not token:
        print("⚠️ Missing GitHub repository or token")
        return
    
    print("🔍 Starting AI fix verification with confirmation counter...")
    print("   Requires 3 consecutive non-detections before auto-closing")
    
    # Get all open AI issues
    open_issues = get_open_ai_issues(repo, token)
    if not open_issues:
        print("✅ No open AI issues to verify")
        return
    
    print(f"📋 Found {len(open_issues)} open AI issue(s) to verify")
    
    # Extract which files were actually reviewed
    reviewed_files = extract_files_reviewed(review_text)
    print(f"📄 Current review analyzed {len(reviewed_files)} file(s):")
    for file in list(reviewed_files)[:5]:  # Show first 5
        print(f"   - {file}")
    if len(reviewed_files) > 5:
        print(f"   ... and {len(reviewed_files) - 5} more")
    
    if not reviewed_files:
        print("⚠️ No files found in review - skipping verification")
        return
    
    # Parse current review to see what issues still exist
    current_issue_ids = parse_current_review_issues(review_text)
    print(f"🔍 Current review found {len(current_issue_ids)} critical issue(s)")
    
    # Check each open issue with confirmation counter
    closed_count = 0
    tracking_count = 0
    reset_count = 0
    skipped_count = 0
    
    print("\n" + "="*60)
    print("Verification Results:")
    print("="*60)
    
    for issue in open_issues:
        result = verify_with_confirmation(repo, token, issue, current_issue_ids, reviewed_files)
        
        if result == "closed":
            closed_count += 1
        elif result == "tracking":
            tracking_count += 1
        elif result == "still_exists":
            reset_count += 1
        elif result == "skipped":
            skipped_count += 1
    
    # Summary
    print("\n" + "="*60)
    print("📊 Verification Summary:")
    print("="*60)
    print(f"   ✅ Issues closed (3/3 confirmations): {closed_count}")
    print(f"   ⏳ Issues tracking (1-2/3 confirmations): {tracking_count}")
    print(f"   ⚠️  Issues reset (detected again): {reset_count}")
    print(f"   ⏭️  Issues skipped (file not reviewed): {skipped_count}")
    print("="*60)
    
    if closed_count > 0:
        print(f"\n🎉 Great work! {closed_count} issue(s) automatically closed after 3 confirmations")
    
    if tracking_count > 0:
        print(f"\nℹ️  {tracking_count} issue(s) being tracked - will close after more confirmations")
    
    if skipped_count > 0:
        print(f"\nℹ️  {skipped_count} issue(s) not verified because their files weren't in this review")
        print("   These issues will be verified when their files are reviewed in future PRs")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ai_verify_fixes.py <review_file>")
        sys.exit(1)
    
    review_file = sys.argv[1]
    main(review_file)
