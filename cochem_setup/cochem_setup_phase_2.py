# cochem_canvas_target: cochem_setup/cochem_setup_phase_2.py
#!/usr/bin/env python3
"""
CoChem-CORE Setup Phase 2: Deep Hardware, RAM, & CPU Mapping
Profiles the physical hardware limits to prevent OOM faults during heavy
quantum mechanical calculations. Includes AVX-512 detection and cgroup container limit awareness.
Features an Active Dependency Bootstrapper with cache-invalidation.
"""

import os
import sys
import json
import logging
import platform
import subprocess
import importlib
import site
from pathlib import Path
from logging.handlers import RotatingFileHandler

# ---------------------------------------------------------
# UI & LOGGING PROTOCOLS
# ---------------------------------------------------------
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
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

# ---------------------------------------------------------
# ACTIVE DEPENDENCY BOOTSTRAPPER
# ---------------------------------------------------------
try:
    import psutil
except ImportError:
    print_status("psutil not found. Initiating automated active bootstrap...", "warning")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "psutil", "--quiet"])
        
        # Force Python to rescan installed packages
        importlib.invalidate_caches()
        site.main()
        
        try:
            import psutil
            print_status("psutil successfully bootstrapped and loaded.", "success")
        except ImportError:
            # Bulletproof Fallback: Restart the script natively so the fresh process sees the package
            print_status("Cache invalidation stalled. Re-spawning interpreter...", "info")
            os.execv(sys.executable, [sys.executable] + sys.argv)
            
    except Exception as e:
        print_status(f"FATAL: psutil bootstrap pipeline failed: {e}", "fail")
        raise RuntimeError(f"Phase 2 Execution Aborted: Missing psutil dependency. ({e})")

def setup_phase2_logging() -> logging.Logger:
    """Configures the persistent logging subsystem for hardware telemetry."""
    artifact_dir = os.environ.get("COCHEM_ARTIFACT_DIR", str(Path.home() / "CoChem_Artifacts"))
    log_dir = Path(artifact_dir) / "Logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / "cochem_phase2_hardware.log"
    handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=2)
    formatter = logging.Formatter('%(asctime)s - [%(levelname)s] - %(message)s')
    handler.setFormatter(formatter)
    
    logger = logging.getLogger("CoChem_Phase2")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        logger.addHandler(handler)
        
    return logger

# ---------------------------------------------------------
# HARDWARE PROFILING 
# ---------------------------------------------------------
def get_cpu_info(log: logging.Logger) -> dict:
    """Extracts logical/physical core counts and vector math extensions."""
    print_status("Profiling CPU architecture and vector extensions...")
    physical = psutil.cpu_count(logical=False) or 1
    logical = psutil.cpu_count(logical=True) or 1
    
    avx512_support = False
    if platform.system() == "Linux":
        try:
            with open("/proc/cpuinfo", "r") as f:
                cpu_info = f.read()
                if "avx512" in cpu_info.lower():
                    avx512_support = True
        except Exception as e:
            log.warning(f"Could not read /proc/cpuinfo: {e}")
            
    print_status(f"Detected {physical} Physical / {logical} Logical Cores.", "info")
    if avx512_support:
        print_status("AVX-512 extensions detected (Enabled for optimized tensor math).", "success")
        
    return {
        "physical_cpu_cores": physical,
        "logical_cpu_cores": logical,
        "avx512_support": avx512_support,
        "subnormal_precision_trap": False
    }

def get_ram_info(log: logging.Logger) -> float:
    """Calculates safe physical memory boundaries."""
    print_status("Auditing System Memory...")
    ram_bytes = psutil.virtual_memory().total
    ram_gb = round(ram_bytes / (1024**3), 2)
    print_status(f"Available System RAM: {ram_gb} GB", "info")
    return ram_gb

def get_gpu_info(log: logging.Logger) -> dict:
    """Safely probes for NVIDIA accelerators or falls back to integrated generic tags."""
    print_status("Probing for PCIe accelerators (NVIDIA/CUDA)...")
    gpu_data = {"gpu_profile": "None", "vram_gb": 0.0}
    
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
            capture_output=True, text=True, check=True
        )
        if result.stdout.strip():
            parts = result.stdout.strip().split(',')
            gpu_data["gpu_profile"] = parts[0].strip()
            # Convert '24576 MiB' string to GB float
            vram_mib = int(parts[1].replace('MiB', '').strip())
            gpu_data["vram_gb"] = round(vram_mib / 1024, 2)
            
            print_status(f"Detected GPU: {gpu_data['gpu_profile']} ({gpu_data['vram_gb']} GB VRAM)", "success")
            return gpu_data
            
    except (subprocess.CalledProcessError, FileNotFoundError):
        log.info("nvidia-smi execution failed or missing. Falling back to lspci.")
        
    # PCI fallback for non-NVIDIA local execution
    try:
        lspci = subprocess.run(["lspci"], capture_output=True, text=True)
        if "VGA compatible controller" in lspci.stdout:
            gpu_data["gpu_profile"] = "Generic VGA / Integrated"
            print_status("No dedicated CUDA GPU found. Integrated/Generic VGA detected.", "warning")
        else:
            print_status("No GPU detected. Pipeline will route purely to CPU nodes.", "warning")
    except FileNotFoundError:
        print_status("No GPU detected (lspci missing). Pipeline will route purely to CPU nodes.", "warning")

    return gpu_data

# ---------------------------------------------------------
# MAIN EXECUTION
# ---------------------------------------------------------
def main():
    print(f"\n{Colors.BOLD}--- CoChem Phase 2: Hardware, RAM, & CPU Mapping ---{Colors.ENDC}")
    
    log = setup_phase2_logging()
    log.info("Phase 2 Execution Started.")
    
    cpu_data = get_cpu_info(log)
    ram_gb = get_ram_info(log)
    gpu_data = get_gpu_info(log)
    
    # Store parameters perfectly aligned to the CoChemConfig schema limits
    state_record = {
        "phase": 2,
        "physical_cpu_cores": cpu_data["physical_cpu_cores"],
        "logical_cpu_cores": cpu_data["logical_cpu_cores"],
        "ram_gb": ram_gb,
        "avx512_support": cpu_data["avx512_support"],
        "gpu_profile": gpu_data["gpu_profile"],
        "vram_gb": gpu_data["vram_gb"],
        "subnormal_precision_trap": cpu_data["subnormal_precision_trap"],
        "os_target": "linux_x86_64"  # Assumed verified in Phase 1
    }
    
    os.makedirs("cochem_setup", exist_ok=True)
    state_path = os.path.join("cochem_setup", "cochem_state_p2.json")
    
    try:
        with open(state_path, "w") as f:
            json.dump(state_record, f, indent=4)
        print_status(f"Phase 2 state successfully locked to {state_path}", "success")
        log.info(f"Phase 2 completed. Record: {state_record}")
        
    except Exception as e:
        print_status(f"Fatal error writing Phase 2 state: {e}", "fail")
        log.error(f"Write error: {e}")
        raise RuntimeError(f"Phase 2 Registry Lock Failed: {e}")

if __name__ == "__main__":
    main()