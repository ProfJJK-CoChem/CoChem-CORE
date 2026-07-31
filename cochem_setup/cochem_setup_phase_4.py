# cochem_canvas_target: cochem_setup/cochem_setup_phase_4.py
#!/usr/bin/env python3
"""
CoChem-CORE Setup Phase 4: Dynamic Orchestration & Silo Generation
Implements aggressive dependency upgrading for standard libraries and
high-risk C++ bindings via isolated Conda micro-environments.
Dynamically reads cochem_deployment_manifest.json to avoid installing
unnecessary multi-gigabyte GPU tensors. Includes an Active Conda Bootstrapper.
"""

import os
import sys
import json
import logging
import subprocess
import shutil
import urllib.request
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

def setup_phase4_logging() -> logging.Logger:
    """Initializes the diagnostic rotating logger."""
    artifact_dir = os.environ.get("COCHEM_ARTIFACT_DIR", str(Path.home() / "CoChem_Artifacts"))
    log_dir = Path(artifact_dir) / "Logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / "cochem_phase4_silos.log"
    handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=2)
    formatter = logging.Formatter('%(asctime)s - [%(levelname)s] - %(message)s')
    handler.setFormatter(formatter)
    
    logger = logging.getLogger("CoChem_Phase4")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        logger.addHandler(handler)
        
    return logger

def find_conda(log: logging.Logger) -> str:
    """Deep-scans for Conda/Mamba or actively bootstraps Miniconda if completely missing."""
    print_status("Probing for Conda/Mamba package manager...", "info")
    
    # 1. Check Standard PATH
    conda_path = shutil.which("mamba") or shutil.which("conda")
    if conda_path:
        return conda_path
        
    # 2. Check Common Hidden Paths (Codespaces/DevContainers)
    common_paths = [
        Path.home() / "miniconda3" / "bin" / "conda",
        Path.home() / "anaconda3" / "bin" / "conda",
        Path("/opt/conda/bin/conda"),
        Path("/opt/miniconda3/bin/conda"),
        Path.home() / ".local" / "miniconda" / "bin" / "conda"
    ]
    
    for p in common_paths:
        if p.exists() and os.access(p, os.X_OK):
            log.info(f"Conda found via deep-scan at {p}")
            return str(p)
            
    # 3. Active Self-Healing: Bootstrap Miniconda
    print_status("Conda not found on system. Initiating automated Miniconda bootstrap...", "warning")
    log.warning("Conda missing. Fetching Miniconda installer via urllib...")
    
    install_dir = Path.home() / ".local" / "miniconda"
    installer_path = Path.home() / "miniconda_installer.sh"
    
    url = "https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"
    try:
        urllib.request.urlretrieve(url, installer_path)
        print_status("Installer downloaded. Compiling Miniconda runtime (this takes ~60 seconds)...", "info")
        
        # Run silent bash installation
        subprocess.run(["bash", str(installer_path), "-b", "-u", "-p", str(install_dir)], check=True, capture_output=True)
        
        installer_path.unlink() # Cleanup
        new_conda = install_dir / "bin" / "conda"
        
        if new_conda.exists():
            print_status(f"Miniconda successfully bootstrapped to {install_dir}", "success")
            log.info("Miniconda bootstrap complete.")
            return str(new_conda)
            
    except Exception as e:
        log.error(f"Miniconda bootstrap failed: {e}")
        raise RuntimeError(f"FATAL: Conda not found and automated installation failed: {e}")
        
    raise RuntimeError("FATAL: Conda installation sequence failed silently.")

def get_selected_modules() -> list:
    """Reads the intended deployment manifest from UNITY or defaults to ALL."""
    manifest_path = Path("cochem_setup/cochem_deployment_manifest.json")
    if manifest_path.exists():
        try:
            with open(manifest_path, "r") as f:
                data = json.load(f)
                return data.get("modules", [])
        except json.JSONDecodeError:
            return ["ALL"]
    return ["ALL"]

