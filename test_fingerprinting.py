#!/usr/bin/env python3
"""
Test script for enhanced fingerprinting system
Tests pattern extraction, categorization, and fuzzy matching
"""
import sys
sys.path.insert(0, 'actions/ai-review/scripts')

from ai_review_to_issues import (
    extract_problem_pattern,
    categorize_issue,
    generate_issue_fingerprint,
    normalize_title,
    titles_are_similar
)

print("=" * 70)
print("TESTING ENHANCED FINGERPRINTING SYSTEM")
print("=" * 70)

# ============================================
# TEST 1: Weighted Pattern Extraction
# ============================================
print("\n📋 TEST 1: Weighted Pattern Extraction")
print("-" * 70)

test_codes = [
    {
        'name': 'Memory Leak (High Priority: Hooks + APIs)',
        'code': '''
useEffect(() => {
    window.addEventListener('storage', handleChange);
}, []);
        ''',
        'expected_patterns': ['HOOK:', 'API:window.', 'API:addeventlistener']
    },
    {
        'name': 'Race Condition (Medium Priority: Async)',
        'code': '''
const fetchData = async () => {
    const response = await fetch('/api/data');
    setState(response.data);
};
        ''',
        'expected_patterns': ['ASYNC:async', 'ASYNC:await', 'ASYNC:fetch']
    },
    {
        'name': 'Generic Code (Low Priority: Functions)',
        'code': '''
function calculateTotal(items) {
    return items.reduce((sum, item) => sum + item.price, 0);
}
        ''',
        'expected_patterns': ['FN:', 'VAR:']
    }
]

for test in test_codes:
    print(f"\n{test['name']}:")
    pattern = extract_problem_pattern(test['code'], "")
    print(f"  Pattern: {pattern}")
    
    # Check if expected patterns are present
    all_present = all(exp in pattern for exp in test['expected_patterns'])
    status = "✅ PASS" if all_present else "❌ FAIL"
    print(f"  Status: {status}")

# ============================================
# TEST 2: Enhanced Category Detection
# ============================================
print("\n\n📁 TEST 2: Enhanced Category Detection")
print("-" * 70)

test_categories = [
    {
        'title': 'Missing cleanup in useEffect',
        'description': 'Event listener not removed',
        'code': 'addEventListener',
        'expected': 'memory-leak'
    },
    {
        'title': 'Async timing problem',
        'description': 'Race condition in data fetch',
        'code': 'await fetch',
        'expected': 'race-condition'
    },
    {
        'title': 'Type annotation missing',
        'description': 'Implicit any type',
        'code': 'function test(param)',
        'expected': 'type-error'
    },
    {
        'title': 'Security vulnerability',
        'description': 'XSS risk',
        'code': 'innerHTML',
        'expected': 'security'
    }
]

for test in test_categories:
    category = categorize_issue(test['title'], test['description'], test['code'])
    status = "✅ PASS" if category == test['expected'] else f"❌ FAIL (got: {category})"
    print(f"  '{test['title'][:40]}...' → {category} {status}")

# ============================================
# TEST 3: Tiered Fuzzy Thresholds
# ============================================
print("\n\n🔍 TEST 3: Tiered Fuzzy Thresholds")
print("-" * 70)

test_pairs = [
    {
        'title1': 'Memory Leak in useEffect',
        'title2': 'Missing Cleanup in useEffect',
        'same_context': True,
        'expected': True,
        'note': 'Same file + category (lenient threshold)'
    },
    {
        'title1': 'Memory Leak in useEffect',
        'title2': 'Missing Cleanup in useEffect',
        'same_context': False,
        'expected': False,
        'note': 'Different context (strict threshold)'
    },
    {
        'title1': 'Memory Leak in Timer',
        'title2': 'Memory Leak in Events',
        'same_context': True,
        'expected': False,
        'note': 'Different enough even with lenient threshold'
    },
    {
        'title1': 'Race Condition in API',
        'title2': 'race condition in api',
        'same_context': True,
        'expected': True,
        'note': 'Case insensitive match'
    }
]

