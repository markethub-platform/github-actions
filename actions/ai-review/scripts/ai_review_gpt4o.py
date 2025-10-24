import sys
import os
import requests
from openai import OpenAI
from datetime import datetime, timezone

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def find_existing_ai_comment(repo, token, pr_number):
    """Find existing GPT-4o AI review comment by searching for the marker"""
    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        comments = response.json()
        
        # Look for our marker in existing comments
        marker = "🤖 GPT-4o AI Code Review"
        for comment in comments:
            if marker in comment.get("body", ""):
                return comment["id"]
        return None
    except Exception as e:
        print(f"⚠️ Error finding existing comment: {e}")
        return None

def update_or_create_comment(repo, token, pr_number, review_content):
    """Update existing comment or create new one with timestamp"""
    existing_comment_id = find_existing_ai_comment(repo, token, pr_number)
    
    # Add timestamp to header
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    review_header = f"## 🤖 GPT-4o AI Code Review\n\n**Last updated:** {timestamp}\n\n"
    review_footer = "\n\n---\n*Powered by GPT-4o | Updates automatically on every push*"
    
    full_comment = f"{review_header}{review_content}{review_footer}"
    
    if existing_comment_id:
        # Update existing comment
        url = f"https://api.github.com/repos/{repo}/issues/comments/{existing_comment_id}"
        headers = {"Authorization": f"Bearer {token}"}
        data = {"body": full_comment}
        
        try:
            response = requests.patch(url, headers=headers, json=data)
            response.raise_for_status()
            print(f"✅ Updated existing GPT-4o review comment (ID: {existing_comment_id})")
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to update comment: {e}")
            print(full_comment)
    else:
        # Create new comment
        url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
        headers = {"Authorization": f"Bearer {token}"}
        data = {"body": full_comment}
        
        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            print("✅ Created new GPT-4o review comment")
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to create comment: {e}")
            print(full_comment)

def post_no_code_message(pr_number):
    """Post message when no code found"""
    repo = os.getenv("GITHUB_REPOSITORY")
    token = os.getenv("GITHUB_TOKEN")
    
    if not repo or not token:
        return
    
    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    headers = {"Authorization": f"Bearer {token}"}
    
    message = """## 🤖 AI Code Review

**Status:** No code files found for review

This PR doesn't contain any TypeScript/JavaScript files in the `frontend/src` directory, or the frontend code hasn't been committed yet.

**Next Steps:**
1. Ensure your frontend source code is committed to the repository
2. Verify files are in the `frontend/src` directory
3. Push your changes and the AI review will run automatically

**What gets reviewed:**
- `.ts`, `.tsx`, `.js`, `.jsx` files in `frontend/src`
- Components, hooks, utilities, and services

---
*AI code review is ready once source code is available*"""
    
    data = {"body": message}
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        print("✅ Posted 'no code' message to PR")
    except Exception as e:
        print(f"⚠️ Could not post message: {e}")

def main(diff_file, pr_number):
    with open(diff_file, "r") as f:
        diff = f.read()

    # Enhanced empty check
    empty_markers = ["# PR changes", "# No changes", "# No code files found", "# No frontend directory"]
    if not diff.strip() or diff.strip() in empty_markers:
        print("ℹ️ No code to review")
        if not pr_number.startswith(("manual", "push")):
            post_no_code_message(pr_number)
        return

    # Limit diff length
    max_chars = 100000  # GPT-4o has 128k context window
    if len(diff) > max_chars:
        diff = diff[:max_chars] + "\n\n[...additional files truncated due to size...]"

    try:
        # GPT-4o with enhanced prompt
        review = client.chat.completions.create(
            model="gpt-4o",
            temperature=0.3,
            messages=[
                {
                    "role": "system", 
                    "content": """You are an AI code reviewer integrated into a GitHub Actions CI/CD pipeline. You are reviewing a React/TypeScript web application codebase and will post your findings as a GitHub PR comment.

**CONTEXT:**
- You are reviewing code automatically via GitHub Actions
- Your output will be posted as a comment on a GitHub Pull Request
- This is NOT an interactive conversation
- Do NOT ask the user to provide code or paste anything
- The code has already been provided in the user message

**YOUR TASK:**
Perform a comprehensive code review of the provided React/TypeScript codebase.

**CRITICAL REQUIREMENTS:**
- ALWAYS reference exact file paths: `src/path/to/file.tsx`
- Provide specific code snippets showing problems
- Give exact replacement code for fixes
- Structure feedback by file/module
- Be concise but thorough
- Focus on actionable feedback

**ANALYSIS AREAS:**

**🔴 CRITICAL ISSUES:**
- TypeScript type errors and `any` types
- React hooks dependency arrays and infinite loops
- Memory leaks (missing cleanup in useEffect)
- Security vulnerabilities (XSS, injection)
- Breaking bugs that would crash in production

**🟡 PERFORMANCE ISSUES:**
- Unnecessary re-renders (missing React.memo, useMemo, useCallback)
- Inefficient useEffect dependencies
- Large bundle sizes (missing code splitting/lazy loading)
- Unoptimized images or assets
- N+1 query problems

**🔵 ENHANCEMENTS:**
- Better TypeScript typing
- Component composition improvements
- Custom hooks extraction
- Error handling improvements
- Accessibility (a11y) compliance
- Code organization and readability

**OUTPUT FORMAT:**

## 📊 Code Review Summary

**Files Reviewed:** [count]
**Issues Found:** 🔴 [critical] | 🟡 [performance] | 🔵 [enhancements]

---

## File: `src/path/to/file.tsx`

**🔴 CRITICAL: [Issue Title]**
- **Problem:** [Brief description]
- **Current Code:**
```typescript
// Problematic code
```
- **Suggested Fix:**
```typescript
// Improved code with inline comments
```
- **Why:** [Impact explanation]

---

## Overall Recommendations

[3-5 high-level suggestions for the codebase]

**IMPORTANT RULES:**
- If code looks good, say so! Don't invent problems.
- If no files provided or empty input, respond with: "No code files found for review."
- Do NOT ask for code to be provided
- Do NOT suggest the user paste code
- Do NOT treat this as an interactive conversation
- Focus on the most impactful issues first"""
                },
                {
                    "role": "user", 
                    "content": f"""Review this React/TypeScript codebase. Provide specific, actionable feedback.

CODEBASE TO REVIEW:
```
{diff}
```

Analyze the code and provide feedback in the specified format. Focus on critical bugs, performance issues, and practical improvements."""
                }
            ],
            max_tokens=2000
        )

        comments = review.choices[0].message.content.strip()

    except Exception as e:
        comments = f"⚠️ GPT-4o review failed: {str(e)}"
        print(f"AI Review Error: {e}")

    if pr_number.startswith("manual") or pr_number.startswith("push"):
        run_type = "Manual" if pr_number.startswith("manual") else "Push"
        print(f"\n🤖 GPT-4o AI CODE REVIEW ({run_type}):")
        print("=" * 80)
        print(comments)
        print("=" * 80)
        return
    
    repo = os.getenv("GITHUB_REPOSITORY")
    token = os.getenv("GITHUB_TOKEN")
    
    if not repo or not token:
        print("⚠️ Missing GitHub repository or token")
        return
    
    # Update or create comment (will show timestamp on each update)
    update_or_create_comment(repo, token, pr_number, comments)
    
    # Save review output for issue creation
    with open("ai_review_output.txt", "w") as f:
        f.write(comments)

if __name__ == "__main__":
    diff_file = sys.argv[1]
    pr_number = sys.argv[2]
    main(diff_file, pr_number)
