import yaml
import os

filepath = r'c:\Users\ashad\Desktop\abhilash\Projects\MockMitra\backend\pyq_papers\ts_eamcet\ts_eamcet_2023_5.yaml'

with open(filepath, 'r', encoding='utf-8') as f:
    data = yaml.safe_load(f)
    if isinstance(data, dict):
        questions = data.get('questions', [])
    else:
        questions = data

    for q in questions:
        options = q.get('options', {})
        for key, val in options.items():
            if not isinstance(val, str):
                print(f"Question ID {q.get('id')} Option {key}: {val} (Type: {type(val)})")
