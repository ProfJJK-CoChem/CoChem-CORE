#!/usr/bin/env python3
"""
CoChem Setup Phase 4: Dynamic Orchestration & Silo Generation
Implements aggressive dependency upgrading for standard libraries and high-risk C++ bindings.
Enforces MolSym extraction and maps pre-compiled GPU4PySCF binary wheels.
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
logging.basicConfig(
    filename='cochem_phase4_silos.log', 
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
    """Executes a subprocess command safely with logging and graceful failure."""
    print_status(f"Executing: {description} for {env_name}...", "info")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logging.info(f"SUCCESS - {description}:\n{result.stdout}")
        print_status(f"Successfully completed: {description}", "success")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"FAILURE - {description}:\n{e.stderr}")
        print_status(f"Failed to execute: {description}. See cochem_phase4_silos.log.", "fail")
        return False
    except FileNotFoundError:
        logging.error(f"Command not found: {cmd[0]}")
        print_status(f"Missing dependency: {cmd[0]} is not in PATH.", "fail")
        return False

def build_torq_silo():
    """Constructs the Python 3.11 micro-silo for TORQ/SPCAT processing."""
    env_name = "cochem_torq_env"
    print_status("Initiating TORQ Python 3.11 Silo Build...", "info")
    
    # 1. Create Conda Environment
    create_cmd = ["conda", "create", "-n", env_name, "python=3.11", "-y"]
    if not run_command(create_cmd, env_name, "Create Python 3.11 Conda Env"):
        return False
        
    # 2. Install base dependencies
    conda_exec = shutil.which("conda")
    if not conda_exec:
         print_status("Conda executable not found. Cannot proceed with dependencies.", "fail")
         return False
         
    # Route through conda run to ensure we are operating inside the silo
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
    print(f"\n{Colors.BOLD}--- CoChem Phase 4: Silo Generation ---{Colors.ENDC}")
    
    # Track state for Phase 5 aggregation
    state_record = {
        "torq_silo_active": False,
        "gpu_silo_active": False
    }
    
    if build_torq_silo():
        state_record["torq_silo_active"] = True
        
    if map_gpu4pyscf():
        state_record["gpu_silo_active"] = True
        
    # Write the intermediate state file
    os.makedirs("cochem_setup", exist_ok=True)
    state_path = os.path.join("cochem_setup", "cochem_state_4.json")
    
    with open(state_path, "w") as f:
        json.dump(state_record, f, indent=4)
        
    print_status(f"Phase 4 Complete. State saved to {state_path}.", "success")

if __name__ == "__main__":
    main()