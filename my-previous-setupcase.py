import shutil
import os

from pathlib import Path
from config import BASE_DIR, CASE_DIR, CORES_PER_CFD

def update_decompose_par_dict(case_dir, n_proc):
    """Update decomposeParDict with the correct number of processors"""
    decompose_file = case_dir / "system" / "decomposeParDict"
    
    if decompose_file.exists():
        # Read the file
        with open(decompose_file, 'r') as f:
            content = f.read()
        
        # Replace numberOfSubdomains
        import re
        content = re.sub(r'numberOfSubdomains\s+\d+;', f'numberOfSubdomains {n_proc};', content)
        
        # Write back
        with open(decompose_file, 'w') as f:
            f.write(content)

def setup_case(base_dir=BASE_DIR, case_dir=CASE_DIR, n_proc=None):
    if os.path.exists(case_dir):
        shutil.rmtree(case_dir)

    shutil.copytree(base_dir, case_dir)
    
    # Update decomposeParDict if n_proc specified
    if n_proc:
        update_decompose_par_dict(Path(case_dir), n_proc)
        print(f"Updated decomposeParDict to use {n_proc} processors")
    
    print(f"Copied {base_dir} → {case_dir} Completed")

if __name__ == "__main__":
    setup_case()
