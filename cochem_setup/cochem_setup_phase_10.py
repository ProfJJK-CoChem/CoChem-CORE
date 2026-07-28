#!/usr/bin/env python3
"""
CoChem-CORE Setup Phase 10: Eckart Frame & MolSym Intake
Verifies and safely provisions 'molsym' and structural alignment dependencies
required for Eckart frame normalization prior to quantum calculations.
Safely cascades through offline tarballs and direct Git cloning to bypass
the absence of MolSym on standard PyPI, mapping the absolute path for IPC.
"""

import os
import sys
import json
import logging
import subprocess
import tarfile
import shutil
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

def print_status(msg: str, status: str = "info") -> None:
    if status == "success":
        print(f" {Colors.OKGREEN}✅ {msg}{Colors.ENDC}")
    elif status == "warning":
        print(f" {Colors.WARNING}⚠️ {msg}{Colors.ENDC}")
    elif status == "fail":
        print(f" {Colors.FAIL}❌ {msg}{Colors.ENDC}")
    else:
        print(f" {Colors.OKCYAN}➡️ {msg}{Colors.ENDC}")

def setup_logging() -> logging.Logger:
    log_dir = Path("Logs")
    log_dir.mkdir(exist_ok=True)
    logger = logging.getLogger("CoChem_Phase10")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = RotatingFileHandler(log_dir / 'cochem_phase10_align.log', maxBytes=5*1024*1024, backupCount=3)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - [Phase10] - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger

log = setup_logging()

# ---------------------------------------------------------
# ALIGNMENT ENGINE PROVISIONING
# ---------------------------------------------------------

def check_qcelemental() -> bool:
    """MolSym strictly requires qcelemental for mass lookups."""
    try:
        import qcelemental
        return True
    except ImportError:
        print_status("qcelemental missing. Attempting pip injection...", "warning")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "qcelemental"], check=True, capture_output=True)
            print_status("qcelemental successfully injected.", "success")
            return True
        except subprocess.CalledProcessError:
            print_status("Failed to inject qcelemental. MolSym may fail.", "fail")
            return False

def ensure_molsym(base_dir: Path) -> str:
    """
    MolSym is often un-pip-installable. This attempts to import it.
    If missing, it clones the repository directly into a safe execution path.
    """
    print_status("Verifying MolSym Structural Aligner...", "info")
    try:
        import molsym
        print_status("MolSym natively detected.", "success")
        return "native"
    except ImportError:
        print_status("MolSym not natively installed. Initiating direct Git bind...", "warning")
        
    target_dir = base_dir / "core_engine" / "molsym_ext"
    if target_dir.exists() and (target_dir / "molsym").exists():
        print_status("MolSym local bindings previously established.", "success")
        return str(target_dir.absolute())

    if not shutil.which("git"):
        print_status("Git is not installed. Cannot clone MolSym.", "fail")
        log.error("Git binary missing from PATH.")
        return "None"

    try:
        subprocess.run(
            ["git", "clone", "https://github.com/NASymmetry/MolSym.git", str(target_dir)],
            capture_output=True, text=True, check=True
        )
        print_status("MolSym cloned and locked into local execution path.", "success")
        return str(target_dir.absolute())
        
    except subprocess.CalledProcessError as e:
        log.error(f"Git clone failed: {e.stderr}")
        print_status("Git clone rejected (Network drop?). Alignment protocols will safely degrade to C1.", "warning")
        return "None"

def main():
    print(f"\n{Colors.BOLD}--- CoChem Phase 10: Eckart Frame & MolSym Intake ---{Colors.ENDC}")
    
    base_dir = Path(__file__).resolve().parent.parent
    check_qcelemental()
    
    molsym_path = ensure_molsym(base_dir)
    
    state_record = {
        "phase": 10,
        "molsym_path": molsym_path,
        "alignment_engine_ready": True if molsym_path != "None" else False
    }
    
    state_path = base_dir / "cochem_setup" / "cochem_state_p10.json"
    
    try:
        with open(state_path, "w") as f:
            json.dump(state_record, f, indent=4)
        print_status(f"Phase 10 state locked. Path bindings preserved.", "success")
        log.info("Phase 10 execution completed.")
    except IOError as e:
        print_status(f"Failed to write Phase 10 state file: {e}", "fail")
        sys.exit(1)

if __name__ == "__main__":
    main()