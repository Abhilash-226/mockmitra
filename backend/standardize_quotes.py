import re

file_path = r'c:\Users\ashad\Desktop\abhilash\Projects\MockMitra\backend\pyq_papers\ts_eamcet\ts_eamcet_2020_7.yaml'
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
in_dq = False
dq_buffer = []

for line in lines:
    stripped = line.strip()
    if not in_dq:
        # Check if line starts with key: "
        match = re.search(r'^(\s+\w+):\s*"(.*)$', line)
        if match:
            indent_prefix = match.group(1)
            content_start = match.group(2)
            if content_start.endswith('"'):
                # Single line " ... "
                # Convert to ' ... ' if it has \
                if '\\' in content_start:
                    inner = content_start[:-1].replace("'", "''")
                    line = f"{indent_prefix}: '{inner}'\n"
                new_lines.append(line)
            else:
                # Multi-line start
                in_dq = True
                dq_buffer = [content_start]
                dq_indent_prefix = indent_prefix
        else:
            new_lines.append(line)
    else:
        # We are inside a double quote.
        # Check if it ends. It might end with " or ' (due to error) or just next field.
        # Usually it ends with " or ' followed by newline
        if stripped.endswith('"') or stripped.endswith("'"):
            dq_buffer.append(stripped[:-1])
            # Combine all bits. Remove the OCR alignment \ if present at end of individual bits
            combined = "".join(dq_buffer)
            # Remove line-continuation \
            combined = combined.replace('\\\n', '').replace('\\ ', ' ').replace('\\', '\\')
            combined = combined.replace("'", "''")
            
            new_lines.append(f"{dq_indent_prefix}: '{combined}'\n")
            in_dq = False
            dq_buffer = []
        else:
            dq_buffer.append(stripped)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Multiline quote standardization complete.")
