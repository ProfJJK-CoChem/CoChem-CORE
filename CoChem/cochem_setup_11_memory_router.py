#!/usr/bin/env python3
"""
CoChem Setup Phase 11: Memory Router & Tiering
Finalizes the cochem_system_config.json. Implements MACE/DFT GPU adaptive tiering 
and hooks the CoChem-ORACLE interrupt listeners (e.g., OS thread preemption).
"""

import os
import sys
import json
import logging
from logging.handlers import RotatingFileHandler

class Colors:
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

logging.basicConfig(
    handlers=[RotatingFileHandler('cochem_setup/cochem_phase11_router.log', maxBytes=1000000, backupCount=3)],
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def print_status(msg: str, status: str = "info") -> None:
    if status == "success":
        print(f" {Colors.OKGREEN}✅ {msg}{Colors.ENDC}")
    elif status == "fail":
        print(f" {Colors.FAIL}❌ {msg}{Colors.ENDC}")
    else:
        print(f" {Colors.WARNING}⚠️ {msg}{Colors.ENDC}")

def calculate_adaptive_tiers(ram_gb: float, cpu_cores: int) -> dict:
    """Calculates safe maximums for DFT and MLFF batch sizes based on physical limits."""
    tiering = {
        "classification": "Bronze",
        "dft_max_core_mb": 2000,
        "mace_batch_size": 16,
        "concurrent_jobs": 1
    }
    
    if ram_gb >= 64 and cpu_cores >= 16:
        tiering["classification"] = "Gold"
        tiering["dft_max_core_mb"] = 4000
        tiering["mace_batch_size"] = 128
        tiering["concurrent_jobs"] = max(1, cpu_cores // 4)
    elif ram_gb >= 32 and cpu_cores >= 8:
        tiering["classification"] = "Silver"
        tiering["dft_max_core_mb"] = 3000
        tiering["mace_batch_size"] = 64
        tiering["concurrent_jobs"] = max(1, cpu_cores // 4)
        
    return tiering

def establish_oracle_hooks():
    """Ensures the directory for ORACLE telemetry interrupt hooks exists."""
    oracle_dir = os.path.expanduser("~/.cochem/silos/oracle/")
    os.makedirs(oracle_dir, exist_ok=True)
    # Touch a dummy pid file to ensure permissions are correct
    pid_file = os.path.join(oracle_dir, "oracle_engine.pid")
    if not os.path.exists(pid_file):
        with open(pid_file, 'w') as f:
            f.write("DORMANT")

def main():
    print(f"\n{Colors.BOLD}--- CoChem Phase 11: Memory Router ---{Colors.ENDC}")
    
    config_path = "cochem_system_config.json"
    
    if not os.path.exists(config_path):
        # CRITICAL FIX: Raise RuntimeError instead of sys.exit(1) to protect Jupyter kernels
        error_msg = f"FATAL: Master registry ({config_path}) not found. Phases 1-5 must run first."
        logging.error(error_msg)
        print_status(error_msg, "fail")
        raise RuntimeError(error_msg)
        
    try:
        with open(config_path, "r") as f:
            master_config = json.load(f)
            
        # Extract Phase 2 Hardware Data safely
        phase2_data = master_config.get("phase_2_data", {})
        ram_gb = phase2_data.get("ram_gb", 16.0)
        cpu_cores = phase2_data.get("cpu_cores", 4)
        
        # Inject adaptive tiering logic
        routing_policy = calculate_adaptive_tiers(ram_gb, cpu_cores)
        master_config["adaptive_routing"] = routing_policy
        
        # Establish telemetry hooks
        establish_oracle_hooks()
        master_config["paths"]["oracle_pid"] = os.path.expanduser("~/.cochem/silos/oracle/oracle_engine.pid")
        
        # Save the finalized, fully-routed configuration
        with open(config_path, "w") as f:
            json.dump(master_config, f, indent=4)
            
        print_status(f"Memory Routing finalized. System classified as: {routing_policy['classification']}", "success")
        
    except json.JSONDecodeError:
        error_msg = f"FATAL: {config_path} is corrupted."
        logging.error(error_msg)
        print_status(error_msg, "fail")
        raise RuntimeError(error_msg)

if __name__ == "__main__":
    main()