#!/usr/bin/env python3
"""
CoChem Setup Phase 10: Intake & Alignment Tooling

Verifies and safely provisions 'molsym' and structural alignment dependencies
required for Eckart frame normalization prior to quantum calculations.
Safely cascades through offline tarballs and direct Git cloning to bypass
the absence of MolSym on standard PyPI.
"""

import os
import sys
import subprocess
import json
import logging
import tarfile
import importlib.util
from pathlib import Path
from logging.handlers import RotatingFileHandler

# ---------------------------------------------------------
# UI & LOGGING PROTOCOLS
# ---------------------------------------------------------
class Colors:
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

# Ensure isolated logging directories exist
os.makedirs("Logs", exist_ok=True)
logging.basicConfig(
    handlers=[RotatingFileHandler('Logs/cochem_phase10_intake.log', maxBytes=5 * 1024 * 1024, backupCount=3)],
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [Phase10] - %(message)s'
)
log = logging.getLogger("CoChem_Phase10")

def print_status(msg: str, status: str = "info") -> None:
    """Standardized console UI output."""
    if status == "success":
        print(f" {Colors.OKGREEN}✅ {msg}{Colors.ENDC}")
    elif status == "warning":
        print(f" {Colors.WARNING}⚠️ {msg}{Colors.ENDC}")
    elif status == "fail":
        print(f" {Colors.FAIL}❌ {msg}{Colors.ENDC}")
    else:
        print(f" {Colors.OKCYAN}➡️ {msg}{Colors.ENDC}")

# ---------------------------------------------------------
# DEPENDENCY PROVISIONING
# ---------------------------------------------------------
def ensure_molsym() -> bool:
    """
    Rigorously provisions the molsym symmetry engine.
    Cascades: 1. Existing Import -> 2. Local Tarball -> 3. Git Clone
    """
    if importlib.util.find_spec("molsym") is not None:
        print_status("MolSym library is already installed and globally accessible.", "success")
        return True
        
    print_status("MolSym not found in active kernel. Initiating safe provisioning...", "warning")
    
    # Cascade 1: Offline Local Tarball
    tarball_path = "MolSym-1.0.0.tar.gz"
    if os.path.exists(tarball_path):
        print_status("Local MolSym tarball detected. Extracting...", "info")
        try:
            with tarfile.open(tarball_path, "r:gz") as tar:
                tar.extractall(path=".")
            
            # Identify extracted directory
            extracted_dirs = [d for d in os.listdir(".") if d.startswith("MolSym-") and os.path.isdir(d)]
            if extracted_dirs:
                target_dir = extracted_dirs[0]
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-e", f"./{target_dir}"],
                    check=True, capture_output=True, text=True
                )
                print_status(f"Successfully installed MolSym from local archive ({target_dir}).", "success")
                log.info("MolSym successfully installed via offline tarball.")
                return True
        except Exception as e:
            log.error(f"Local tarball extraction or installation failed: {e}")
            print_status("Tarball extraction failed. Falling back to Git...", "warning")

    # Cascade 2: Direct Git Clone
    try:
        if not os.path.exists("MolSym"):
            print_status("Cloning MolSym from official NASymmetry repository...", "info")
            subprocess.run(
                ["git", "clone", "https://github.com/NASymmetry/MolSym.git"],
                check=True, capture_output=True, text=True
            )
        
        print_status("Binding MolSym to active Python kernel...", "info")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-e", "./MolSym"],
            check=True, capture_output=True, text=True
        )
        print_status("Successfully installed MolSym via Git clone.", "success")
        log.info("MolSym successfully cloned and installed.")
        return True
        
    except subprocess.CalledProcessError as e:
        print_status("Failed to provision MolSym. See Logs/cochem_phase10_intake.log", "fail")
        log.error(f"MolSym Git provisioning failed: {e.stderr if hasattr(e, 'stderr') else str(e)}")
        print(f"\n{Colors.WARNING}Manual Intervention Required:{Colors.ENDC}")
        print("Please download 'MolSym-1.0.0.tar.gz' manually and place it in this directory, then rerun.")
        return False

# ---------------------------------------------------------
# MAIN EXECUTION
# ---------------------------------------------------------
def main():
    print(f"\n{Colors.BOLD}--- CoChem Phase 10: Intake & Alignment Tooling ---{Colors.ENDC}")
    
    molsym_status = ensure_molsym()
    
    # Store parameters for Phase 11 routing
    state_record = {
        "phase": 10,
        "molsym_available": molsym_status,
        "alignment_engine_ready": molsym_status
    }
    
    os.makedirs("cochem_setup", exist_ok=True)
    state_path = os.path.join("cochem_setup", "cochem_state_p10.json")
    
    try:
        with open(state_path, "w") as f:
            json.dump(state_record, f, indent=4)
        print_status(f"Phase 10 state successfully locked to {state_path}", "success")
        log.info("Phase 10 execution completed and state saved.")
    except IOError as e:
        print_status(f"Failed to write state file: {e}", "fail")
        log.error(f"IOError during state save: {e}")
        sys.exit(1)

    if not molsym_status:
        print(f"\n{Colors.FAIL}⚠️  Warning: Alignment Engine is offline. CoChem-TOPOS will fail if invoked.{Colors.ENDC}")

if __name__ == "__main__":
    main()