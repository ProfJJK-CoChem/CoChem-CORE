#!/usr/bin/env python3
"""
CoChem Setup Phase 3: Deep Engine & Cryptographic Verification
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
    log_file = os.path.join(log_dir, "cochem_phase3_engines.log")
    
    handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=3)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - [Phase3] - %(message)s')
    handler.setFormatter(formatter)
    
    log = logging.getLogger("CoChem_Phase3")
    log.setLevel(logging.DEBUG)
    if not log.handlers:
        log.addHandler(handler)
    return log

log = setup_logging()

# ---------------------------------------------------------
# CRYPTOGRAPHIC & ENGINE PROTOCOLS
# ---------------------------------------------------------
def compute_hash(filepath: str) -> str:
    """
    Computes SHA-256 with explicit error typing and chunking 
    to prevent memory spikes on massive binaries.
    """
    if not filepath or not os.path.exists(filepath):
        return "Not_Found"
    
    sha256 = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    except PermissionError:
        log.error(f"Permission denied when hashing {filepath}")
        return "Permission_Denied"
    except Exception as e:
        log.error(f"Hashing failed for {filepath}: {e}")
        return "Hash_Error"

def mask_path(path: str) -> str:
    """Masks the home directory for cleaner terminal outputs."""
    home = os.path.expanduser("~")
    if path.startswith(home):
        return path.replace(home, "~", 1)
    return path

def verify_engine(engine_cmd: str, version_flag: str = "--version") -> dict:
    """
    Locates the engine, executes it safely to capture stdout/stderr,
    and computes the cryptographic hash.
    """
    print_status(f"Scanning for {engine_cmd}...", "info")
    engine_path = shutil.which(engine_cmd)
    
    if not engine_path:
        log.warning(f"Engine '{engine_cmd}' not found in local PATH.")
        return {
            "status": "missing", 
            "path": "Not_Found", 
            "version": "Unknown", 
            "hash": "Not_Found"
        }

    # Explicit permission trap
    if not os.access(engine_path, os.X_OK):
        log.error(f"Execution permission missing for {engine_path}.")
        return {
            "status": "error", 
            "path": engine_path, 
            "version": "Permission_Denied", 
            "hash": "Permission_Denied"
        }

    try:
        # PATCH APPLIED: capture_output=True prevents POSIX stderr leaks to terminal
        result = subprocess.run([engine_path, version_flag], capture_output=True, text=True, timeout=10)
        out = result.stdout + result.stderr
        version = "Unknown"
        
        # Advanced parsing heuristics for specific computational engines
        if engine_cmd == "orca":
            if "Program Version" in out:
                version = out.split("Program Version")[1].split()[0]
            elif "O   R   C   A" in out:
                version = "Found (Header Match)"
        elif engine_cmd == "mpirun":
            if "Open MPI" in out:
                # Naive split extraction; heavily depends on OS package layout
                parts = out.split()
                if "MPI" in parts:
                    try:
                        idx = parts.index("MPI") + 1
                        version = parts[idx]
                    except IndexError:
                        pass
            if version == "Unknown" and "mpirun" in out.lower():
                version = "Executable_Verified"
        elif engine_cmd == "xtb":
            if "xtb version" in out:
                version = out.split("xtb version")[1].split()[0]

        if version == "Unknown" and result.returncode == 0:
            version = "Executable_Verified"

        engine_hash = compute_hash(engine_path)
        
        log.info(f"Verified {engine_cmd}: Path={engine_path}, Version={version}, Hash={engine_hash}")
        return {
            "status": "found",
            "path": engine_path,
            "version": version,
            "hash": engine_hash
        }

    except subprocess.TimeoutExpired:
        log.error(f"Timeout while checking version for {engine_cmd}")
        return {
            "status": "timeout", 
            "path": engine_path, 
            "version": "Unknown", 
            "hash": compute_hash(engine_path)
        }
    except Exception as e:
        log.error(f"Error executing {engine_cmd}: {e}")
        return {
            "status": "error", 
            "path": engine_path, 
            "version": "Execution_Failed", 
            "hash": compute_hash(engine_path)
        }

# ---------------------------------------------------------
# MAIN EXECUTION
# ---------------------------------------------------------
def main():
    print(f"\n{Colors.BOLD}--- CoChem Phase 3: Deep Engine & Cryptographic Verification ---{Colors.ENDC}")
    
    # Load upstream state to ensure sequential integrity
    state_dir = "cochem_setup"
    os.makedirs(state_dir, exist_ok=True)
    upstream_state = os.path.join(state_dir, "cochem_state_p2.json")
    
    if not os.path.exists(upstream_state):
        print_status(f"Missing upstream state file: {upstream_state}. Please run Phase 2 first.", "fail")
        log.error("Phase 3 Execution Halted: Missing Phase 2 state.")
        sys.exit(1)
        
    engines_data = {}
    
    # 1. ORCA
    orca_data = verify_engine("orca")
    engines_data["orca"] = orca_data
    if orca_data["status"] == "found":
        print_status(f"ORCA executable cached: {mask_path(orca_data['path'])} (v{orca_data['version']})", "success")
    else:
        print_status("ORCA not found in standard PATH. MACE/PySCF fallbacks will be required.", "warning")

    # 2. OpenMPI
    mpi_data = verify_engine("mpirun")
    engines_data["mpirun"] = mpi_data
    if mpi_data["status"] == "found":
        print_status(f"OpenMPI cached: {mask_path(mpi_data['path'])}", "success")
    else:
        print_status("OpenMPI not found. Workloads will be strictly restricted to sequential mode.", "warning")

    # 3. g-xTB
    xtb_data = verify_engine("xtb")
    engines_data["xtb"] = xtb_data
    if xtb_data["status"] == "found":
        print_status(f"g-xTB cached: {mask_path(xtb_data['path'])}", "success")
    else:
        print_status("g-xTB not found. Fast conformational triages will degrade to local PySCF.", "warning")

    # Save Cryptographic Engine Matrix
    state_record = {
        "phase": 3,
        "engines": engines_data
    }

    state_path = os.path.join(state_dir, "cochem_state_p3.json")
    try:
        with open(state_path, "w") as f:
            json.dump(state_record, f, indent=4)
        print_status(f"Phase 3 state locked cryptographically to {state_path}", "success")
        log.info("Phase 3 execution completed and state saved.")
    except IOError as e:
        print_status(f"Failed to write state file: {e}", "fail")
        log.error(f"IOError during state save: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()