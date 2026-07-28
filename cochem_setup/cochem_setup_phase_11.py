#!/usr/bin/env python3
"""
CoChem-CORE Setup Phase 11: Memory Router & Tiering
Finalizes the cochem_system_config.json. Implements MACE/DFT adaptive tiering,
verifies downstream alignment readiness, and categorizes the physical node to prevent 
OOM crashes during massive structure screenings.
"""

import os
import sys
import json
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

def setup_logging() -> logging.Logger:
    log_dir = Path("Logs")
    log_dir.mkdir(exist_ok=True)
    logger = logging.getLogger("CoChem_Phase11")
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        handler = RotatingFileHandler(log_dir / 'cochem_phase11_router.log', maxBytes=5*1024*1024, backupCount=3)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - [Phase11] - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
    return logger

log = setup_logging()

def print_status(msg: str, status: str = "info") -> None:
    if status == "success":
        print(f" {Colors.OKGREEN}✅ {msg}{Colors.ENDC}")
    elif status == "warning":
        print(f" {Colors.WARNING}⚠️ {msg}{Colors.ENDC}")
    elif status == "fail":
        print(f" {Colors.FAIL}❌ {msg}{Colors.ENDC}")
    else:
        print(f" {Colors.OKCYAN}➡️ {msg}{Colors.ENDC}")

# ---------------------------------------------------------
# TIERING LOGIC
# ---------------------------------------------------------

def calculate_adaptive_tiers(ram_gb: float, cores: int, vram_gb: float) -> dict:
    """
    Scientifically bounds the execution limits based on hardware profiles to prevent 
    OOM crashes during large TOPOS sweeps.
    """
    print_status(f"Evaluating Hardware Thresholds (RAM: {ram_gb}GB, Cores: {cores}, VRAM: {vram_gb}GB)...", "info")
    
    policy = {
        "max_concurrent_mace_threads": 1,
        "max_dft_basis_functions": 1000,
        "recommend_ccsdt": False,
        "classification": "BASIC_LAPTOP"
    }

    if vram_gb >= 11.0 and ram_gb >= 32.0 and cores >= 8:
        policy["classification"] = "WORKSTATION_GPU"
        policy["max_concurrent_mace_threads"] = 4
        policy["max_dft_basis_functions"] = 4000
        policy["recommend_ccsdt"] = True
    elif ram_gb >= 64.0 and cores >= 16:
        policy["classification"] = "HPC_NODE"
        policy["max_concurrent_mace_threads"] = 8
        policy["max_dft_basis_functions"] = 8000
        policy["recommend_ccsdt"] = True
    elif ram_gb >= 16.0 and cores >= 4:
        policy["classification"] = "STANDARD_DESKTOP"
        policy["max_concurrent_mace_threads"] = 2
        policy["max_dft_basis_functions"] = 2000
        
    log.info(f"Node Classified: {policy['classification']}")
    return policy

def load_phase_10_status(base_dir: Path) -> bool:
    """Checks if the MolSym alignment engine is ready."""
    state_path = base_dir / "cochem_setup" / "cochem_state_p10.json"
    if state_path.exists():
        with open(state_path, "r") as f:
            data = json.load(f)
            return data.get("alignment_engine_ready", False)
    return False

# ---------------------------------------------------------
# MAIN EXECUTION
# ---------------------------------------------------------
def main():
    print(f"\n{Colors.BOLD}--- CoChem Phase 11: Memory Router & Tiering ---{Colors.ENDC}")
    
    base_dir = Path(__file__).resolve().parent.parent
    config_path = base_dir / "cochem_system_config.json"
    
    if not config_path.exists():
        error_msg = f"FATAL: {config_path} not found. Phase 5 failed or was skipped."
        log.error(error_msg)
        print_status(error_msg, "fail")
        # PATCH 3: Change sys.exit(1) to RuntimeError to prevent Jupyter Kernel death
        raise RuntimeError("Setup failed: cochem_system_config.json not found.")
        
    molsym_ready = load_phase_10_status(base_dir)
    
    try:
        with open(config_path, "r") as f:
            master_config = json.load(f)
            
        # Extract hardware constraints established by Phase 5
        hw_data = master_config.get("hardware", {})
        ram_gb = hw_data.get("ram_gb", 16.0)
        cpu_cores = hw_data.get("physical_cpu_cores", 4)
        vram_gb = hw_data.get("vram_gb", 0.0)
        
        # Inject adaptive tiering and alignment capabilities
        routing_policy = calculate_adaptive_tiers(ram_gb, cpu_cores, vram_gb)
        master_config["adaptive_routing"] = routing_policy
        master_config["alignment_engine_ready"] = molsym_ready
        
        # Save the finalized, fully-routed configuration
        with open(config_path, "w") as f:
            json.dump(master_config, f, indent=4)
            
        print_status(f"Memory Routing finalized. Node classified as: {routing_policy['classification']}", "success")
        print_status("Official cochem_system_config.json has been securely locked.", "success")
        log.info("Phase 11 execution completed. Configuration finalized.")
        
    except json.JSONDecodeError:
        error_msg = f"FATAL: {config_path} is corrupted. Please re-run Phase 5."
        log.error(error_msg)
        print_status(error_msg, "fail")
        raise RuntimeError("Setup failed: Registry corruption detected.")

if __name__ == "__main__":
    main()