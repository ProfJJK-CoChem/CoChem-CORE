#!/usr/bin/env python3
"""
CoChem Setup Phase 10: Intake & Alignment Tooling
Verifies and provisions 'molsym' and structural alignment dependencies
required for Eckart frame normalization prior to quantum calculations.
"""

import os
import sys
import subprocess
import json
import logging
from logging.handlers import RotatingFileHandler
import importlib.util

class Colors:
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

os.makedirs("cochem_setup", exist_ok=True)
logging.basicConfig(
    handlers=[RotatingFileHandler('cochem_setup/cochem_phase10_intake.log', maxBytes=1000000, backupCount=3)],
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

def ensure_molsym() -> bool:
    """Audits the environment for 'molsym'. Installs if missing."""
    print_status("Checking for 'molsym' geometry alignment library...", "info")
    
    spec = importlib.util.find_spec("molsym")
    if spec is not None:
        print_status("molsym is already installed.", "success")
        return True
        
    print_status("molsym not found. Attempting safe installation...", "warning")
    try:
        # Use sys.executable to ensure we install into the active Jupyter kernel's environment
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "molsym"],
            check=True, capture_output=True, text=True
        )
        print_status("Successfully installed molsym.", "success")
        logging.info("molsym installed successfully via subprocess.")
        return True
    except subprocess.CalledProcessError as e:
        print_status("Failed to install molsym. Check logs.", "fail")
        logging.error(f"molsym install failed: {e.stderr}")
        return False

def main():
    print(f"\n{Colors.BOLD}--- CoChem Phase 10: Intake & Alignment ---{Colors.ENDC}")
    
    molsym_status = ensure_molsym()
    
    # Store parameters for Phase 11 routing
    state_record = {
        "phase": 10,
        "molsym_available": molsym_status,
        "alignment_engine_ready": molsym_status
    }
    
    state_path = os.path.join("cochem_setup", "cochem_state_10.json")
    with open(state_path, "w") as f:
        json.dump(state_record, f, indent=4)
        
    if molsym_status:
        print_status(f"Phase 10 Complete. Intake alignment tools ready.", "success")
    else:
        print_status(f"Phase 10 Degraded. Geometry alignment may fail downstream.", "warning")

if __name__ == "__main__":
    main()