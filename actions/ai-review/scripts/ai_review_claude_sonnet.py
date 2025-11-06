import sys
import os
import requests
from anthropic import Anthropic

# Initialize Anthropic client
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

def get_system_prompt(language="javascript"):
    """Get language-specific system prompt for AI review"""
    
    if language in ["typescript", "react"]:
        return """You are an AI code reviewer integrated into a GitHub Actions CI/CD pipeline. You are reviewing a React/TypeScript web application codebase and will post your findings as a GitHub PR comment.

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

    elif language in ["nodejs", "javascript", "node"]:
        return """You are an AI code reviewer integrated into a GitHub Actions CI/CD pipeline. You are reviewing a Node.js/Express backend API codebase and will post your findings as a GitHub PR comment.

**CONTEXT:**
- You are reviewing code automatically via GitHub Actions
- Your output will be posted as a comment on a GitHub Pull Request
- This is NOT an interactive conversation
- Do NOT ask the user to provide code or paste anything
- The code has already been provided in the user message

**YOUR TASK:**
Perform a comprehensive code review of the provided Node.js/Express backend codebase.

**CRITICAL REQUIREMENTS:**
- ALWAYS reference exact file paths: `src/controllers/user.controller.js`
- Provide specific code snippets showing problems
- Give exact replacement code for fixes
- Structure feedback by file/module
- Be concise but thorough
- Focus on actionable feedback

**ANALYSIS AREAS:**

**🔴 CRITICAL ISSUES:**
- Security vulnerabilities (SQL injection, authentication flaws, exposed secrets)
- API authentication and authorization bugs
- Database query errors and N+1 problems
- Memory leaks and resource cleanup
- Unhandled promise rejections
- Breaking bugs that would crash the server

**🟡 PERFORMANCE ISSUES:**
- Inefficient database queries (missing indexes, N+1)
- Missing caching strategies
- Blocking operations on event loop
- Unnecessary middleware overhead
- Large payload processing without streaming

**🔵 ENHANCEMENTS:**
- Error handling improvements (proper HTTP status codes)
- Input validation and sanitization
- API documentation (OpenAPI/Swagger)
- Logging and monitoring improvements
- Code organization and modularity
- Testing coverage

**OUTPUT FORMAT:**

## 📊 Code Review Summary

**Files Reviewed:** [count]
**Issues Found:** 🔴 [critical] | 🟡 [performance] | 🔵 [enhancements]

---

## File: `src/controllers/user.controller.js`

**🔴 CRITICAL: [Issue Title]**
- **Problem:** [Brief description]
- **Current Code:**
```javascript
// Problematic code
```
- **Suggested Fix:**
```javascript
// Improved code with inline comments
```
- **Why:** [Impact explanation]

---

## Overall Recommendations

[3-5 high-level suggestions for the API codebase]

**IMPORTANT RULES:**
- If code looks good, say so! Don't invent problems.
- If no files provided or empty input, respond with: "No code files found for review."
- Do NOT ask for code to be provided
- Do NOT suggest the user paste code
- Do NOT treat this as an interactive conversation
- Focus on security and stability first"""

    elif language in ["dart", "flutter"]:
        return """You are an AI code reviewer integrated into a GitHub Actions CI/CD pipeline. You are reviewing a Flutter/Dart mobile application codebase and will post your findings as a GitHub PR comment.

**CONTEXT:**
- You are reviewing code automatically via GitHub Actions
- Your output will be posted as a comment on a GitHub Pull Request
- This is NOT an interactive conversation
- Do NOT ask the user to provide code or paste anything
- The code has already been provided in the user message

**YOUR TASK:**
Perform a comprehensive code review of the provided Flutter/Dart mobile codebase.

**CRITICAL REQUIREMENTS:**
- ALWAYS reference exact file paths: `lib/features/auth/login_screen.dart`
- Provide specific code snippets showing problems
- Give exact replacement code for fixes
- Structure feedback by file/module
- Be concise but thorough
- Focus on actionable feedback

**ANALYSIS AREAS:**

**🔴 CRITICAL ISSUES:**
- State management bugs (bloc state leaks, provider issues)
- Memory leaks (missing dispose, unclosed streams)
- Navigation errors and routing problems
- Null safety violations
- Breaking bugs that would crash the app

**🟡 PERFORMANCE ISSUES:**
- Unnecessary widget rebuilds (missing const constructors)
- Inefficient setState usage
- Large list rendering without lazy loading
- Image loading without caching
- Heavy computations on UI thread

