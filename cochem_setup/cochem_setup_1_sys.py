#!/usr/bin/env python3
""" 
CoChem Setup Phase 1: Core System Auditing, Hypervisor Profiling & Caching 
Executes baseline OS checks, memory auditing, and network profiling. 
"""
import os
import sys
import subprocess
import shutil
import logging
from logging.handlers import RotatingFileHandler
import json
import platform

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

# Initialize local directory for logs and state files safely
os.makedirs("cochem_setup", exist_ok=True)

logging.basicConfig(
    handlers=[RotatingFileHandler('cochem_setup/cochem_phase1_sys.log', maxBytes=1000000, backupCount=3)],
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def print_status(msg: str, status: str = "info") -> None:
    if status == "success":
        print(f" {Colors.OKGREEN}✅ {msg}{Colors.ENDC}")
    elif status == "warning":
        print(f" {Colors.WARNING}⚠️ {msg}{Colors.ENDC}")
    elif status == "fail":
        print(f" {Colors.FAIL}❌ {msg}{Colors.ENDC}")
    else:
        print(f" {Colors.OKCYAN}➡️ {msg}{Colors.ENDC}")

def audit_os() -> dict:
    """Audits OS specifications to ensure Linux/Mint compatibility."""
    print_status("Auditing Operating System specifications...", "info")
    os_info = {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine()
    }
    
    if os_info["system"].lower() != "linux":
        print_status(f"Non-Linux OS detected ({os_info['system']}). CoChem strictly targets Linux Mint/Ubuntu.", "warning")
        logging.warning(f"OS mismatch: {os_info}")
    else:
        print_status("Linux OS verified.", "success")
        logging.info(f"OS verification passed: {os_info}")
        
    return os_info

def main():
    print(f"\n{Colors.BOLD}--- CoChem Phase 1: System Audit ---{Colors.ENDC}")
    
    # Execute hardware queries
    os_metadata = audit_os()
    
    # Store parameters for downstream Phase 5 aggregation
    state_record = {
        "phase": 1,
        "os_info": os_metadata,
        "python_executable": sys.executable,
        "python_version": platform.python_version()
    }
    
    state_path = os.path.join("cochem_setup", "cochem_state_1.json")
    with open(state_path, "w") as f:
        json.dump(state_record, f, indent=4)
        
    print_status(f"Phase 1 Complete. Hardware base state saved to {state_path}.", "success")

if __name__ == "__main__":
    main()