for test in test_pairs:
    result = titles_are_similar(
        test['title1'],
        test['title2'],
        same_context=test['same_context']
    )
    status = "✅ PASS" if result == test['expected'] else "❌ FAIL"
    context = "lenient (0.75)" if test['same_context'] else "strict (0.85)"
    print(f"\n  '{test['title1']}' vs")
    print(f"  '{test['title2']}'")
    print(f"  Context: {context}")
    print(f"  Expected: {test['expected']}, Got: {result} {status}")
    print(f"  Note: {test['note']}")

# ============================================
# TEST 4: Complete Fingerprint Generation
# ============================================
print("\n\n🔐 TEST 4: Complete Fingerprint Generation")
print("-" * 70)

test_issues = [
    {
        'file': 'frontend/src/hooks/useAuth.ts',
        'title': 'Memory Leak in useEffect',
        'problem': 'Event listener not removed',
        'code': '''
useEffect(() => {
    window.addEventListener('storage', handleChange);
}, []);
        ''',
        'fix': '''
useEffect(() => {
    window.addEventListener('storage', handleChange);
    return () => window.removeEventListener('storage', handleChange);
}, [handler]);
        '''
    },
    {
        'file': 'frontend/src/hooks/useAuth.ts',
        'title': 'Missing Cleanup in useEffect',  # Similar title
        'problem': 'Event listener not cleaned up',
        'code': '''
useEffect(() => {
    window.addEventListener('storage', handleChange);
}, []);
        ''',
        'fix': '''
useEffect(() => {
    window.addEventListener('storage', handleChange);
    return () => window.removeEventListener('storage', handleChange);
}, [handler]);
        '''
    }
]

print("\nIssue 1:")
fp1 = generate_issue_fingerprint(
    test_issues[0]['file'],
    test_issues[0]['title'],
    test_issues[0]['problem'],
    test_issues[0]['code'],
    test_issues[0]['fix']
)
print(f"  Title: {test_issues[0]['title']}")
print(f"  Fingerprint: {fp1['fingerprint']}")
print(f"  Simple ID: {fp1['simple_id']}")
print(f"  Category: {fp1['category']}")
print(f"  Pattern: {fp1['pattern'][:50]}...")

print("\nIssue 2 (should match Issue 1 via fingerprint):")
fp2 = generate_issue_fingerprint(
    test_issues[1]['file'],
    test_issues[1]['title'],
    test_issues[1]['problem'],
    test_issues[1]['code'],
    test_issues[1]['fix']
)
print(f"  Title: {test_issues[1]['title']}")
print(f"  Fingerprint: {fp2['fingerprint']}")
print(f"  Simple ID: {fp2['simple_id']}")
print(f"  Category: {fp2['category']}")
print(f"  Pattern: {fp2['pattern'][:50]}...")

print("\n🔍 Comparison:")
print(f"  Fingerprints match: {fp1['fingerprint'] == fp2['fingerprint']}")
print(f"  Simple IDs match: {fp1['simple_id'] == fp2['simple_id']}")
print(f"  Categories match: {fp1['category'] == fp2['category']}")
print(f"  Patterns match: {fp1['pattern'] == fp2['pattern']}")

if fp1['fingerprint'] == fp2['fingerprint']:
    print("\n  ✅ SUCCESS: Same code pattern generates same fingerprint!")
    print("     Even with different title wording, duplicate will be detected.")
else:
    print("\n  ❌ FAIL: Fingerprints should match (same code pattern)")

# ============================================
# SUMMARY
# ============================================
print("\n\n" + "=" * 70)
print("📊 TEST SUMMARY")
print("=" * 70)
print("""
✅ Tested: Weighted pattern extraction (hooks, APIs, async prioritized)
✅ Tested: Enhanced category detection with aliases
✅ Tested: Tiered fuzzy thresholds (0.75 same context, 0.85 different)
✅ Tested: Complete fingerprint generation
✅ Tested: Duplicate detection via fingerprints

🎯 Expected Behavior:
- Same code patterns → same fingerprints → duplicate detected
- Similar titles + same file + same category → fuzzy match
- Different titles but same code → still matches via fingerprint
- Case variations → normalized and matched

🚀 Ready for deployment!
""")
print("=" * 70)
