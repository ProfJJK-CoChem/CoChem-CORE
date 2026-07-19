#!/usr/bin/env python3
"""
CoChem Master Deployment Orchestrator
Sequentially triggers the CoChem environment initialization.
Halts gracefully if any sub-phase throws a fatal error.
"""
import os
import sys
import subprocess
import time

class Colors:
    HEADER = '\033[95m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_banner():
    print(f"\n{Colors.HEADER}{Colors.BOLD}======================================================{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD} CoChem Pipeline: Master Initialization {Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}======================================================{Colors.ENDC}\n")

def run_phase(script_name: str, phase_desc: str) -> bool:
    """Executes a setup phase and monitors its return code."""
    if not os.path.exists(script_name):
        print(f"{Colors.FAIL}❌ FATAL: Cannot find {script_name} in the root directory.{Colors.ENDC}")
        return False
    
    print(f"{Colors.OKGREEN}▶ Starting {phase_desc} ({script_name})...{Colors.ENDC}")
    try:
        # check=True forces a CalledProcessError if the script fails, protecting downstream steps
        subprocess.run([sys.executable, script_name], check=True)
        print(f"{Colors.OKGREEN}✅ Successfully completed {phase_desc}.{Colors.ENDC}\n")
        return True
    except subprocess.CalledProcessError as e:
        print(f"{Colors.FAIL}❌ FATAL: {script_name} failed with return code {e.returncode}.{Colors.ENDC}")
        return False
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}⚠️ Pipeline forcefully halted by user.{Colors.ENDC}")
        return False

def main():
    print_banner()
    
    # Official CoChem Topology 1 Sequence
    phases = [
        ("cochem_setup_1_sys.py", "Phase 1: OS & Hypervisor Audit"),
        ("cochem_setup_2_hw.py", "Phase 2: Hardware, RAM, & CPU Mapping"),
        ("cochem_setup_3_engines.py", "Phase 3: Deep Engine Verification"),
        ("cochem_setup_4_silos.py", "Phase 4: Dynamic Silo Generation"),
        ("cochem_setup_5_finalize.py", "Phase 5: IPC Config Lock & Finalize"),
        ("cochem_setup_10_intake_align.py", "Phase 10: Intake & Alignment"),
        ("cochem_setup_11_memory_router.py", "Phase 11: Memory Router & Tiering")
    ]
    
    for script, desc in phases:
        # If a phase is missing, we log it and halt to prevent silent fallback errors
        if not run_phase(script, desc):
            print(f"{Colors.WARNING}⚠️ Pipeline halted during {desc}. Fix errors and restart.{Colors.ENDC}")
            sys.exit(1)
            
    print(f"{Colors.HEADER}{Colors.BOLD}======================================================{Colors.ENDC}")
    print(f"{Colors.OKGREEN}{Colors.BOLD} CoChem Setup Successfully Completed! {Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}======================================================{Colors.ENDC}\n")

if __name__ == "__main__":
    # Ensure the user is running this from the correct root directory
    if not os.path.exists("cochem_setup_1_sys.py"):
        print(f"{Colors.FAIL}Error: setup.py must be run from the directory containing the cochem_setup_*.py scripts.{Colors.ENDC}")
        sys.exit(1)
    main()