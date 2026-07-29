# cochem_canvas_target: cochem_setup/cochem_setup_phase_11.py
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

def setup_phase11_logging() -> logging.Logger:
    """Configures the persistent logging subsystem within the strict Artifact Air-Gap."""
    artifact_dir = os.environ.get("COCHEM_ARTIFACT_DIR", str(Path.home() / "CoChem_Artifacts"))
    log_dir = Path(artifact_dir) / "Logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / "cochem_phase11_router.log"
    handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=2)
    formatter = logging.Formatter('%(asctime)s - [%(levelname)s] - %(message)s')
    handler.setFormatter(formatter)
    
    logger = logging.getLogger("CoChem_Phase11")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        logger.addHandler(handler)
        
    return logger

def load_phase_10_status(setup_dir: Path, log: logging.Logger) -> bool:
    """Safely retrieves the MolSym symmetry engine availability."""
    p10_path = setup_dir / "cochem_state_p10.json"
    if p10_path.exists():
        try:
            with open(p10_path, "r") as f:
                p10_data = json.load(f)
                ready = p10_data.get("alignment_engine_ready", False)
                log.info(f"Phase 10 alignment_engine_ready: {ready}")
                return ready
        except json.JSONDecodeError:
            log.warning("Phase 10 state corrupted. Defaulting alignment_engine_ready to False.")
    else:
        log.warning("Phase 10 state missing. Defaulting alignment_engine_ready to False.")
    return False

def calculate_adaptive_tiers(ram_gb: float, cpu_cores: int, vram_gb: float) -> dict:
    """Determines node capabilities and safe operational limits."""
    # Baseline assumption: 1 heavy ORCA core thread requires ~4GB RAM for safe CCSD(T) or large DFT
    safe_concurrent_heavy_jobs = max(1, int(ram_gb // 4.0))
    max_concurrent_heavy_jobs = min(safe_concurrent_heavy_jobs, cpu_cores)
    
    classification = "Tier 3 (Edge/Laptop)"
    if ram_gb >= 60 and cpu_cores >= 16:
        classification = "Tier 1 (HPC/Heavy Workstation)"
    elif ram_gb >= 15 and cpu_cores >= 8:
        classification = "Tier 2 (Standard Workstation)"
        
    return {
        "classification": classification,
        "max_concurrent_heavy_jobs": max_concurrent_heavy_jobs,
        "safe_maxcore_mb_per_thread": 4000 if ram_gb >= 16 else max(1000, int((ram_gb * 1024) / max(1, cpu_cores))),
        "mace_off23_capable": bool(vram_gb >= 4.0 or ram_gb >= 16.0),
        "ccsd_t_capable": bool(ram_gb >= 32.0)
    }

# ---------------------------------------------------------
# MAIN EXECUTION
# ---------------------------------------------------------
def main():
    print(f"\n{Colors.BOLD}--- CoChem Phase 11: Memory Router & Tiering ---{Colors.ENDC}")
    
    log = setup_phase11_logging()
    log.info("Phase 11 Execution Started.")
    
    # Resolve project root dynamically
    repo_root = Path(__file__).resolve().parent.parent
    setup_dir = repo_root / "cochem_setup"
    config_path = setup_dir / "cochem_system_config.json"
    
    if not config_path.exists():
        print_status(f"CRITICAL: {config_path.name} not found. Run Phase 5 first.", "fail")
        raise RuntimeError("Phase 11 Aborted: Master registry not found.")
        
    molsym_ready = load_phase_10_status(setup_dir, log)
    
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
        
        # Workspace Sweep: Purge Phase 10 state
        p10_path = setup_dir / "cochem_state_p10.json"
        if p10_path.exists():
            p10_path.unlink()
            
    except json.JSONDecodeError:
        error_msg = f"FATAL: {config_path.name} is corrupted. Please re-run Phase 5."
        print_status(error_msg, "fail")
        log.error(error_msg)
        raise RuntimeError(error_msg)
    except Exception as e:
        print_status(f"Phase 11 Failed: {str(e)}", "fail")
        log.error(f"Execution Error: {e}")
        raise RuntimeError(f"Phase 11 Aborted: {e}")

if __name__ == "__main__":
    main()