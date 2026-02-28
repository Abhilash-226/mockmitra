import yaml
import sys
from pathlib import Path

def fix_yaml(file_path):
    path = Path(file_path)
    if not path.exists():
        print(f"File not found: {file_path}")
        return

    with open(path, 'r', encoding='utf-8') as f:
        try:
            data = yaml.safe_load(f)
        except Exception as e:
            print(f"Error loading YAML {file_path}: {e}")
            return

    if not data or 'questions' not in data:
        print(f"No questions found in {file_path}")
        return

    questions = data['questions']
    fixed_count = 0

    for q in questions:
        qid = q.get('id')
        if not qid: continue

        # 1. Subject Normalization based on ID
        if 1 <= qid <= 80:
            q['subject'] = 'Mathematics'
        elif 81 <= qid <= 120:
            q['subject'] = 'Physics'
        elif 121 <= qid <= 160:
            q['subject'] = 'Chemistry'

        # 2. Options Cleanup (keys 1,2,3,4 -> A,B,C,D)
        opts = q.get('options', {})
        numeric_keys = ['1', '2', '3', '4']
        letter_keys = ['A', 'B', 'C', 'D']
        
        has_numeric = any(k in opts for k in numeric_keys)
        if has_numeric:
            # If A,B,C,D are empty/placeholder, prefer numeric values
            placeholders = ["None", "IMAGE_CONTENT", "UNREADABLE_IMAGE", ""]
            for i, nk in enumerate(numeric_keys):
                lk = letter_keys[i]
                val = opts.get(nk)
                if val and (opts.get(lk) in placeholders or lk not in opts):
                    opts[lk] = val
            
            # Remove all numeric keys
            for nk in numeric_keys:
                if nk in opts:
                    del opts[nk]
            fixed_count += 1

        # 3. Missing Topic/Text
        if not q.get('topic') or q.get('topic') == 'null':
            # Use chapter if available, else General
            q['topic'] = q.get('chapter') or 'General'
        
        if not q.get('text'):
            q['text'] = 'IMAGE_CONTENT'

    # 4. Update Metadata
    data['metadata']['total_questions'] = len(questions)

    # Save back
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    print(f"✅ Fixed {fixed_count} questions in {file_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fix_yaml_structure.py <file_or_dir>")
        sys.exit(1)
    
    input_path = Path(sys.argv[1])
    if input_path.is_file():
        fix_yaml(input_path)
    elif input_path.is_dir():
        for yfile in input_path.glob("*.yaml"):
            fix_yaml(yfile)