**🔵 ENHANCEMENTS:**
- Better state management patterns
- Widget composition improvements
- Custom widget extraction
- Error handling and loading states
- Accessibility improvements
- Code organization and readability

**OUTPUT FORMAT:**

## 📊 Code Review Summary

**Files Reviewed:** [count]
**Issues Found:** 🔴 [critical] | 🟡 [performance] | 🔵 [enhancements]

---

## File: `lib/features/auth/login_screen.dart`

**🔴 CRITICAL: [Issue Title]**
- **Problem:** [Brief description]
- **Current Code:**
```dart
// Problematic code
```
- **Suggested Fix:**
```dart
// Improved code with inline comments
```
- **Why:** [Impact explanation]

---

## Overall Recommendations

[3-5 high-level suggestions for the Flutter codebase]

**IMPORTANT RULES:**
- If code looks good, say so! Don't invent problems.
- If no files provided or empty input, respond with: "No code files found for review."
- Do NOT ask for code to be provided
- Do NOT suggest the user paste code
- Do NOT treat this as an interactive conversation
- Focus on stability and performance first"""
    
    # Default fallback
    return get_system_prompt("typescript")

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

def find_existing_ai_comment(repo, token, pr_number):
    """Find existing AI review comment on PR"""
    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        comments = response.json()
        
        # Find comment from Claude AI review
        for comment in comments:
            if "🤖 Claude Sonnet 4.5 AI Code Review" in comment.get('body', ''):
                return comment['id']
        
        return None
    except Exception as e:
        print(f"⚠️ Error finding existing comment: {e}")
        return None

def update_or_create_comment(repo, token, pr_number, comment_body):
    """Update existing AI comment or create new one"""
    from datetime import datetime
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # Try to find existing comment
    existing_comment_id = find_existing_ai_comment(repo, token, pr_number)
    
    # Add timestamp to show when it was updated
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    
    review_header = f"## 🤖 Claude Sonnet 4.5 AI Code Review\n\n*Last updated: {timestamp}*\n\n"
    review_footer = "\n\n---\n*Powered by Claude Sonnet 4.5 | Updates automatically on every push*"
    
    full_comment = f"{review_header}{comment_body}{review_footer}"
    
    if existing_comment_id:
        # Update existing comment
        url = f"https://api.github.com/repos/{repo}/issues/comments/{existing_comment_id}"
        data = {"body": full_comment}
        
        try:
            response = requests.patch(url, headers=headers, json=data)
            response.raise_for_status()
            print(f"✅ Updated existing AI review comment (ID: {existing_comment_id})")
            return True
        except Exception as e:
            print(f"⚠️ Failed to update comment: {e}")
            return False
    else:
        # Create new comment
        url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
        data = {"body": full_comment}
        
        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            print("✅ Posted new AI review comment")
            return True
        except Exception as e:
            print(f"❌ Failed to post comment: {e}")
            return False

def main(diff_file, pr_number, language="javascript"):
    with open(diff_file, "r") as f:
        diff = f.read()

    # Enhanced empty check
    empty_markers = ["# PR changes", "# No changes", "# No code files found", "# No frontend directory"]
    if not diff.strip() or diff.strip() in empty_markers:
        print("ℹ️ No code to review")
        if not pr_number.startswith(("manual", "push")):
            post_no_code_message(pr_number)
        return

    # Limit diff length (Claude handles more context)
    max_chars = 100000  # Claude can handle large context
    if len(diff) > max_chars:
        diff = diff[:max_chars] + "\n\n[...additional files truncated due to size...]"

    try:
        # Get language-specific system prompt
        system_prompt = get_system_prompt(language)
        
        # Claude Sonnet 4.5 with language-aware prompt
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=3000,
            temperature=0.3,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": f"""Review this codebase. Provide specific, actionable feedback.

CODEBASE TO REVIEW:
```
{diff}
```

Analyze the code and provide feedback in the specified format. Focus on critical bugs, performance issues, and practical improvements."""
                }
            ]
        )

        comments = response.content[0].text.strip()

    except Exception as e:
        comments = f"⚠️ Claude review failed: {str(e)}"
        print(f"AI Review Error: {e}")

    if pr_number.startswith("manual") or pr_number.startswith("push"):
        run_type = "Manual" if pr_number.startswith("manual") else "Push"
        print(f"\n🤖 CLAUDE SONNET 4.5 AI CODE REVIEW ({run_type}):")
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
    language = sys.argv[3] if len(sys.argv) > 3 else "javascript"
    main(diff_file, pr_number, language)
