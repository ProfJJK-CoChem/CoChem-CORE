#!/usr/bin/env python3
"""
CoChem Master Deployment Orchestrator
Sequentially triggers the CoChem environment initialization and micro-silo provisioning.
Halts gracefully if any sub-phase throws a fatal error, enforcing the authoritative 
cochem_system_config.json specification.
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
    print(f"{Colors.HEADER}{Colors.BOLD} CoChem Pipeline: Master Environment Orchestrator       {Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}======================================================{Colors.ENDC}\n")

def run_phase(script_name, description):
    print(f"{Colors.BOLD}[ORCHESTRATOR] Starting Phase: {description} ({script_name}){Colors.ENDC}")
    script_path = os.path.join("cochem_setup", script_name)
    
    if not os.path.exists(script_path):
        print(f"{Colors.FAIL}[FATAL] Missing required script: {script_path}{Colors.ENDC}")
        sys.exit(1)
        
    try:
        result = subprocess.run([sys.executable, script_path], check=True)
        print(f"{Colors.OKGREEN}[SUCCESS] Completed Phase: {description}{Colors.ENDC}\n")
    except subprocess.CalledProcessError as e:
        print(f"{Colors.FAIL}[FATAL] Phase failed with exit code {e.returncode}{Colors.ENDC}")
        sys.exit(1)

def main():
    print_banner()
    
    # Ensure cochem_setup directory exists
    if not os.path.exists("cochem_setup"):
        print(f"{Colors.FAIL}[FATAL] 'cochem_setup/' directory not found in current path.{Colors.ENDC}")
        sys.exit(1)

    phases = [
        ("cochem_setup_1_sys.py", "OS & Hypervisor Audit"),
        ("cochem_setup_2_hw.py", "Hardware, RAM, & CPU Topology Mapping"),
        ("cochem_setup_3_engines.py", "ORCA, OpenMPI, & xTB Binary Verification"),
        ("cochem_setup_4_silos.py", "Dynamic Micro-Silo Generation & Silo Binding"),
        ("cochem_setup_5_finalize.py", "Inter-Process Communication (IPC) Config Lock"),
        ("cochem_setup_10_intake_align.py", "Intake & Alignment Tooling (Eckart/MolSym)"),
        ("cochem_setup_11_memory_router.py", "Memory Router & Tiering Configuration")
    ]

    start_time = time.time()
    for script, desc in phases:
        run_phase(script, desc)
        
    elapsed = time.time() - start_time
    print(f"{Colors.OKGREEN}{Colors.BOLD}🏁 COCHEM-CORE DEPLOYMENT COMPLETE in {elapsed:.2f} seconds!{Colors.ENDC}")
    print(f"{Colors.BOLD}Authoritative registry written to: cochem_system_config.json{Colors.ENDC}")

if __name__ == "__main__":
    main()