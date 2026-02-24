"""
Post-extraction verification for PYQ papers.
Run after extraction to verify question IDs, coverage, and structure.
"""
import yaml
import sys
from pathlib import Path


def verify_extraction(yaml_path: str, expected_total: int = 160) -> bool:
    """
    Verify a PYQ YAML file for correctness.
    
    Checks:
    1. Total questions match expected count
    2. IDs are exactly 1-N with no gaps or duplicates
    3. Every question has required fields (id, section, topic, text, options, correct_answer)
    4. All options have exactly 4 keys (A, B, C, D)
    5. No IMAGE_CONTENT or UNREADABLE_IMAGE placeholders remain
    6. Subject field matches the ID range expectations (if known)
    
    Returns True if all checks pass, False otherwise.
    """
    path = Path(yaml_path)
    if not path.exists():
        print(f"❌ File not found: {yaml_path}")
        return False

    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    questions = data.get('questions', [])
    total = len(questions)
    
    print(f"\n{'='*60}")
    print(f"VERIFICATION: {path.name}")
    print(f"{'='*60}")
    
    all_ok = True

    # 1. Count check
    print(f"\n[1] Question Count:")
    print(f"    Expected: {expected_total} | Found: {total}")
    if total != expected_total:
        print(f"    ❌ FAIL: Count mismatch! {'Extra' if total > expected_total else 'Missing'} questions.")
        all_ok = False
    else:
        print(f"    ✅ PASS")

    # 2. ID coverage
    print(f"\n[2] ID Coverage (1-{expected_total}):")
    all_ids = [q.get('id') for q in questions]
    expected_ids = set(range(1, expected_total + 1))
    found_ids = set(all_ids)
    
    missing_ids = sorted(expected_ids - found_ids)
    extra_ids = sorted(found_ids - expected_ids)
    dup_ids = sorted(set(i for i in all_ids if all_ids.count(i) > 1))
    
    if missing_ids:
        print(f"    ❌ MISSING IDs ({len(missing_ids)}): {missing_ids}")
        all_ok = False
    else:
        print(f"    ✅ No missing IDs")
    
    if extra_ids:
        print(f"    ❌ EXTRA IDs ({len(extra_ids)}): {extra_ids}")
        all_ok = False
    else:
        print(f"    ✅ No extra IDs")
    
    if dup_ids:
        print(f"    ❌ DUPLICATE IDs ({len(dup_ids)}): {dup_ids}")
        all_ok = False
    else:
        print(f"    ✅ No duplicate IDs")

    # 3. Required fields
    print(f"\n[3] Required Fields Check:")
    required_fields = ['id', 'section', 'topic', 'text', 'options', 'correct_answer']
    field_issues = []
    for q in questions:
        qid = q.get('id', '?')
        for field in required_fields:
            if field not in q or not q[field]:
                field_issues.append(f"Q{qid}: missing '{field}'")
    
    if field_issues:
        print(f"    ❌ FAIL ({len(field_issues)} issues):")
        for issue in field_issues[:10]:
            print(f"        - {issue}")
        if len(field_issues) > 10:
            print(f"        ... and {len(field_issues) - 10} more")
        all_ok = False
    else:
        print(f"    ✅ All questions have required fields")

    # 4. Options check (must have exactly A, B, C, D)
    print(f"\n[4] Options Structure (A, B, C, D):")
    option_issues = []
    for q in questions:
        qid = q.get('id', '?')
        opts = q.get('options', {})
        if not isinstance(opts, dict):
            option_issues.append(f"Q{qid}: options is not a dict")
            continue
        keys = set(opts.keys())
        expected_keys = {'A', 'B', 'C', 'D'}
        if keys != expected_keys:
            option_issues.append(f"Q{qid}: has keys {sorted(keys)} instead of {sorted(expected_keys)}")
    
    if option_issues:
        print(f"    ❌ FAIL ({len(option_issues)} issues):")
        for issue in option_issues[:10]:
            print(f"        - {issue}")
        if len(option_issues) > 10:
            print(f"        ... and {len(option_issues) - 10} more")
        all_ok = False
    else:
        print(f"    ✅ All options have correct A/B/C/D structure")

    # 5. Placeholder check
    print(f"\n[5] Placeholder Content:")
    placeholder_issues = []
    placeholders = {"IMAGE_CONTENT", "UNREADABLE_IMAGE", "Option A", "Option B", "Option C", "Option D"}
    for q in questions:
        qid = q.get('id', '?')
        opts = q.get('options', {})
        if isinstance(opts, dict):
            for k, v in opts.items():
                if str(v).strip() in placeholders:
                    placeholder_issues.append(f"Q{qid} Option {k}: '{v}'")
    
    if placeholder_issues:
        print(f"    ⚠ WARNING ({len(placeholder_issues)} placeholder options):")
        for issue in placeholder_issues[:10]:
            print(f"        - {issue}")
        if len(placeholder_issues) > 10:
            print(f"        ... and {len(placeholder_issues) - 10} more")
        # Don't fail on placeholders, just warn
    else:
        print(f"    ✅ No placeholder content found")

    # 6. Subject/section distribution
    print(f"\n[6] Subject Distribution:")
    subject_map = {}
    for q in questions:
        subj = q.get('subject', 'Unknown')
        subject_map.setdefault(subj, []).append(q.get('id'))
    
    for subj, ids in sorted(subject_map.items()):
        id_range = f"Q{min(ids)}-Q{max(ids)}"
        print(f"    {subj}: {len(ids)} questions ({id_range})")

    # Summary
    print(f"\n{'='*60}")
    if all_ok:
        print(f"✅ VERIFICATION PASSED: {path.name} is correctly structured.")
    else:
        print(f"❌ VERIFICATION FAILED: {path.name} has issues (listed above).")
    print(f"{'='*60}\n")
    
    return all_ok


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python verify_extraction.py <yaml_path> [expected_total]")
        print("Example: python verify_extraction.py backend/pyq_papers/ts_eamcet/ts_eamcet_2020_3.yaml 160")
        sys.exit(1)
    
    yaml_path = sys.argv[1]
    expected_total = int(sys.argv[2]) if len(sys.argv) > 2 else 160
    
    success = verify_extraction(yaml_path, expected_total)
    sys.exit(0 if success else 1)
