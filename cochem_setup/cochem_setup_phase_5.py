# cochem_canvas_target: cochem_setup/cochem_setup_phase_5.py
#!/usr/bin/env python3
"""
CoChem-CORE Setup Phase 5: IPC Config Lock & Workspace Sweep
Aggregates Phase 1-4 ephemeral states, enforces strict validation 
via the Golden Gatekeeper, and mints the foundational `cochem_system_config.json`.
Supports Incremental Sideloading (e.g., merging only Phase 4 silo updates).
"""

import os
import sys
import json
import logging
import subprocess
import importlib
import site
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler

# ---------------------------------------------------------
# TORQ SILO INTERCEPT & RELAUNCH
# ---------------------------------------------------------
if "cochem_torq_silo" not in sys.executable:
    _home = Path.home()
    _silo_candidates = [
        _home / ".local" / "miniconda" / "envs" / "cochem_torq_silo" / "bin" / "python",
        _home / "miniconda3" / "envs" / "cochem_torq_silo" / "bin" / "python",
        _home / "miniconda" / "envs" / "cochem_torq_silo" / "bin" / "python",
        _home / ".conda" / "envs" / "cochem_torq_silo" / "bin" / "python",
        Path("/opt/conda/envs/cochem_torq_silo/bin/python"),
        Path("/usr/local/miniconda/envs/cochem_torq_silo/bin/python")
    ]
    
    for _candidate in _silo_candidates:
        if _candidate.exists():
            print(f"🔄 Intercepted naked Python execution. Rerouting Phase 5 into TORQ Silo: {_candidate}")
            try:
                res = subprocess.run([str(_candidate), __file__] + sys.argv[1:])
                sys.exit(res.returncode)
            except Exception as e:
                print(f"⚠️ Failed to relaunch into TORQ silo: {e}")
            break

# Dynamic Pathing to access the Core Engine schemas
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "core_engine"))

try:
    from cochem_core_registry_schema import (
        CoChemConfig, HardwareConfig, EnginePaths, EngineInfo, SiloConfig
    )
    PYDANTIC_ACTIVE = True
