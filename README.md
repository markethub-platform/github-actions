# MarketHub GitHub Actions

Centralized GitHub Actions workflows and composite actions for the MarketHub platform.

## 🎯 Purpose

This repository provides reusable workflows and composite actions that can be used across all MarketHub repositories (web, mobile, backend) to ensure consistent CI/CD practices.

## 📦 What's Included

### Composite Actions

#### `actions/extract-code`
Extracts source code files for AI review.
- Supports: TypeScript, JavaScript, Python, Dart
- Automatically filters by file extension
- Truncates if too large

#### `actions/ai-review`
Runs AI-powered code review using Claude Sonnet or GPT-4.
- Reviews entire codebase
- Creates PR comments
- Optionally creates GitHub issues for critical findings

#### `actions/verify-fixes`
Verifies if AI-reported issues have been fixed.
- Uses 3-confirmation system
- Prevents false positives
- Auto-closes with high confidence

### Reusable Workflows

#### `.github/workflows/ai-code-review.yml`
Complete AI code review workflow that orchestrates all composite actions.

**Usage:**
```yaml
jobs:
  ai-review:
    uses: markethub-platform/github-actions/.github/workflows/ai-code-review.yml@v1
    with:
      language: typescript
      source_dir: frontend/src
      ai_model: claude
    secrets:
      ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
      GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

#### `.github/workflows/code-quality-typescript.yml`
TypeScript/JavaScript quality checks (ESLint, TypeScript, Tests).

**Usage:**
```yaml
jobs:
  quality:
    uses: markethub-platform/github-actions/.github/workflows/code-quality-typescript.yml@v1
    with:
      working_directory: frontend
      node_version: '20'
```

#### `.github/workflows/security-audit.yml`
Security vulnerability scanning.

**Usage:**
```yaml
jobs:
  security:
    uses: markethub-platform/github-actions/.github/workflows/security-audit.yml@v1
    with:
      language: npm
      working_directory: frontend
      fail_on_vulnerabilities: true
```

## 🚀 How to Use

### 1. Call from Your Repository

In your repository's `.github/workflows/ci.yml`:

```yaml
name: CI/CD

on:
  pull_request:
  push:
    branches: [main]

jobs:
  # All run in parallel
  ai-review:
    uses: markethub-platform/github-actions/.github/workflows/ai-code-review.yml@v1
    with:
      language: typescript
      source_dir: src
    secrets: inherit

  code-quality:
    uses: markethub-platform/github-actions/.github/workflows/code-quality-typescript.yml@v1
    with:
      working_directory: .
    
  security:
    uses: markethub-platform/github-actions/.github/workflows/security-audit.yml@v1
    with:
      language: npm
```

### 2. Version Pinning

- `@v1` - Recommended (auto-updates to latest v1.x.x)
- `@v1.0.0` - Exact version (for stability)
- `@main` - Bleeding edge (for testing)

## 📁 Repository Structure

```
github-actions/
├── actions/                          # Composite actions
│   ├── extract-code/
│   │   └── action.yml
│   ├── ai-review/
│   │   ├── action.yml
│   │   └── scripts/
│   │       ├── ai_review_claude_sonnet.py
│   │       ├── ai_review_gpt4o.py
│   │       ├── ai_review_to_issues.py
│   │       └── requirements.txt
│   └── verify-fixes/
│       ├── action.yml
│       └── scripts/
│           └── ai_verify_fixes.py
│
└── .github/workflows/                # Reusable workflows
    ├── ai-code-review.yml
    ├── code-quality-typescript.yml
    └── security-audit.yml
```

## 🔧 Maintenance

### Adding New Workflows
1. Create workflow in `.github/workflows/`
2. Use `workflow_call` trigger
3. Document inputs/secrets
4. Test thoroughly
5. Tag new version

### Updating Existing Workflows
1. Make changes on a branch
2. Test with `@branch-name` from a test repo
3. Once stable, merge to `main`
4. Tag new version if breaking changes

### Versioning
- `v1.x.x` - Backwards compatible features/fixes
- `v2.x.x` - Breaking changes requiring migration

## 📝 License

Private - MarketHub Platform

## 👥 Maintainers

MarketHub Platform Team
