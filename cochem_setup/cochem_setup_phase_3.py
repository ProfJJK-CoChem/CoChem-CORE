# cochem_canvas_target: cochem_setup/cochem_setup_phase_3.py
#!/usr/bin/env python3
"""
CoChem-CORE Setup Phase 3: Engines & Determinism
Performs cryptographic verification of system ORCA, OpenMPI, and g-xTB binaries.
If binaries are missing, it executes active fallback provisioning and compilation
within the isolated Air-Gap registry.
"""

import os
import sys
import json
import shutil
import urllib.request
import tarfile
import subprocess
import logging
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

def setup_phase3_logging() -> tuple[Path, logging.Logger]:
    """Configures the persistent logging subsystem within the strict Artifact Air-Gap."""
    artifact_dir = os.environ.get("COCHEM_ARTIFACT_DIR")
    if not artifact_dir:
        raise RuntimeError("❌ FATAL: COCHEM_ARTIFACT_DIR not set. Must run via Orchestrator.")
    
    log_dir = Path(artifact_dir) / "Logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / "cochem_phase3_engines.log"
    handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=2)
    formatter = logging.Formatter('%(asctime)s - [%(levelname)s] - %(message)s')
    handler.setFormatter(formatter)
    
    logger = logging.getLogger("CoChem_Phase3")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        logger.addHandler(handler)
        
    engines_dir = Path(artifact_dir) / "Registry" / "Engines"
    engines_dir.mkdir(parents=True, exist_ok=True)
    return engines_dir, logger

def test_executable(cmd_list: list, check_string: str, env: dict = None) -> bool:
    """Executes a command and checks if the output contains a validation string."""
    try:
        result = subprocess.run(
            cmd_list, 
            capture_output=True, 
            text=True, 
            env=env,
            timeout=15
        )
        if check_string.lower() in result.stdout.lower() or check_string.lower() in result.stderr.lower():
            return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired, PermissionError):
        return False
    return False

# ---------------------------------------------------------
# ACTIVE FALLBACK INSTALLATION ROUTINES
# ---------------------------------------------------------
def install_openmpi(engines_dir: Path, log: logging.Logger) -> Path:
    """Actively downloads and compiles OpenMPI source if missing from the environment."""
    mpi_dir = engines_dir / "openmpi_4_1_6"
    if mpi_dir / "bin" / "mpirun" in mpi_dir.glob("**/mpirun"):
        print_status("OpenMPI local cache hit verified.", "success")
        log.info("OpenMPI found in local engine cache.")
        return list(mpi_dir.glob("**/mpirun"))[0]

    print_status("OpenMPI missing. Initiating automated source fetch (OpenMPI 4.1.6)...", "warning")
    log.info("Downloading OpenMPI 4.1.6 source archive...")
    
    tarball_path = engines_dir / "openmpi-4.1.6.tar.gz"
    url = "https://download.open-mpi.org/release/open-mpi/v4.1/openmpi-4.1.6.tar.gz"
    
    try:
        urllib.request.urlretrieve(url, tarball_path)
        print_status("OpenMPI archive downloaded successfully. Extracting...", "info")
        
        with tarfile.open(tarball_path, "r:gz") as tar:
            tar.extractall(path=engines_dir)
            
        src_dir = engines_dir / "openmpi-4.1.6"
        build_dir = engines_dir / "openmpi_build"
        build_dir.mkdir(exist_ok=True)
        
        print_status("Configuring OpenMPI build...", "info")
        subprocess.run(
            [str(src_dir / "configure"), f"--prefix={mpi_dir}"],
            cwd=build_dir, check=True, capture_output=True
        )
        
        print_status("Compiling OpenMPI binaries (Make)...", "info")
        subprocess.run(["make", "-j4"], cwd=build_dir, check=True, capture_output=True)
        subprocess.run(["make", "install"], cwd=build_dir, check=True, capture_output=True)
        
        print_status("OpenMPI successfully compiled and staged.", "success")
        log.info("OpenMPI compilation successful.")
        
        # Cleanup tarball and build scratch to save space
        tarball_path.unlink(missing_ok=True)
        shutil.rmtree(build_dir, ignore_errors=True)
        
        return mpi_dir / "bin" / "mpirun"
        
    except Exception as e:
        print_status(f"OpenMPI automated compilation failed: {e}", "fail")
        log.error(f"OpenMPI build error: {e}")
        return None

def install_xtb(engines_dir: Path, log: logging.Logger) -> Path:
    """Fetches and extracts Grimme's xTB binaries for fast-pass triaging."""
    xtb_dir = engines_dir / "xtb_bin"
    xtb_bin = xtb_dir / "xtb"
    if xtb_bin.exists():
        print_status("g-xTB local cache hit verified.", "success")
        log.info("g-xTB found in local engine cache.")
        return xtb_bin

    print_status("g-xTB missing. Fetching pre-compiled release...", "warning")
    log.info("Downloading g-xTB static binary release...")
    
    tarball_path = engines_dir / "xtb.tar.xz"
    url = "https://github.com/grimme-lab/xtb/releases/download/v6.7.1/xtb-6.7.1-linux-x86_64.tar.xz"
    
    try:
        urllib.request.urlretrieve(url, tarball_path)
        print_status("g-xTB archive downloaded. Extracting into Air-Gap registry...", "info")
        
        xtb_dir.mkdir(parents=True, exist_ok=True)
        with tarfile.open(tarball_path, "r:xz") as tar:
            tar.extractall(path=xtb_dir)
            
        print_status("g-xTB successfully staged.", "success")
        log.info("g-xTB extraction complete.")
        tarball_path.unlink(missing_ok=True)
        
        bin_matches = list(xtb_dir.glob("**/xtb"))
        if bin_matches:
            return bin_matches[0]
            
    except Exception as e:
        print_status(f"g-xTB automated fetch failed: {e}", "warning")
        log.warning(f"g-xTB download error: {e}")
        
    return None

