#!/usr/bin/env python3
"""
CoChem-CORE Setup Phase 4: Dynamic Orchestration & Silo Generation
Implements aggressive dependency upgrading for standard libraries and
high-risk C++ bindings via isolated Conda micro-environments.
Dynamically reads cochem_deployment_manifest.json to avoid installing
unnecessary multi-gigabyte GPU tensors.
"""

import os
import sys
import json
import logging
import subprocess
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
    logger = logging.getLogger("CoChem_Phase4")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = RotatingFileHandler(os.path.join(log_dir, 'cochem_phase4_silos.log'), maxBytes=5*1024*1024, backupCount=3)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - [Phase4] - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger

log = setup_logging()

# ---------------------------------------------------------
# SILO GENERATION FUNCTIONS
# ---------------------------------------------------------

def load_deployment_manifest() -> list:
    """Reads the UI-generated manifest. If missing, defaults to CORE-only."""
    manifest_path = Path("cochem_deployment_manifest.json")
    if not manifest_path.exists():
        log.warning("Deployment manifest missing. Falling back to Core install.")
        return ["CoChem-CORE"]
    try:
        with open(manifest_path, "r") as f:
            data = json.load(f)
            modules = data.get("selected_modules", ["CoChem-CORE"])
            log.info(f"Loaded manifest with modules: {modules}")
            return modules
    except json.JSONDecodeError as e:
        log.error(f"Manifest decode failed: {e}")
        return ["CoChem-CORE"]

def find_conda() -> str:
    """Locates Conda or Mamba to trigger silo generation."""
    for exe in ["mamba", "conda"]:
        path = shutil.which(exe)
        if path:
            return path
    raise FileNotFoundError("Neither Conda nor Mamba is installed. Cannot provision silos.")

def build_torq_silo(conda_path: str) -> bool:
    """Builds the C++ constrained environment for topological conformer searches."""
    env_name = "CoChem-TORQ-Silo"
    print_status(f"Provisioning explicit Python 3.11 environment: {env_name}...", "info")
    try:
        # Create env
        subprocess.run([conda_path, "create", "-n", env_name, "python=3.11", "-y"], check=True, capture_output=True)
        # Install exact dependencies
        print_status("Injecting networkx, rdkit, and mace-torch into TORQ Silo...", "info")
        pip_path = f"$(conda info --base)/envs/{env_name}/bin/pip"
        subprocess.run(f"conda run -n {env_name} pip install --upgrade pip", shell=True, check=True)
        subprocess.run(f"conda run -n {env_name} pip install networkx rdkit mace-torch", shell=True, check=True)
        print_status("TORQ Silo Provisioned Successfully.", "success")
        log.info("CoChem-TORQ-Silo built and configured.")
        return True
    except subprocess.CalledProcessError as e:
        print_status(f"Failed to build {env_name}.", "fail")
        log.error(f"Silo creation failed: {e}")
        return False

def build_gpu_silo(conda_path: str) -> bool:
    """Builds the GPU-accelerated environment mapping to pre-compiled PySCF wheels."""
    env_name = "CoChem-GPU-Silo"
    print_status(f"Provisioning PySCF/GPU accelerated environment: {env_name}...", "info")
    try:
        subprocess.run([conda_path, "create", "-n", env_name, "python=3.11", "-y"], check=True, capture_output=True)
        # Assuming CUDA 12 is handled by the devcontainer image, we install the specific GPU wheel.
        print_status("Injecting gpu4pyscf binding matrix...", "info")
        subprocess.run(f"conda run -n {env_name} pip install pyscf gpu4pyscf-cuda12", shell=True, check=True)
        print_status("GPU Silo Provisioned Successfully.", "success")
        log.info("CoChem-GPU-Silo built and configured.")
        return True
    except subprocess.CalledProcessError as e:
        print_status(f"Failed to build {env_name}.", "warning")
        log.warning(f"GPU Silo creation failed (Hardware may not support CUDA): {e}")
        return False

# ---------------------------------------------------------
# MAIN EXECUTION
# ---------------------------------------------------------
def main():
    print(f"\n{Colors.BOLD}--- CoChem Phase 4: Dynamic Micro-Silo Orchestration ---{Colors.ENDC}")
    
    selected_modules = load_deployment_manifest()
    
    try:
        conda_path = find_conda()
    except FileNotFoundError as e:
        print_status(str(e), "fail")
        sys.exit(1)

    # Base state for Phase 5 aggregation
    state_record = {
        "phase": 4,
        "torq_silo_active": False,
        "gpu_silo_active": False
    }
    
    # Build Torq Silo if any geometry/ML tool is selected
    if any(mod in selected_modules for mod in ["CoChem-TOPOS", "CoChem-TORQ", "CoChem-SCAN", "CoChem-SpycFit", "CoChem-LUMOS"]):
        if build_torq_silo(conda_path):
            state_record["torq_silo_active"] = True
    else:
        print_status("Skipping TORQ Silo (Not required by deployment manifest)", "info")
        
    # Build GPU Silo if heavy ab initio/spectroscopy tools are selected
    if any(mod in selected_modules for mod in ["CoChem-TORQ", "CoChem-SCAN", "CoChem-SpycFit", "CoChem-LUMOS"]):
        if build_gpu_silo(conda_path):
            state_record["gpu_silo_active"] = True
    else:
        print_status("Skipping GPU PySCF Silo (Not required by deployment manifest)", "info")
        
    # Write the intermediate state file
    os.makedirs("cochem_setup", exist_ok=True)
    state_path = os.path.join("cochem_setup", "cochem_state_p4.json")
    
    try:
        with open(state_path, "w") as f:
            json.dump(state_record, f, indent=4)
        print_status(f"Phase 4 state successfully locked to {state_path}", "success")
        log.info("Phase 4 execution completed.")
    except IOError as e:
        print_status(f"Failed to write state file: {e}", "fail")
        log.error(f"IOError during state save: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()