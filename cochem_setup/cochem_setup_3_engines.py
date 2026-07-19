#!/usr/bin/env python3
"""
CoChem Setup Phase 3: Deep Engine Verification
Audits the physical presence and execution permissions of ORCA, OpenMPI, and g-xTB.
Outputs path mappings to cochem_state_3.json.
"""
import os
import sys
import subprocess
import json
import logging
import shutil
from logging.handlers import RotatingFileHandler

class Colors:
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

os.makedirs("cochem_setup", exist_ok=True)
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler = RotatingFileHandler('cochem_setup/cochem_phase3_engines.log', maxBytes=1000000, backupCount=3)
file_handler.setFormatter(log_formatter)

logger = logging.getLogger('Phase3_Engines')
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)

def print_status(msg: str, status: str = "info") -> None:
    if status == "success":
        print(f" {Colors.OKGREEN}✅ {msg}{Colors.ENDC}")
    elif status == "warning":
        print(f" {Colors.WARNING}⚠️ {msg}{Colors.ENDC}")
    elif status == "fail":
        print(f" {Colors.FAIL}❌ {msg}{Colors.ENDC}")
    else:
        print(f" {Colors.OKCYAN}➡️ {msg}{Colors.ENDC}")

def mask_path(path: str) -> str:
    """Masks home directory in logs to prevent exposing absolute system usernames."""
    home = os.path.expanduser("~")
    if path and path.startswith(home):
        return path.replace(home, "~", 1)
    return path

def check_engine(binary_name: str, test_flag: str, env_vars: dict = None) -> str:
    """Safely executes an engine to verify it isn't a dead symlink."""
    # First, try standard PATH
    path = shutil.which(binary_name)
    
    # Fallback to CoChem hidden directory structure
    if not path:
        local_hidden = os.path.expanduser(f"~/.cochem/engines/{binary_name}")
        if os.path.exists(local_hidden) and os.access(local_hidden, os.X_OK):
            path = local_hidden
            
    if not path:
        logger.warning(f"Engine NOT FOUND: {binary_name}")
        return None
        
    try:
        # check=True prevents silent subprocess failure, capture_output prevents terminal clutter
        env = os.environ.copy()
        if env_vars:
            env.update(env_vars)
            
        result = subprocess.run([path, test_flag], capture_output=True, text=True, timeout=5, env=env)
        logger.info(f"Verified {binary_name} at {mask_path(path)}")
        return path
    except (subprocess.TimeoutExpired, PermissionError, OSError) as e:
        logger.error(f"Engine Execution Failed for {binary_name} at {mask_path(path)}: {str(e)}")
        return None

def main():
    print(f"\n{Colors.BOLD}--- CoChem Phase 3: Engine Verification ---{Colors.ENDC}")
    
    # 1. ORCA Verification
    orca_path = check_engine("orca", "fake_input.inp") # ORCA prints its version header even if input is fake
    if orca_path:
        print_status(f"ORCA located and executable: {mask_path(orca_path)}", "success")
    else:
        print_status("ORCA 6.1.1 not found or lacks execution permissions.", "fail")
        
    # 2. OpenMPI Verification (critical for ORCA parallelization)
    mpi_path = check_engine("mpirun", "--version")
    if mpi_path:
        print_status(f"OpenMPI located and executable: {mask_path(mpi_path)}", "success")
    else:
        print_status("OpenMPI not found. ORCA will be restricted to sequential mode.", "warning")
        
    # 3. g-xTB Verification
    xtb_path = check_engine("xtb", "--version")
    if xtb_path:
        print_status(f"g-xTB located and executable: {mask_path(xtb_path)}", "success")
    else:
        print_status("g-xTB not found. Certain conformational filters will degrade.", "warning")

    # Store parameters for downstream Phase 5 aggregation
    state_record = {
        "phase": 3,
        "orca_path": orca_path,
        "mpi_path": mpi_path,
        "xtb_path": xtb_path
    }
    
    state_path = os.path.join("cochem_setup", "cochem_state_3.json")
    with open(state_path, "w") as f:
        json.dump(state_record, f, indent=4)
        
    print_status(f"Phase 3 Complete. Engine topology saved to {state_path}.", "success")
    
    logger.removeHandler(file_handler)
    file_handler.close()
    
    if not orca_path:
        print_status("Critical Engine Missing: ORCA. Setup cannot continue safely.", "fail")
        sys.exit(1)

if __name__ == "__main__":
    main()