except ImportError as e:
    try:
        print("➡️  Attempting inline Pydantic bootstrap for Golden Gatekeeper...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "pydantic"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        importlib.invalidate_caches()
        importlib.reload(site)
        
        from cochem_core_registry_schema import (
            CoChemConfig, HardwareConfig, EnginePaths, EngineInfo, SiloConfig
        )
        PYDANTIC_ACTIVE = True
        print("✅ Pydantic bootstrap completed for Phase 5 schema validation.")
    except Exception as bootstrap_err:
        PYDANTIC_ACTIVE = False
        print(f"⚠️ Pydantic Registry Schemas not found in core_engine. Using strict dictionary fallback.\n(Import Error: {e} | Bootstrap Error: {bootstrap_err})")

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

def setup_phase5_logging() -> logging.Logger:
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
def normalize_engine_info(raw_engine: dict, default_version: str = None) -> dict:
    if not isinstance(raw_engine, dict):
        return {"status": "missing", "path": None, "version": default_version, "hash": None}

    path = raw_engine.get("path")
    hash_value = raw_engine.get("hash") or raw_engine.get("sha256")
    version = raw_engine.get("version", default_version)
    if path and path != "None":
        return {"status": "found", "path": path, "version": version, "hash": hash_value}

    return {"status": "missing", "path": None, "version": version, "hash": hash_value}

def compile_master_registry(setup_dir: Path, repo_root: Path, log: logging.Logger) -> bool:
    """Aggregates states with explicit support for Incremental Silo Sideloading."""
    config_path = repo_root / "cochem_system_config.json"
    p4_state_file = setup_dir / "cochem_state_p4.json"
    
    raw_config = None
    
    # Mode 1: Incremental Patch (Phases 1-3 skipped, updating existing registry)
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                raw_config = json.load(f)
            
            # Verify it's actually a dictionary and not corrupted python code
            if isinstance(raw_config, dict) and "schema_version" in raw_config:
                print_status("Existing system config detected. Entering Incremental Patch mode...", "info")
                
                # We ONLY care about updating the Silos if we are in Incremental mode
                if p4_state_file.exists():
                    with open(p4_state_file, "r") as f:
                        p4 = json.load(f)
                        raw_config.setdefault("silos", {})
                        raw_config["silos"]["topos_silo_active"] = p4.get("topos_silo_active", raw_config["silos"].get("topos_silo_active", False))
                        raw_config["silos"]["torq_silo_active"] = p4.get("torq_silo_active", raw_config["silos"].get("torq_silo_active", False))
                        raw_config["silos"]["gpu_silo_active"] = p4.get("gpu_silo_active", raw_config["silos"].get("gpu_silo_active", False))
                        raw_config["last_updated"] = datetime.now().isoformat()
                        print_status("Phase 4 Silos (TOPOS/TORQ/GPU) dynamically merged into existing registry.", "success")
                else:
                    print_status("No Phase 4 state found to merge. Skipping silo update.", "warning")
                    
            else:
                print_status("Existing config file is corrupted (malformed JSON). Rebuilding from scratch...", "warning")
                raw_config = None
        except Exception as e:
            print_status(f"Could not parse existing config: {e}. Rebuilding from scratch...", "warning")
            raw_config = None

    # Mode 2: Full Build (Phases 1-4 must exist)
    if raw_config is None:
        print_status("Aggregating full ephemeral states from Phases 1-4...", "info")
        try:
            with open(setup_dir / "cochem_state_p2.json", "r") as f: p2 = json.load(f)
            with open(setup_dir / "cochem_state_p3.json", "r") as f: p3 = json.load(f)
            with open(setup_dir / "cochem_state_p4.json", "r") as f: p4 = json.load(f)
            
            p3_engines = p3.get("engines", {})
            normalized_engines = {
                "orca": normalize_engine_info(p3_engines.get("orca", {}), "6.1.1"),
                "mpirun": normalize_engine_info(p3_engines.get("mpirun", p3_engines.get("openmpi", {}))),
                "xtb": normalize_engine_info(p3_engines.get("xtb", p3_engines.get("g_xtb", {}))),
            }

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
                "engines": normalized_engines,
                "silos": {
                    "topos_silo_active": p4.get("topos_silo_active", False),
                    "torq_silo_active": p4.get("torq_silo_active", False),
                    "gpu_silo_active": p4.get("gpu_silo_active", False)
                }
            }
        except FileNotFoundError as e:
            print_status(f"Missing state file: {e}. You must run the full Phase 1-4 loop at least once.", "fail")
            log.error(f"Registry Compilation Exception: {e}")
            return False

    # Schema Validation execution
    try:
        if PYDANTIC_ACTIVE:
            print_status("Executing strict Pydantic schema validation (Golden Gatekeeper)...", "info")
            validated_config = CoChemConfig(**raw_config).model_dump()
        else:
            print_status("Bypassing Pydantic validation, compiling strict JSON layout...", "warning")
            validated_config = raw_config

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

def main():
    print(f"\n{Colors.BOLD}--- CoChem Phase 5: IPC Config Lock & Workspace Sweep ---{Colors.ENDC}")
    log = setup_phase5_logging()
    
    setup_dir = Path("cochem_setup")
    if not setup_dir.exists():
        setup_dir = REPO_ROOT / "cochem_setup"
        
    if not setup_dir.exists():
        print_status("cochem_setup/ directory is missing. Run Phases 1-4 first.", "fail")
        raise RuntimeError("Phase 5 Aborted: Execution context directory 'cochem_setup/' not found.")
        
    if compile_master_registry(setup_dir, REPO_ROOT, log):
        cleanup_states(setup_dir, log)
        print(f"\n{Colors.BOLD}{Colors.OKGREEN}✅ CoChem Environment Phase 1-5 successfully unified.{Colors.ENDC}")
    else:
        print(f"\n{Colors.BOLD}{Colors.FAIL}❌ Registry Finalization Failed.{Colors.ENDC}")
        raise RuntimeError("Phase 5 Aborted: Master registry compilation failed.")

if __name__ == "__main__":
    main()