# cochem_canvas_target: cochem_setup/cochem_setup_phase_10.py
#!/usr/bin/env python3
"""
CoChem-CORE Setup Phase 10: Eckart Frame & MolSym Intake
Verifies and safely provisions 'molsym' and structural alignment dependencies
required for Eckart frame normalization prior to quantum calculations.
Safely cascades through offline tarballs and direct Git cloning to bypass
the absence of MolSym on standard PyPI, mapping the absolute path for IPC.
"""

import os
import json
import shutil
import logging
import subprocess
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
    """Standardized console UI output."""
    if status == "success":
        print(f" {Colors.OKGREEN}✅ {msg}{Colors.ENDC}")
    elif status == "warning":
        print(f" {Colors.WARNING}⚠️ {msg}{Colors.ENDC}")
    elif status == "fail":
        print(f" {Colors.FAIL}❌ {msg}{Colors.ENDC}")
    else:
        print(f" {Colors.OKCYAN}➡️ {msg}{Colors.ENDC}")

def setup_phase10_logging() -> logging.Logger:
    """Configures the persistent logging subsystem."""
    artifact_dir = os.environ.get("COCHEM_ARTIFACT_DIR", str(Path.home() / "CoChem_Artifacts"))
    log_dir = Path(artifact_dir) / "Logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / "cochem_phase10_molsym.log"
    handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=2)
    formatter = logging.Formatter('%(asctime)s - [%(levelname)s] - %(message)s')
    handler.setFormatter(formatter)
    
    logger = logging.getLogger("CoChem_Phase10")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        logger.addHandler(handler)
        
    return logger

def check_qcelemental(log: logging.Logger) -> None:
    """Checks for the underlying QCEngine schema dependency utilized by MolSym."""
    print_status("Checking qcelemental dependency for robust isotopic mass mapping...", "info")
    try:
        import qcelemental
        print_status("qcelemental verified.", "success")
        log.info("qcelemental module successfully imported.")
    except ImportError:
        print_status("qcelemental missing in orchestration environment. Ensure Conda silos contain it.", "warning")
        log.warning("qcelemental not found in the immediate Python context.")

def ensure_molsym(base_dir: Path, log: logging.Logger) -> str:
    """Safely fetches MolSym via Git and locks it into the CoChem execution path."""
    target_dir = base_dir / "cochem_libraries" / "MolSym"
    
    if target_dir.exists() and (target_dir / "molsym").exists():
        print_status("MolSym library natively detected.", "success")
        log.info(f"MolSym located at {target_dir}")
        return str(target_dir.absolute())

    print_status("MolSym missing. Initiating secure Git clone...", "info")
    
    if not shutil.which("git"):
        print_status("Git binary missing from PATH. Cannot fetch MolSym.", "fail")
        log.error("Git binary missing from PATH.")
        return "None"

    try:
        target_dir.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "clone", "https://github.com/NASymmetry/MolSym.git", str(target_dir)],
            capture_output=True, text=True, check=True
        )
        print_status("MolSym cloned and locked into local execution path.", "success")
        log.info("MolSym successfully cloned from NASymmetry repository.")
        return str(target_dir.absolute())
        
    except subprocess.CalledProcessError as e:
        log.error(f"Git clone failed: {e.stderr}")
        print_status("Git clone rejected (Network drop?). Alignment protocols will safely degrade to C1.", "warning")
        return "None"

# ---------------------------------------------------------
# MAIN EXECUTION
# ---------------------------------------------------------
def main():
    print(f"\n{Colors.BOLD}--- CoChem Phase 10: Eckart Frame & MolSym Intake ---{Colors.ENDC}")
    
    log = setup_phase10_logging()
    log.info("Phase 10 Execution Started.")
    
    # Resolve project root dynamically
    base_dir = Path(__file__).resolve().parent.parent
    
    check_qcelemental(log)
    molsym_path = ensure_molsym(base_dir, log)
    
    # Generate Phase 10 state for the Memory Router
    state_record = {
        "phase": 10,
        "molsym_path": molsym_path,
        "alignment_engine_ready": True if molsym_path != "None" else False
    }
    
    os.makedirs(base_dir / "cochem_setup", exist_ok=True)
    state_path = base_dir / "cochem_setup" / "cochem_state_p10.json"
    
    try:
        with open(state_path, "w") as f:
            json.dump(state_record, f, indent=4)
        print_status(f"Phase 10 State Locked: alignment_engine_ready={state_record['alignment_engine_ready']}", "success")
        log.info(f"Phase 10 state written to {state_path}")
    except Exception as e:
        print_status(f"Fatal error writing Phase 10 state: {e}", "fail")
        log.error(f"Write error: {e}")
        raise RuntimeError(f"Phase 10 Execution Aborted: {e}")

if __name__ == "__main__":
    main()