#!/usr/bin/env python3
"""
Cleanup Duplicate AI Issues
Identifies and closes duplicate issues, keeping the most recent one
"""
import os
import sys
import requests
import re
from difflib import SequenceMatcher
from datetime import datetime

def normalize_title(title):
    """Normalize title for comparison"""
    title = re.sub(r'^\[AI\]\s*🔴\s*', '', title)
    title = title.lower()
    title = re.sub(r'[^\w\s-]', '', title)
    return ' '.join(title.split())

def titles_are_similar(title1, title2, threshold=0.85):
    """Check if titles are similar"""
    norm1 = normalize_title(title1)
    norm2 = normalize_title(title2)
    similarity = SequenceMatcher(None, norm1, norm2).ratio()
    return similarity >= threshold

def extract_file_path(issue_body):
    """Extract file path from issue body"""
    file_match = re.search(r'\*\*File:\*\*\s*`([^`]+)`', issue_body)
    return file_match.group(1) if file_match else ''

def get_all_ai_issues(repo, token):
    """Get all AI review issues"""
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
            "per_page": 100
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            all_issues.extend(response.json())
        except Exception as e:
            print(f"⚠️ Error fetching issues: {e}")
    
    return all_issues

def find_duplicate_groups(issues):
    """Group duplicate issues"""
    groups = []
    processed = set()
    
    for i, issue1 in enumerate(issues):
        if issue1['number'] in processed:
            continue
        
        file1 = extract_file_path(issue1.get('body', ''))
        duplicates = [issue1]
        
        for issue2 in issues[i+1:]:
            if issue2['number'] in processed:
                continue
            
            file2 = extract_file_path(issue2.get('body', ''))
            
            # Same file + similar title = duplicate
            if file1 == file2 and titles_are_similar(issue1['title'], issue2['title']):
                duplicates.append(issue2)
                processed.add(issue2['number'])
        
        if len(duplicates) > 1:
            # Sort by creation date (keep most recent)
            duplicates.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            groups.append(duplicates)
            processed.add(issue1['number'])
    
    return groups

def close_duplicate(repo, token, issue_number, kept_issue_number, dry_run=True):
    """Close a duplicate issue"""
    if dry_run:
        print(f"   [DRY RUN] Would close #{issue_number} (duplicate of #{kept_issue_number})")
        return True
    
    url = f"https://api.github.com/repos/{repo}/issues/{issue_number}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # Add comment
    comment_url = f"{url}/comments"
    comment = f"""## 🔄 Closing as Duplicate

This issue is a **duplicate** of #{kept_issue_number}.

**Why Closing:**
- Same file and problem pattern
- Keeping most recent issue for tracking
- Enhanced fingerprint system will prevent future duplicates

**Please reference:** Issue #{kept_issue_number} for updates

---
*Automated cleanup by AI review system*"""
    
    try:
        requests.post(comment_url, headers=headers, json={"body": comment})
        
        # Close issue
        requests.patch(url, headers=headers, json={"state": "closed"})
        print(f"   ✅ Closed #{issue_number} as duplicate of #{kept_issue_number}")
        return True
    except Exception as e:
        print(f"   ❌ Failed to close #{issue_number}: {e}")
        return False

def main():
    """Main cleanup function"""
    repo = os.getenv("GITHUB_REPOSITORY")
    token = os.getenv("GITHUB_TOKEN")
    
    if not repo or not token:
        print("❌ Missing GITHUB_REPOSITORY or GITHUB_TOKEN")
        sys.exit(1)
    
    # Check for dry-run flag
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv
    
    if dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
    else:
        print("⚠️ LIVE MODE - Issues will be closed")
        confirm = input("Continue? (yes/no): ")
        if confirm.lower() != "yes":
            print("Cancelled")
            return
    
    print(f"\n📊 Repository: {repo}")
    print("🔍 Fetching all AI review issues...")
    
    all_issues = get_all_ai_issues(repo, token)
    print(f"✅ Found {len(all_issues)} total AI review issues")
    
    print("\n🔍 Identifying duplicate groups...")
    duplicate_groups = find_duplicate_groups(all_issues)
    
    if not duplicate_groups:
        print("✅ No duplicates found!")
        return
    
    print(f"\n📋 Found {len(duplicate_groups)} duplicate group(s):")
    print("="*70)
    
    total_to_close = 0
    
    for idx, group in enumerate(duplicate_groups, 1):
        keeper = group[0]  # Most recent
        duplicates = group[1:]  # Older ones
        
        print(f"\nGroup {idx}:")
        print(f"   KEEP: #{keeper['number']} - {keeper['title']}")
        print(f"        Created: {keeper.get('created_at')}")
        print(f"        State: {keeper['state'].upper()}")
        
        for dup in duplicates:
            print(f"   CLOSE: #{dup['number']} - {dup['title']}")
            print(f"          Created: {dup.get('created_at')}")
            print(f"          State: {dup['state'].upper()}")
            total_to_close += 1
    
    print("\n" + "="*70)
    print(f"📊 Summary: {len(duplicate_groups)} groups, {total_to_close} duplicates to close")
    print("="*70)
    
    if total_to_close == 0:
        print("✅ Nothing to close!")
        return
    
    if not dry_run:
        print(f"\n🚀 Closing {total_to_close} duplicate issue(s)...")
    
    closed_count = 0
    for group in duplicate_groups:
        keeper = group[0]
        for dup in group[1:]:
            if close_duplicate(repo, token, dup['number'], keeper['number'], dry_run):
                closed_count += 1
    
    print("\n" + "="*70)
    if dry_run:
        print(f"✅ DRY RUN COMPLETE - Would close {closed_count} issue(s)")
        print("\nRun without --dry-run flag to actually close duplicates:")
        print(f"  python cleanup_duplicates.py")
    else:
        print(f"✅ CLEANUP COMPLETE - Closed {closed_count} duplicate issue(s)")
    print("="*70)

if __name__ == "__main__":
    main()
