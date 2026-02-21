import yaml
import sys
import os

def validate(filepath):
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return False
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            yaml.safe_load(f)
        print(f"YAML {filepath} loaded successfully!")
        return True
    except Exception as exc:
        print(f"Error in {filepath}:")
        print(exc)
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        validate(sys.argv[1])
    else:
        # Default to the one I'm working on
        validate(r'c:\Users\ashad\Desktop\abhilash\Projects\MockMitra\backend\pyq_papers\ts_eamcet\ts_eamcet_2022_2.yaml')
