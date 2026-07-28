#!/usr/bin/env python3
"""
CoChem-CORE: Stage 0.0 - Setup Orchestrator
Sequentially executes the 7-Phase Initialization pipeline.
Enforces strictly gated execution, directory integrity checks, and automated diagnostic recovery instructions on failure.
"""

import os
import sys
import subprocess
from pathlib import Path

# ---------------------------------------------------------
# UI & LOGGING PROTOCOLS
# ---------------------------------------------------------
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

# Define the exact execution sequence matching the CoChem architecture
PHASE_MANIFEST = [
    (1, ".\cochem_setup\cochem_setup_phase_1.py", "OS/Hypervisor Audit"),
    (2, ".\cochem_setup\cochem_setup_phase_2.py", "Hardware, RAM, & CPU Mapping"),
    (3, ".\cochem_setup\cochem_setup_phase_3.py", "Engine Binary Validation (ORCA, OpenMPI, g-xTB)"),
    (4, ".\cochem_setup\cochem_setup_phase_4.py", "Silo Generation & Python 3.11 Enforcer"),
    (5, ".\cochem_setup\cochem_setup_phase_5.py", "IPC Config Lock & Workspace Sweep"),
    (10, ".\cochem_setup\cochem_setup_phase_10.py", "Eckart Frame & MolSym Intake"),
    (11, ".\cochem_setup\cochem_setup_phase_11.py", "Memory Router & Adaptive Tiering")
]

def verify_integrity(base_dir: Path) -> bool:
    print(f"{Colors.OKCYAN}Verifying Orchestrator Integrity...{Colors.ENDC}")
    for _, script, _ in PHASE_MANIFEST:
        target = base_dir / script
        if not target.exists():
            print(f"{Colors.FAIL}❌ Missing Phase Script: {script}{Colors.ENDC}")
            return False
    return True

def run_phase(base_dir: Path, phase_num: int, script_name: str, desc: str) -> bool:
    script_path = base_dir / script_name
    print(f"\n{Colors.HEADER}>>> Executing Phase {phase_num}: {desc}{Colors.ENDC}")
    try:
        # Stream output natively so user can see progress
        result = subprocess.run([sys.executable, str(script_path)], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n{Colors.FAIL}❌ Phase {phase_num} Failed with Exit Code {e.returncode}{Colors.ENDC}")
        print(f"{Colors.WARNING}----------------------------------------{Colors.ENDC}")
        print(f"{Colors.BOLD}Diagnostic Recovery Instructions:{Colors.ENDC}")
        print(f"1. {Colors.BOLD}Inspect Trailing Log:{Colors.ENDC} Check Logs/cochem_phase{phase_num}_*.log for specific traceback.")
        print(f"2. {Colors.BOLD}Isolate Failure Phase:{Colors.ENDC} The last successful state JSON in cochem_setup/ indicates where the cascade halted.")
        print(f"3. {Colors.BOLD}Resource Check:{Colors.ENDC} Do NOT bypass thermal or memory checks. If Phase 2 or 4 failed, ensure your host has sufficient unallocated RAM.")
        print(f"4. {Colors.BOLD}Silo Fallback:{Colors.ENDC} If this occurred during Phase 4 (Silo Generation), allow the process to finish if it is attempting dynamic environment generation before manually killing.")
        print(f"{Colors.WARNING}----------------------------------------{Colors.ENDC}\n")
        return False

def main():
    print(f"{Colors.BOLD}=============================================================={Colors.ENDC}")
    print(f"{Colors.BOLD}            CoChem-CORE 7-Phase Orchestrator                  {Colors.ENDC}")
    print(f"{Colors.BOLD}=============================================================={Colors.ENDC}\n")
    
    base_dir = Path(__file__).parent.absolute()
    
    if not verify_integrity(base_dir):
        sys.exit(1)
        
    for phase_num, script_name, desc in PHASE_MANIFEST:
        success = run_phase(base_dir, phase_num, script_name, desc)
        if not success:
            sys.exit(1)
            
    print(f"\n{Colors.OKGREEN}{Colors.BOLD}✅============================================================{Colors.ENDC}")
    print(f"{Colors.OKGREEN}{Colors.BOLD}      ALL PHASES COMPLETED. REGISTRY OFFICIALLY LOCKED.       {Colors.ENDC}")
    print(f"{Colors.OKGREEN}{Colors.BOLD}==============================================================✅{Colors.ENDC}\n")

if __name__ == "__main__":
    main()