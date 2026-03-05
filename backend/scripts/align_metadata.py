import yaml
import os

# Paths
CONFIG_PATH = r"backend/exam_configs/ts_eamcet.yaml"
PAPERS_DIR = r"backend/pyq_papers/ts_eamcet"
FILES_TO_PROCESS = [
    "ts_eamcet_2020_1.yaml", "ts_eamcet_2020_2.yaml", "ts_eamcet_2020_3.yaml",
    "ts_eamcet_2020_4.yaml", "ts_eamcet_2020_5.yaml", "ts_eamcet_2020_6.yaml",
    "ts_eamcet_2020_7.yaml", "ts_eamcet_2021_2.yaml", "ts_eamcet_2021_3.yaml",
    "ts_eamcet_2021_4.yaml", "ts_eamcet_2021_5.yaml", "ts_eamcet_2021_6.yaml"
]

def load_config(path):
    with open(path, 'r') as f:
        return yaml.safe_load(f)

def get_mapping(config):
    # Mapping topic -> [ (subject_name, section_name), ... ]
    mapping = {} 
    
    for subj in config['subjects']:
        subj_name = subj['name']
        for sect in subj['sections']:
            sect_name = sect['name']
            for topic in sect['topics']:
                if topic not in mapping:
                    mapping[topic] = []
                mapping[topic].append((subj_name, sect_name))
    return mapping

def get_subject_by_id(qid):
    if 1 <= qid <= 80:
        return "Mathematics"
    elif 81 <= qid <= 120:
        return "Physics"
    elif 121 <= qid <= 160:
        return "Chemistry"
    return None

def process_file(file_path, mapping):
    print(f"Processing {file_path}...")
    with open(file_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    updated_fields = 0
    subject_counts = {"Mathematics": 0, "Physics": 0, "Chemistry": 0}
    
    for q in data.get('questions', []):
        qid = q.get('id')
        topic = q.get('topic')
        expected_subject = get_subject_by_id(qid)
        
        if topic in mapping:
            options = mapping[topic]
            # Find the option that matches the expected subject
            matched = False
            for opt_subj, opt_sect in options:
                if opt_subj == expected_subject:
                    if q.get('subject') != opt_subj:
                        q['subject'] = opt_subj
                        updated_fields += 1
                    if q.get('section') != opt_sect:
                        q['section'] = opt_sect
                        updated_fields += 1
                    matched = True
                    break
            
            # If no match for expected subject, pick the first one but keep the current subject if possible
            if not matched:
                first_subj, first_sect = options[0]
                if q.get('subject') not in [s for s, _ in options]:
                    q['subject'] = first_subj
                    q['section'] = first_sect
                    updated_fields += 1
                else:
                    # Current subject is valid for this topic, just update section if needed
                    for s, sect in options:
                        if s == q.get('subject'):
                            if q.get('section') != sect:
                                q['section'] = sect
                                updated_fields += 1
                            break
        
        # Count for metadata update
        subj = q.get('subject')
        if subj in subject_counts:
            subject_counts[subj] += 1

    # Update metadata sections
    if 'sections' in data:
        for sect_meta in data['sections']:
            subj_name = sect_meta['name']
            if subj_name in subject_counts:
                sect_meta['question_count'] = subject_counts[subj_name]

    with open(file_path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, sort_keys=False, allow_unicode=True, width=1000)
    print(f"  Processed {file_path} ({updated_fields} fields updated)")

def main():
    config = load_config(CONFIG_PATH)
    mapping = get_mapping(config)
    
    for filename in FILES_TO_PROCESS:
        file_path = os.path.join(PAPERS_DIR, filename)
        if os.path.exists(file_path):
            process_file(file_path, mapping)
        else:
            print(f"Warning: {file_path} not found.")

if __name__ == "__main__":
    main()
