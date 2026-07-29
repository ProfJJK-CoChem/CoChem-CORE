# cochem_canvas_target: cochem_setup/cochem_setup_phase_1.py
#!/usr/bin/env python3
"""
CoChem-CORE Setup Phase 1: Core System Auditing & Profiling
Executes baseline OS checks, stack size expansion, memory auditing,
and sanitizes ghost dependencies to prevent library collisions.
"""

import os
import sys
import json
import hashlib
import platform
import subprocess
import shutil
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

try:
    import resource
except ImportError:
    resource = None  # Windows fallback, though CoChem natively demands Linux/WSL for engine stability

def setup_airgap_logging() -> Path:
    """Configures the persistent logging subsystem within the strict Artifact Air-Gap."""
    artifact_dir = os.environ.get("COCHEM_ARTIFACT_DIR")
    if not artifact_dir:
        raise RuntimeError("❌ FATAL: COCHEM_ARTIFACT_DIR not set. Must run via Master Orchestrator.")
    
    log_dir = Path(artifact_dir) / "Logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / "cochem_phase1_audit.log"
    
    # Use RotatingFileHandler to prevent log bloat over time
    handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=2)
    formatter = logging.Formatter('%(asctime)s - [%(levelname)s] - %(message)s')
    handler.setFormatter(formatter)
    
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    # Clear existing handlers to prevent duplicate lines if run interactively
    if logger.hasHandlers():
        logger.handlers.clear()
    logger.addHandler(handler)
    
    registry_dir = Path(artifact_dir) / "Registry"
    registry_dir.mkdir(parents=True, exist_ok=True)
    return registry_dir

def purge_ghost_dependencies():
    """Actively wipes legacy library paths to prevent C++ ABI collisions in the micro-silos."""
    purged = []
    for bad_env in ["LD_LIBRARY_PATH", "PYTHONPATH"]:
        if bad_env in os.environ:
            os.environ.pop(bad_env, None)
            purged.append(bad_env)
    
    if purged:
        msg = f"🧹 Purged ghost dependencies ({', '.join(purged)}) to ensure silo sterility."
        print(msg)
        logging.info(msg)
    else:
        logging.info("Environment clean. No ghost dependencies found.")

def tune_system_stack():
    """Expands the OS stack limit to prevent Deep Coupled-Cluster Segfaults."""
    if resource:
        try:
            soft, hard = resource.getrlimit(resource.RLIMIT_STACK)
            resource.setrlimit(resource.RLIMIT_STACK, (hard, hard))
            msg = f"📈 OS Stack Size tuned to maximum limit ({hard}) for heavy Tensor evaluations."
            print(msg)
            logging.info(msg)
        except Exception as e:
            msg = f"⚠️ Warning: Could not tune OS stack limits: {e}"
            print(msg)
            logging.warning(msg)
    else:
        logging.info("OS Stack tuning bypassed (Non-POSIX OS detected).")

def verify_toolchain():
    """Programmatically verifies the presence of essential Linux system build tools."""
    tools = ['gcc', 'g++', 'make', 'git']
    missing = []
    
    for tool in tools:
        if shutil.which(tool) is None:
            missing.append(tool)
            
    if missing:
        msg = f"FATAL: Missing essential build tools required for CoChem Silos: {', '.join(missing)}"
        logging.error(msg)
        raise RuntimeError(f"❌ {msg}\n(Hint: Run 'sudo apt install build-essential git')")
        
    msg = "✅ Essential C++ and system toolchain verified."
    print(msg)
    logging.info(msg)

def inspect_memory_ceiling():
    """Audits virtual memory limits to ensure out-of-core HDF5 streaming will not bottleneck."""
    if platform.system().lower() == "linux":
        map_count_file = Path("/proc/sys/vm/max_map_count")
        if map_count_file.exists():
            try:
                count = int(map_count_file.read_text().strip())
                if count < 65530:
                    msg = f"⚠️ WARNING: vm.max_map_count is low ({count}). Out-of-core HDF5 streams may bottleneck."
                    print(msg)
                    logging.warning(msg)
                else:
                    msg = f"✅ Virtual memory map ceiling optimal ({count})."
                    print(msg)
                    logging.info(msg)
            except Exception as e:
                logging.error(f"Failed to read vm.max_map_count: {e}")

def check_fast_pass(registry_dir: Path) -> dict:
    """Generates a hardware/OS hash and checks if we can skip heavy downstream profiling."""
    sys_str = f"{platform.platform()}_{platform.python_version()}"
    sys_hash = hashlib.sha256(sys_str.encode()).hexdigest()
    
    config_path = registry_dir / "cochem_system_config.json"
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
                if config.get("system_hash") == sys_hash:
                    return {"fast_pass": True, "hash": sys_hash}
        except Exception as e:
            logging.warning(f"Fast-pass cache read failed: {e}")
            
    return {"fast_pass": False, "hash": sys_hash}

def main():
    print("\n=======================================================")
    print(" CoChem Phase 1: Core System Auditing & Profiling ")
    print("=======================================================\n")
    
    try:
        registry_dir = setup_airgap_logging()
        logging.info("Phase 1 Execution Started.")
        
        purge_ghost_dependencies()
        tune_system_stack()
        verify_toolchain()
        inspect_memory_ceiling()
        
        fast_pass_status = check_fast_pass(registry_dir)
        if fast_pass_status["fast_pass"]:
            msg = "⚡ Valid CoChem config detected. Fast-Pass caching enabled."
            print(msg)
            logging.info(msg)
            
        state = {
            "PHASE_1_COMPLETE": True,
            "SYSTEM_HASH": fast_pass_status["hash"],
            "FAST_PASS_ACTIVE": fast_pass_status["fast_pass"],
            "OS_PLATFORM": platform.platform(),
            "PYTHON_VER": platform.python_version()
        }
        
        state_file = registry_dir / "cochem_state_p1.json"
        with open(state_file, "w") as f:
            json.dump(state, f, indent=4)
            
        msg = f"✅ Phase 1 state safely written to Air-Gap: {state_file.name}"
        print(msg)
        logging.info("Phase 1 Execution Completed Successfully.")
        
    except Exception as e:
        print(f"\n❌ Phase 1 Encountered a Fatal Error: {e}")
        # RuntimeError replaces sys.exit(1) to prevent annihilating the Jupyter kernel
        raise RuntimeError(f"Phase 1 aborted: {e}")

if __name__ == "__main__":
    main()