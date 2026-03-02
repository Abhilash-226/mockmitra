import yaml
import sys

file_path = r'c:\Users\ashad\Desktop\abhilash\Projects\MockMitra\backend\pyq_papers\ts_eamcet\ts_eamcet_2020_7.yaml'
try:
    with open(file_path, 'r', encoding='utf-8') as f:
        yaml.safe_load(f)
    print("YAML is valid.")
except Exception as e:
    print(f"YAML Error: {e}")
    sys.exit(1)
