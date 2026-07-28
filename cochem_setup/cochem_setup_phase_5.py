#!/usr/bin/env python3
"""
CoChem-CORE Setup Phase 5: IPC Config Lock & Workspace Sweep
Aggregates Phase 1-4 ephemeral states, enforces strict Pydantic validation 
via the Golden Gatekeeper, and mints the foundational `cochem_system_config.json`.
"""

import os
import sys
import json
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler

# Dynamic Pathing to access the Core Engine schemas
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "core_engine"))

try:
    from cochem_core_registry_schema import (
        CoChemConfig, HardwareConfig, EnginePaths, EngineInfo, SiloConfig
    )
except ImportError as e:
    print(f"FATAL: Pydantic Registry Schemas not found. Did you delete 'core_engine/cochem_core_registry_schema.py'?\n{e}")
    sys.exit(1)

# ---------------------------------------------------------
# UI & LOGGING PROTOCOLS
# ---------------------------------------------------------
class Colors:
    HEADER = '\033[95m'
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

def setup_logging() -> logging.Logger:
    log_dir = REPO_ROOT / "Logs"
    log_dir.mkdir(exist_ok=True)
    logger = logging.getLogger("CoChem_Phase5")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = RotatingFileHandler(log_dir / 'cochem_phase5_finalize.log', maxBytes=5*1024*1024, backupCount=3)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - [Phase5] - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger

log = setup_logging()

# ---------------------------------------------------------
# AGGREGATION FUNCTIONS
# ---------------------------------------------------------

def load_state(phase_num: int, setup_dir: Path) -> dict:
    """Loads a specific ephemeral state file."""
    state_path = setup_dir / f"cochem_state_p{phase_num}.json"
    if not state_path.exists():
        raise FileNotFoundError(f"Missing state file: {state_path.name}. Pipeline broken.")
    with open(state_path, "r") as f:
        return json.load(f)

def compile_master_registry(setup_dir: Path) -> bool:
    """
    Consumes all intermediate JSON states, maps them to Pydantic schemas, 
    and writes out the un-editable golden registry.
    """
    print_status("Aggregating ephemeral state blocks...", "info")
    
    try:
        p2 = load_state(2, setup_dir)
        p3 = load_state(3, setup_dir)
        p4 = load_state(4, setup_dir)
        
        # Structure into Pydantic models
        hw_config = HardwareConfig(**p2)
        
        # Engine parsing
        e_data = p3.get("engines", {})
        orca_info = EngineInfo(**e_data.get("orca", {"status": "missing"}))
        mpi_info = EngineInfo(**e_data.get("mpirun", {"status": "missing"}))
        xtb_info = EngineInfo(**e_data.get("xtb", {"status": "missing"}))
        engine_config = EnginePaths(orca=orca_info, mpirun=mpi_info, xtb=xtb_info)
        
        silo_config = SiloConfig(
            torq_silo_active=p4.get("torq_silo_active", False),
            gpu_silo_active=p4.get("gpu_silo_active", False)
        )
        
        master_config = CoChemConfig(
            hardware=hw_config,
            engines=engine_config,
            silos=silo_config
        )
        
        # Write out to the protected root level
        registry_path = REPO_ROOT / "cochem_system_config.json"
        with open(registry_path, "w") as f:
            f.write(master_config.model_dump_json(indent=4))
            
        print_status(f"Pydantic Validation Passed. Golden Registry minted to: cochem_system_config.json", "success")
        log.info("Master Registry successfully serialized through Pydantic RAM boundary.")
        return True
        
    except Exception as e:
        print_status("Schema Validation or Golden Gatekeeper Error! Check types.", "fail")
        log.error(f"Registry Compilation Exception: {e}")
        return False

def cleanup_states(setup_dir: Path) -> None:
    """Purges the temporary state files to clean the workspace and prevent registry ghosting."""
    print_status("Performing workspace sweep of ephemeral states...", "info")
    cleaned = 0
    for file_path in setup_dir.glob("cochem_state_*.json"):
        try:
            file_path.unlink()
            cleaned += 1
            log.info(f"Purged transient state: {file_path.name}")
        except OSError as e:
            log.warning(f"Failed to remove {file_path.name}: {e}")
            
    print_status(f"Workspace sweep complete. Swept {cleaned} dangling files.", "success")

def main():
    print(f"\n{Colors.BOLD}--- CoChem Phase 5: IPC Config Lock & Workspace Sweep ---{Colors.ENDC}")
    
    setup_dir = REPO_ROOT / "cochem_setup"
    if not setup_dir.exists():
        print_status("cochem_setup/ directory is missing. Run Phases 1-4 first.", "fail")
        sys.exit(1)
        
    if compile_master_registry(setup_dir):
        cleanup_states(setup_dir)
        print(f"\n{Colors.BOLD}{Colors.OKGREEN}CoChem Environment Phase 1-5 successfully unified.{Colors.ENDC}")
    else:
        print(f"\n{Colors.BOLD}{Colors.FAIL}Pipeline halted during Pydantic compilation.{Colors.ENDC}")
        sys.exit(1)

if __name__ == "__main__":
    main()