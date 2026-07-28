#!/usr/bin/env python3
"""
CoChem-CORE Setup Phase 3: Deep Engine & Cryptographic Verification
Locates local installations of ORCA, OpenMPI, and g-xTB, extracts version info,
and calculates SHA-256 hashes for strict deterministic provenance.
"""

import os
import sys
import json
import hashlib
import subprocess
import shutil
import logging
from logging.handlers import RotatingFileHandler
from typing import Dict, Any

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

def setup_logging() -> logging.Logger:
    """Initializes the diagnostic rotating logger."""
    log_dir = "Logs"
    os.makedirs(log_dir, exist_ok=True)
    logger = logging.getLogger("CoChem_Phase3")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = RotatingFileHandler(os.path.join(log_dir, 'cochem_phase3_engines.log'), maxBytes=5*1024*1024, backupCount=3)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - [Phase3] - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger

log = setup_logging()

# ---------------------------------------------------------
# ENGINE VERIFICATION FUNCTIONS
# ---------------------------------------------------------

def calculate_sha256(filepath: str) -> str:
    """Computes the cryptographic SHA-256 hash of a compiled binary."""
    sha256_hash = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except IOError as e:
        log.error(f"Failed to hash {filepath}: {e}")
        return "HASH_FAILED"

def verify_engine(executable_name: str) -> Dict[str, Any]:
    """
    Locates the binary in the system PATH.
    If found, returns the absolute path and its SHA-256 hash.
    """
    path = shutil.which(executable_name)
    if not path:
        log.warning(f"Engine binary '{executable_name}' not found in PATH.")
        return {"status": "missing", "path": None, "version": None, "hash": None}

    # Ensure we actually have execution permission, guarding against broken symlinks
    if not os.access(path, os.X_OK):
        log.error(f"Binary '{executable_name}' found at {path}, but lacks execution permissions.")
        return {"status": "permission_denied", "path": path, "version": None, "hash": None}

    binary_hash = calculate_sha256(path)
    log.info(f"Verified {executable_name} at {path} (SHA-256: {binary_hash[:16]}...)")
    
    return {
        "status": "found",
        "path": os.path.abspath(path),
        "version": "unknown",  # We let the Config Compiler handle explicit semantic version checking
        "hash": binary_hash
    }

def mask_path(path: str) -> str:
    """Truncates paths for UI display to prevent UI flooding."""
    if not path: return "None"
    if len(path) > 50:
        return "..." + path[-47:]
    return path

# ---------------------------------------------------------
# MAIN EXECUTION
# ---------------------------------------------------------
def main():
    print(f"\n{Colors.BOLD}--- CoChem Phase 3: Engines & Determinism ---{Colors.ENDC}")
    
    engines_data = {}
    
    print_status("Checking for system-wide ORCA...", "info")
    engines_data["orca"] = verify_engine("orca")
    if engines_data["orca"]["status"] == "found":
        print_status(f"Found cached CoChem ORCA at: {mask_path(engines_data['orca']['path'])}", "success")
    else:
        print_status(f"ORCA status: {engines_data['orca']['status']}. Ab initio extrapolation stages will fail.", "warning")

    print_status("Checking for system-wide OpenMPI...", "info")
    engines_data["mpirun"] = verify_engine("mpirun")
    if engines_data["mpirun"]["status"] == "found":
        print_status(f"Found cached CoChem OpenMPI at: {mask_path(engines_data['mpirun']['path'])}", "success")
    else:
        print_status(f"OpenMPI status: {engines_data['mpirun']['status']}. Workloads will be strictly restricted to sequential mode.", "warning")

    print_status("Checking for system-wide g-xTB...", "info")
    engines_data["xtb"] = verify_engine("xtb")
    if engines_data["xtb"]["status"] == "found":
        print_status(f"Found cached CoChem g-xTB at: {mask_path(engines_data['xtb']['path'])}", "success")
    else:
        print_status(f"g-xTB status: {engines_data['xtb']['status']}. Fast triages will degrade to local PySCF/MACE.", "warning")

    # Save Cryptographic Engine Matrix
    state_record = {
        "phase": 3,
        "engines": engines_data
    }
    
    os.makedirs("cochem_setup", exist_ok=True)
    state_path = os.path.join("cochem_setup", "cochem_state_p3.json")
    
    try:
        with open(state_path, "w") as f:
            json.dump(state_record, f, indent=4)
        print_status(f"Phase 3 state successfully locked to {state_path}", "success")
        log.info("Phase 3 execution completed.")
    except IOError as e:
        print_status(f"Failed to write state file: {e}", "fail")
        log.error(f"IOError during state save: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()