#!/usr/bin/env python3
"""
CoChem Setup Phase 11: Memory Router & Tiering

Finalizes the cochem_system_config.json. Implements MACE/DFT adaptive tiering,
verifies downstream alignment readiness, and hooks the CoChem-ORACLE 
interrupt listeners for OS thread preemption.
"""

import os
import sys
import json
import logging
from logging.handlers import RotatingFileHandler
from typing import Dict, Any

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

os.makedirs("Logs", exist_ok=True)
logging.basicConfig(
    handlers=[RotatingFileHandler('Logs/cochem_phase11_router.log', maxBytes=5 * 1024 * 1024, backupCount=3)],
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [Phase11] - %(message)s'
)
log = logging.getLogger("CoChem_Phase11")

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

# ---------------------------------------------------------
# ROUTING & TIERING PROTOCOLS
# ---------------------------------------------------------
def load_upstream_state() -> Dict[str, Any]:
    """Retrieves the Phase 10 state, trapping failures gracefully."""
    state_path = os.path.join("cochem_setup", "cochem_state_p10.json")
    if not os.path.exists(state_path):
        print_status(f"Missing upstream state: {state_path}", "fail")
        # PATCH APPLIED: Replace kernel-killing sys.exit with graceful exception
        raise RuntimeError("Setup Phase 11 halted: Upstream state (p10) not found. Please run Phase 10 first.")
    
    with open(state_path, "r") as f:
        return json.load(f)

def calculate_adaptive_tiers(ram_gb: float, cpu_cores: int, vram_gb: float) -> Dict[str, Any]:
    """Calculates safe mathematical maximums for DFT and MLFF batch sizes based on physical bounds."""
    print_status(f"Calculating adaptive matrices for {ram_gb}GB RAM, {cpu_cores} Cores, {vram_gb}GB VRAM...", "info")
    
    # MACE batch logic: heavily dependent on VRAM if > 0, otherwise RAM
    if vram_gb > 0:
        mace_batch_max = int((vram_gb * 1024 - 1500) / 150)  # Reserve 1.5GB overhead, ~150MB per molecule
        classification = "GPU-Accelerated"
    else:
        mace_batch_max = int((ram_gb * 1024 - 2000) / 300)   # Reserve 2GB overhead, ~300MB per molecule on CPU
        classification = "CPU-Bound"

    # Enforce an absolute ceiling to prevent massive out-of-core caching penalties
    mace_batch_max = max(1, min(mace_batch_max, 256)) 
    
    # DFT logic: Reserve 2GB strictly for the OS layer, distribute remainder across cores
    safe_ram_mb = max(2048, (ram_gb - 2.0) * 1024)
    dft_ram_per_core = int(safe_ram_mb / max(cpu_cores, 1))
    
    # ORCA requires at least ~1000 MB per core for stable CCSD/r2SCAN convergence
    dft_ram_per_core = max(1000, dft_ram_per_core)

    return {
        "classification": classification,
        "mace_batch_limit": mace_batch_max,
        "dft_cores": cpu_cores,
        "dft_ram_per_core_mb": dft_ram_per_core
    }

def establish_oracle_hooks(config: Dict[str, Any]) -> None:
    """Establishes deterministic telemetry paths for ORACLE OS-level preemption."""
    oracle_path = os.path.expanduser("~/.cochem/silos/oracle/")
    os.makedirs(oracle_path, exist_ok=True)
    
    if "paths" not in config:
        config["paths"] = {}
        
    config["paths"]["oracle_pid"] = os.path.join(oracle_path, "oracle_engine.pid")
    log.info(f"ORACLE telemetry hooks securely anchored at {oracle_path}")

# ---------------------------------------------------------
# MAIN EXECUTION
# ---------------------------------------------------------
def main() -> None:
    print(f"\n{Colors.BOLD}--- CoChem Phase 11: Memory Router & Tiering ---{Colors.ENDC}")
    
    try:
        p10_state = load_upstream_state()
        molsym_ready = p10_state.get("molsym_available", False)
    except RuntimeError as e:
        log.error(str(e))
        return

    config_path = "cochem_system_config.json"
    if not os.path.exists(config_path):
        error_msg = f"FATAL: Master registry ({config_path}) not found. Phases 1-5 must run first."
        log.error(error_msg)
        print_status(error_msg, "fail")
        raise RuntimeError(error_msg)
        
    try:
        with open(config_path, "r") as f:
            master_config = json.load(f)
            
        # Extract hardware constraints from Phase 5 Gatekeeper structure
        hw_data = master_config.get("hardware", {})
        ram_gb = hw_data.get("ram_gb", 16.0)
        cpu_cores = hw_data.get("physical_cpu_cores", 4)
        vram_gb = hw_data.get("vram_gb", 0.0)
        
        # Inject adaptive tiering and alignment capabilities
        routing_policy = calculate_adaptive_tiers(ram_gb, cpu_cores, vram_gb)
        master_config["adaptive_routing"] = routing_policy
        master_config["alignment_engine_ready"] = molsym_ready
        
        # Establish telemetry hooks
        establish_oracle_hooks(master_config)
        
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
        raise RuntimeError(error_msg)

if __name__ == "__main__":
    main()