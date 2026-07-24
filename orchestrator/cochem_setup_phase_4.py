#!/usr/bin/env python3
"""
CoChem Setup Phase 4: Dynamic Orchestration & Silo Generation
Implements aggressive dependency upgrading for standard libraries and
high-risk C++ bindings via isolated Conda micro-environments.
Dynamically reads cochem_deployment_manifest.json to avoid installing
unnecessary multi-gigabyte GPU tensors.
"""

import os
import sys
import subprocess
import shutil
import json
import logging
import urllib.request
import tarfile
from pathlib import Path

# Setup logging trace
os.makedirs("Logs", exist_ok=True)
logging.basicConfig(
    filename='Logs/cochem_phase4_silos.log', 
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

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

def run_command(cmd: list, env_name: str, description: str) -> bool:
    """Executes a subprocess command, traps output, and logs safely."""
    print_status(f"[{env_name}] {description}...", "info")
    try:
        # capture_output=True prevents massive Conda readouts from freezing the Jupyter cell
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        logging.info(f"SUCCESS: {description}\n{result.stdout}")
        print_status(f"Success: {description}", "success")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"FAILED: {description}\n{e.stderr}")
        print_status(f"Failed: {description}. Check Logs/cochem_phase4_silos.log.", "fail")
        return False

def build_torq_silo():
    """Constructs an isolated Conda environment for Math & Topology logic (TORQ/TOPOS)."""
    print_status("Provisioning TORQ Mathematical Silo...", "info")
    env_name = "cochem_torq_silo"
    
    create_cmd = ["conda", "create", "-n", env_name, "python=3.10", "-y"]
    if not run_command(create_cmd, env_name, "Create TORQ Silo"):
        return False
        
    deps_cmd = ["conda", "run", "-n", env_name, "pip", "install", 
                "numpy", "scipy", "networkx", "ase", "pyarrow"]
    
    if not run_command(deps_cmd, env_name, "Install TORQ Mathematical Stack"):
        return False
        
    return True

def map_gpu4pyscf():
    """Maps pre-compiled binary wheels instead of compiling C++ source to prevent compiler traps."""
    print_status("Mapping GPU4PySCF binary wheels...", "info")
    env_name = "cochem_gpu_silo"
    
    create_cmd = ["conda", "create", "-n", env_name, "python=3.10", "-y"]
    if not run_command(create_cmd, env_name, "Create GPU PySCF Silo"):
        return False
        
    # Use pip to pull the pre-compiled wheel rather than source
    install_cmd = ["conda", "run", "-n", env_name, "pip", "install", "gpu4pyscf", "pyscf"]
    if not run_command(install_cmd, env_name, "Install pre-compiled GPU4PySCF"):
        return False
        
    return True

def main():
    print(f"\n{Colors.BOLD}--- CoChem Phase 4: Dynamic Silo Generation ---{Colors.ENDC}")
    
    # Ingest manifest to dynamically skip unselected silos
    manifest_path = "cochem_deployment_manifest.json"
    selected_modules = []
    
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
                # Parse either list format or dictionary format (depending on GUI iteration)
                raw_modules = manifest.get("active_modules", [])
                if isinstance(raw_modules, dict):
                    selected_modules = list(raw_modules.keys())
                else:
                    selected_modules = raw_modules
            print_status(f"Loaded deployment manifest. Found {len(selected_modules)} active modules.", "success")
        except Exception as e:
            logging.warning(f"Could not parse manifest: {e}. Defaulting to all silos.")
            selected_modules = ["CoChem-TOPOS", "CoChem-TORQ", "CoChem-SCAN", "CoChem-SpycFit", "CoChem-LUMOS"]
    else:
        print_status("Deployment manifest not found. Enforcing full ecosystem installation.", "warning")
        selected_modules = ["CoChem-TOPOS", "CoChem-TORQ", "CoChem-SCAN", "CoChem-SpycFit", "CoChem-LUMOS"]
            
    # Track state for Phase 5 aggregation
    state_record = {
        "phase": 4,
        "torq_silo_active": False,
        "gpu_silo_active": False
    }
    
    # Build Torq Silo if any geometry/ML tool is selected
    if any(mod in selected_modules for mod in ["CoChem-TOPOS", "CoChem-TORQ", "CoChem-SCAN", "CoChem-SpycFit", "CoChem-LUMOS"]):
        if build_torq_silo():
            state_record["torq_silo_active"] = True
    else:
        print_status("Skipping TORQ Silo (Not required by deployment manifest)", "info")
        
    # Build GPU Silo if heavy ab initio/spectroscopy tools are selected
    if any(mod in selected_modules for mod in ["CoChem-TORQ", "CoChem-SCAN", "CoChem-SpycFit", "CoChem-LUMOS"]):
        if map_gpu4pyscf():
            state_record["gpu_silo_active"] = True
    else:
        print_status("Skipping GPU PySCF Silo (Not required by deployment manifest)", "info")
        
    # Write the intermediate state file
    os.makedirs("cochem_setup", exist_ok=True)
    state_path = os.path.join("cochem_setup", "cochem_state_4.json")
    try:
        with open(state_path, "w") as f:
            json.dump(state_record, f, indent=4)
        print_status(f"Phase 4 state successfully locked to {state_path}", "success")
    except IOError as e:
        print_status(f"Failed to write state file: {e}", "fail")
        sys.exit(1)

if __name__ == "__main__":
    main()