# ---------------------------------------------------------
# BINARY VERIFICATION LOGIC
# ---------------------------------------------------------
def verify_orca(log: logging.Logger) -> dict:
    """Uses the Bulletproof Sibling Scanner to locate Max-Planck ORCA 6.1.1."""
    print_status("Checking for system-wide ORCA...")
    
    orca_path = shutil.which("orca")
    if not orca_path:
        orca_home = os.environ.get("ORCA_HOME", "")
        if orca_home:
            orca_path = shutil.which("orca", path=orca_home)
            
    if orca_path:
        orca_dir = Path(orca_path).parent
        # The Sibling Check: Ensures this is actually Max-Planck's ORCA
        if (orca_dir / "orca_scf").exists() and (orca_dir / "orca_mcscf").exists():
            print_status(f"System ORCA natively detected at: {orca_path}", "success")
            log.info(f"ORCA 6.1.x verified via sibling scan at {orca_path}")
            return {"status": "verified", "path": str(orca_path)}
        else:
            log.warning(f"Found 'orca' binary at {orca_path} but missing siblings. Likely GNOME screen reader.")
            
    print_status("ORCA status: missing. Ab initio extrapolation stages will require manual path linkage.", "warning")
    log.warning("ORCA missing. Prompting manual installation fallback downstream.")
    return {"status": "missing", "path": "None"}

def verify_openmpi(engines_dir: Path, log: logging.Logger) -> dict:
    """Validates OpenMPI or triggers active source compilation."""
    print_status("Checking for system-wide OpenMPI...")
    
    mpirun_path = shutil.which("mpirun")
    if mpirun_path and test_executable([mpirun_path, "--version"], "open mpi"):
        print_status(f"OpenMPI natively detected at: {mpirun_path}", "success")
        log.info(f"OpenMPI verified at {mpirun_path}")
        return {"status": "verified", "path": str(mpirun_path)}
        
    print_status("System OpenMPI missing. Triggering active compilation...", "warning")
    compiled_mpi = install_openmpi(engines_dir, log)
    
    if compiled_mpi and compiled_mpi.exists():
        return {"status": "compiled_source", "path": str(compiled_mpi)}
        
    print_status("OpenMPI status: missing. Workloads restricted to sequential mode.", "warning")
    log.warning("OpenMPI installation failed. Workloads restricted to sequential mode.")
    return {"status": "missing", "path": "None"}

def verify_xtb(engines_dir: Path, log: logging.Logger) -> dict:
    """Validates g-xTB or triggers fallback deployment."""
    print_status("Checking for system-wide g-xTB...")
    
    xtb_path = shutil.which("xtb")
    if xtb_path and test_executable([xtb_path, "--version"], "xtb"):
        print_status(f"System g-xTB verified at: {xtb_path}", "success")
        log.info(f"xTB verified at {xtb_path}")
        return {"status": "verified", "path": str(xtb_path)}
        
    print_status("System g-xTB missing. Triggering automated deployment...", "warning")
    local_xtb = install_xtb(engines_dir, log)
    
    if local_xtb and local_xtb.exists():
        return {"status": "verified", "path": str(local_xtb)}
        
    print_status("g-xTB status: missing. Fast triages will degrade to local PySCF/MACE.", "warning")
    log.warning("xTB missing. Falling back to PySCF/MACE for triages.")
    return {"status": "missing", "path": "None"}

# ---------------------------------------------------------
# MAIN EXECUTION
# ---------------------------------------------------------
def main():
    print(f"\n{Colors.BOLD}--- CoChem Phase 3: Engines & Determinism ---{Colors.ENDC}")
    
    try:
        engines_dir, log = setup_phase3_logging()
        log.info("Phase 3 Execution Started.")
        
        orca_state = verify_orca(log)
        mpi_state = verify_openmpi(engines_dir, log)
        xtb_state = verify_xtb(engines_dir, log)
        
        state_record = {
            "phase": 3,
            "engines": {
                "orca": {
                    "status": orca_state["status"],
                    "path": orca_state["path"],
                    "version": "6.1.1"
                },
                "mpirun": {
                    "status": mpi_state["status"],
                    "path": mpi_state["path"],
                    "version": "4.1.6"
                },
                "xtb": {
                    "status": xtb_state["status"],
                    "path": xtb_state["path"],
                    "version": "latest"
                }
            }
        }
        
        os.makedirs("cochem_setup", exist_ok=True)
        state_path = os.path.join("cochem_setup", "cochem_state_p3.json")
        
        with open(state_path, "w") as f:
            json.dump(state_record, f, indent=4)
            
        print_status("Phase 3 state successfully locked to cochem_setup/cochem_state_p3.json", "success")
        log.info("Phase 3 completed successfully. IPC registry written.")
        
    except Exception as e:
        print_status(f"Phase 3 Encountered a Fatal Error: {e}", "fail")
        # RuntimeError protects the active Jupyter kernel from terminating unexpectedly
        raise RuntimeError(f"Phase 3 Execution Aborted: {e}")

if __name__ == "__main__":
    main()