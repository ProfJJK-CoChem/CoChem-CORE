# cochem_canvas_target: cochem_setup/cochem_setup_phase_5.py
#!/usr/bin/env python3
"""
CoChem-CORE Setup Phase 5: IPC Config Lock & Workspace Sweep
Aggregates Phase 1-4 ephemeral states, enforces strict validation 
via the Golden Gatekeeper, and mints the foundational `cochem_system_config.json`.
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler

# Dynamic Pathing to access the Core Engine schemas
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "core_engine"))

try:
    from cochem_core_registry_schema import (
        CoChemConfig, HardwareConfig, EnginePaths, EngineInfo, SiloConfig
    )
    PYDANTIC_ACTIVE = True
except ImportError as e:
    PYDANTIC_ACTIVE = False
    print(f"⚠️ Pydantic Registry Schemas not found in core_engine. Using strict dictionary fallback.\n({e})")

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
    """Standardized console UI output."""
    if status == "success":
        print(f" {Colors.OKGREEN}✅ {msg}{Colors.ENDC}")
    elif status == "warning":
        print(f" {Colors.WARNING}⚠️ {msg}{Colors.ENDC}")
    elif status == "fail":
        print(f" {Colors.FAIL}❌ {msg}{Colors.ENDC}")
    else:
        print(f" {Colors.OKCYAN}➡️ {msg}{Colors.ENDC}")

def setup_phase5_logging() -> logging.Logger:
    """Configures the persistent logging subsystem within the strict Artifact Air-Gap."""
    artifact_dir = os.environ.get("COCHEM_ARTIFACT_DIR", str(Path.home() / "CoChem_Artifacts"))
    log_dir = Path(artifact_dir) / "Logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / "cochem_phase5_gatekeeper.log"
    handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=2)
    formatter = logging.Formatter('%(asctime)s - [%(levelname)s] - %(message)s')
    handler.setFormatter(formatter)
    
    logger = logging.getLogger("CoChem_Phase5")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        logger.addHandler(handler)
        
    return logger

# ---------------------------------------------------------
# GOLDEN GATEKEEPER COMPILATION
# ---------------------------------------------------------
def load_ephemeral_state(setup_dir: Path, phase_num: int) -> dict:
    """Loads a specific ephemeral state JSON from previous phases."""
    state_file = setup_dir / f"cochem_state_p{phase_num}.json"
    if not state_file.exists():
        raise FileNotFoundError(f"Missing state file: {state_file.name}. Phase {phase_num} did not complete.")
    with open(state_file, "r") as f:
        return json.load(f)

def compile_master_registry(setup_dir: Path, log: logging.Logger) -> bool:
    """Aggregates all phase states and validates them against the Golden Schema."""
    print_status("Aggregating ephemeral states from Phases 1-4...", "info")
    
    try:
        p2 = load_ephemeral_state(setup_dir, 2)
        p3 = load_ephemeral_state(setup_dir, 3)
        p4 = load_ephemeral_state(setup_dir, 4)
        
        raw_config = {
            "schema_version": "1.0.0",
            "last_updated": datetime.now().isoformat(),
            "hardware": {
                "physical_cpu_cores": p2.get("physical_cpu_cores", 1),
                "logical_cpu_cores": p2.get("logical_cpu_cores", 1),
                "ram_gb": p2.get("ram_gb", 4.0),
                "avx512_support": p2.get("avx512_support", False),
                "gpu_profile": p2.get("gpu_profile", "None"),
                "vram_gb": p2.get("vram_gb", 0.0),
                "subnormal_precision_trap": p2.get("subnormal_precision_trap", False),
                "os_target": p2.get("os_target", "linux_x86_64")
            },
            "engines": p3.get("engines", {}),
            "silos": {
                "torq_silo_active": p4.get("torq_silo_active", False),
                "gpu_silo_active": p4.get("gpu_silo_active", False)
            }
        }
        
        # Schema Validation execution
        if PYDANTIC_ACTIVE:
            print_status("Executing strict Pydantic schema validation (Golden Gatekeeper)...", "info")
            validated_config = CoChemConfig(**raw_config).model_dump()
        else:
            print_status("Bypassing Pydantic validation, compiling strict JSON layout...", "warning")
            validated_config = raw_config

        config_path = setup_dir / "cochem_system_config.json"
        with open(config_path, "w") as f:
            json.dump(validated_config, f, indent=4)
            
        print_status(f"Authoritative Registry locked: {config_path}", "success")
        log.info(f"System Configuration Successfully Compiled: {config_path}")
        return True

    except Exception as e:
        print_status(f"Schema Validation or Golden Gatekeeper Error! Check types.", "fail")
        log.error(f"Registry Compilation Exception: {e}")
        return False

def cleanup_states(setup_dir: Path, log: logging.Logger) -> None:
    """Purges the temporary state files to clean the workspace and prevent registry ghosting."""
    print_status("Performing workspace sweep of ephemeral states...", "info")
    cleaned = 0
    for file_path in setup_dir.glob("cochem_state_p*.json"):
        try:
            file_path.unlink()
            cleaned += 1
            log.info(f"Purged transient state: {file_path.name}")
        except OSError as e:
            log.warning(f"Failed to remove {file_path.name}: {e}")
            
    print_status(f"Workspace sweep complete. Swept {cleaned} dangling files.", "success")

# ---------------------------------------------------------
# MAIN EXECUTION
# ---------------------------------------------------------
def main():
    print(f"\n{Colors.BOLD}--- CoChem Phase 5: IPC Config Lock & Workspace Sweep ---{Colors.ENDC}")
    log = setup_phase5_logging()
    
    setup_dir = Path("cochem_setup")
    if not setup_dir.exists():
        setup_dir = REPO_ROOT / "cochem_setup"
        
    if not setup_dir.exists():
        print_status("cochem_setup/ directory is missing. Run Phases 1-4 first.", "fail")
        raise RuntimeError("Phase 5 Aborted: Execution context directory 'cochem_setup/' not found.")
        
    if compile_master_registry(setup_dir, log):
        cleanup_states(setup_dir, log)
        print(f"\n{Colors.BOLD}{Colors.OKGREEN}✅ CoChem Environment Phase 1-5 successfully unified.{Colors.ENDC}")
    else:
        print(f"\n{Colors.BOLD}{Colors.FAIL}❌ Registry Finalization Failed.{Colors.ENDC}")
        raise RuntimeError("Phase 5 Aborted: Master registry compilation failed.")

if __name__ == "__main__":
    main()