# ---------------------------------------------------------
# SILO CONSTRUCTION PROTOCOLS
# ---------------------------------------------------------
def run_conda_cmd(cmd_list: list, log: logging.Logger) -> bool:
    """Safely executes a Conda command and streams to log."""
    try:
        log.info(f"Executing Conda Command: {' '.join(cmd_list)}")
        result = subprocess.run(
            cmd_list,
            capture_output=True,
            text=True,
            check=True
        )
        log.info(f"Conda Output: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        log.error(f"Conda Error: {e.stderr}")
        return False

def enforce_pip_upgrades(conda_path: str, env_name: str, log: logging.Logger) -> bool:
    """Aggressively upgrades pip inside the silo before installing MACE."""
    print_status(f"Enforcing pip/wheel upgrade in silo '{env_name}'...", "info")
    return run_conda_cmd(
        [conda_path, "run", "-n", env_name, "python", "-m", "pip", "install", "--upgrade", "pip", "wheel", "setuptools"],
        log
    )

def build_torq_silo(conda_path: str, log: logging.Logger) -> bool:
    """Builds the primary Discovery/Geometry engine (TORQ/TOPOS)."""
    env_name = "cochem_torq_silo"
    print_status(f"Building Discovery Silo '{env_name}' (Python 3.11, MACE, NetworkX)...", "info")
    
    # 1. Create Base Env with Upgrade Fallback
    create_cmd = [conda_path, "create", "-y", "-c", "conda-forge", "-n", env_name, "python=3.11", "numpy", "scipy", "networkx", "matplotlib"]
    if not run_conda_cmd(create_cmd, log):
        log.warning(f"Conda create failed. Attempting forced upgrade on existing {env_name}...")
        upgrade_cmd = [conda_path, "install", "-y", "-c", "conda-forge", "-n", env_name, "python=3.11", "numpy", "scipy", "networkx", "matplotlib"]
        if not run_conda_cmd(upgrade_cmd, log):
            print_status("Failed to create or upgrade base TORQ Conda environment.", "fail")
            return False
        
    # 2. Upgrade Pip
    enforce_pip_upgrades(conda_path, env_name, log)
    
    # 3. Pip Install PyTorch, MACE, and dependencies
    print_status("Injecting PyTorch and MACE-OFF23...", "info")
    pip_cmd = [conda_path, "run", "-n", env_name, "pip", "install", "torch", "mace-torch", "pydantic", "h5py", "rdkit"]
    
    if run_conda_cmd(pip_cmd, log):
        print_status("TORQ Silo built successfully.", "success")
        return True
    else:
        print_status("Failed to inject PIP dependencies into TORQ silo.", "fail")
        return False

def build_gpu_silo(conda_path: str, log: logging.Logger) -> bool:
    """Builds the specialized GPU4PySCF execution engine for heavy ab initio."""
    env_name = "cochem_gpu_silo"
    print_status(f"Building Ab Initio GPU Silo '{env_name}' (GPU4PySCF)...", "info")
    
    create_cmd = [conda_path, "create", "-y", "-c", "conda-forge", "-n", env_name, "python=3.11", "numpy", "scipy", "h5py"]
    if not run_conda_cmd(create_cmd, log):
        log.warning(f"Conda create failed. Attempting forced upgrade on existing {env_name}...")
        upgrade_cmd = [conda_path, "install", "-y", "-c", "conda-forge", "-n", env_name, "python=3.11", "numpy", "scipy", "h5py"]
        if not run_conda_cmd(upgrade_cmd, log):
            print_status("Failed to create or upgrade Ab Initio GPU Silo.", "fail")
            return False
         
    enforce_pip_upgrades(conda_path, env_name, log)
    
    print_status("Injecting PySCF and pre-compiled GPU4PySCF wheels...", "info")
    pip_cmd = [conda_path, "run", "-n", env_name, "pip", "install", "pyscf", "gpu4pyscf"]
    
    if run_conda_cmd(pip_cmd, log):
        print_status("GPU Silo built successfully.", "success")
        return True
    else:
        print_status("Failed to inject PySCF into GPU silo.", "warning")
        return False

# ---------------------------------------------------------
# MAIN EXECUTION
# ---------------------------------------------------------
def main():
    print(f"\n{Colors.BOLD}--- CoChem Phase 4: Micro-Silo Orchestration ---{Colors.ENDC}")
    
    log = setup_phase4_logging()
    log.info("Phase 4 Execution Started.")
    
    try:
        conda_path = find_conda(log)
        print_status(f"Package Manager Detected: {conda_path}", "success")
    except RuntimeError as e:
        print_status(str(e), "fail")
        log.error(str(e))
        raise
        
    selected_modules = get_selected_modules()
    
    # State record for Phase 5 Golden Gatekeeper aggregation
    state_record = {
        "phase": 4,
        "torq_silo_active": False,
        "gpu_silo_active": False
    }
    
    if "ALL" in selected_modules or any(mod in selected_modules for mod in ["CoChem-TOPOS", "CoChem-TORQ", "CoChem-SCAN", "CoChem-SpycFit", "CoChem-LUMOS"]):
        if build_torq_silo(conda_path, log):
            state_record["torq_silo_active"] = True
    else:
        print_status("Skipping TORQ Silo (Not required by deployment manifest)", "info")
        
    if "ALL" in selected_modules or any(mod in selected_modules for mod in ["CoChem-TORQ", "CoChem-SCAN", "CoChem-SpycFit", "CoChem-LUMOS"]):
        if build_gpu_silo(conda_path, log):
            state_record["gpu_silo_active"] = True
    else:
        print_status("Skipping GPU PySCF Silo (Not required by deployment manifest)", "info")
        
    os.makedirs("cochem_setup", exist_ok=True)
    state_path = os.path.join("cochem_setup", "cochem_state_p4.json")
    
    try:
        with open(state_path, "w") as f:
            json.dump(state_record, f, indent=4)
        print_status(f"Phase 4 state locked to cochem_setup/cochem_state_p4.json", "success")
        log.info("Phase 4 completed successfully.")
        
    except Exception as e:
        print_status(f"Fatal error writing Phase 4 state: {e}", "fail")
        log.error(f"Write error: {e}")
        raise RuntimeError(f"Phase 4 Registry Lock Failed: {e}")

if __name__ == "__main__":
    main()