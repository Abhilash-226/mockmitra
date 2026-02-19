import sys
import os
from pathlib import Path

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.services.blueprint_loader import get_blueprint_loader

def debug_loader():
    loader = get_blueprint_loader()
    count = loader.load_all(force_reload=True)
    print(f"Total blueprints loaded: {count}")
    
    blueprints = loader.get_all_blueprints()
    exams = set(bp.exam for bp in blueprints if bp.exam)
    print(f"Unique exams found: {exams}")
    
    ts_eamcet_bps = [bp for bp in blueprints if bp.exam and "eamcet" in bp.exam.lower()]
    print(f"Blueprints containing 'eamcet': {len(ts_eamcet_bps)}")
    if ts_eamcet_bps:
        print(f"Sample exam field: '{ts_eamcet_bps[0].exam}'")
        
    # Test hierarchical filtering
    found_alg = loader.query_blueprints(exam="ts_eamcet", subject="Mathematics", section="Algebra")
    print(f"Blueprints found for 'ts_eamcet' > 'Mathematics' > 'Algebra': {len(found_alg)}")
    
    found_trig = loader.query_blueprints(exam="ts_eamcet", subject="Mathematics", section="Trigonometry")
    print(f"Blueprints found for 'ts_eamcet' > 'Mathematics' > 'Trigonometry': {len(found_trig)}")

    if found_alg:
        print(f"Sample Alg BP: ID={found_alg[0].id}, Section={found_alg[0].section}, Subject={found_alg[0].subject}")

if __name__ == "__main__":
    debug_loader()
