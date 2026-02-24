import yaml
import sys
from pathlib import Path
import re

def deduplicate_options(yaml_path):
    print(f"Processing {yaml_path}...")
    with open(yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    if 'questions' not in data:
        print("No questions found.")
        return

    # Patterns to match 1, 2, 3, 4 or 1., 2., 3., 4. or 1. *, etc.
    num_pattern = re.compile(r'^(\d)[\.\s]*')
    
    modified_count = 0
    for q in data['questions']:
        if 'options' not in q:
            continue
            
        opts = q['options']
        new_opts = {}
        
        # Priority mapping: A, B, C, D
        # We'll first collect everything that looks like an option
        candidates = {}
        
        for k, v in opts.items():
            k_str = str(k).strip()
            # Clean up the key
            # Handle "1. ✓", "1. *", "1", "1."
            clean_k = k_str.replace('✓', '').replace('*', '').replace('.', '').strip()
            
            target_key = None
            if clean_k in ['A', 'B', 'C', 'D']:
                target_key = clean_k
            elif clean_k in ['1', '2', '3', '4']:
                target_key = chr(64 + int(clean_k)) # 1 -> A, 2 -> B, etc.
            
            if target_key:
                if target_key not in candidates:
                    candidates[target_key] = []
                candidates[target_key].append(str(v).strip())
        
        # Decide which value to keep for each target key
        final_opts = {}
        for k in ['A', 'B', 'C', 'D']:
            vals = candidates.get(k, [])
            if not vals:
                final_opts[k] = "UNREADABLE_IMAGE" # Placeholder
                continue
            
            # Filter out "IMAGE_CONTENT", "UNREADABLE_IMAGE", or empty strings
            valid_vals = [v for v in vals if v and v not in ["IMAGE_CONTENT", "UNREADABLE_IMAGE"]]
            if valid_vals:
                final_opts[k] = valid_vals[0] # Take the first valid one
            else:
                final_opts[k] = vals[0] # Fallback to whatever we had
        
        if final_opts != opts:
            q['options'] = final_opts
            modified_count += 1

    if modified_count > 0:
        with open(yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        print(f"  Fixed {modified_count} questions.")
    else:
        print("  No changes needed.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python deduplicate_options.py <yaml_path>")
        sys.exit(1)
        
    yaml_path = Path(sys.argv[1])
    if yaml_path.is_dir():
        for yf in yaml_path.glob("*.yaml"):
            deduplicate_options(yf)
    else:
        deduplicate_options(yaml_path)
