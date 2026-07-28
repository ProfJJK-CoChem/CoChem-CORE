#!/usr/bin/env python3
"""
CoChem-CORE Setup Phase 2: Deep Hardware, RAM, & CPU Mapping
Profiles the physical hardware limits to prevent OOM faults during heavy
quantum mechanical calculations. Includes AVX-512 detection and cgroup container limit awareness.
"""

import os
import sys
import json
import logging
import subprocess
from logging.handlers import RotatingFileHandler

# Strict Dependency Gate
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("FATAL: psutil not found. Phase 2 requires psutil for deep memory profiling.")
    sys.exit(1)

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

def setup_logging() -> logging.Logger:
    """Initializes the diagnostic rotating logger."""
    log_dir = "Logs"
    os.makedirs(log_dir, exist_ok=True)
    logger = logging.getLogger("CoChem_Phase2")
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        handler = RotatingFileHandler(os.path.join(log_dir, 'cochem_phase2_hw.log'), maxBytes=5*1024*1024, backupCount=3)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - [Phase2] - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
    return logger

log = setup_logging()

# ---------------------------------------------------------
# HARDWARE PROFILING FUNCTIONS
# ---------------------------------------------------------

def get_cpu_info() -> dict:
    """Determines physical vs logical cores and AVX-512 support for math libraries."""
    print_status("Profiling CPU architecture...", "info")
    logical_cores = psutil.cpu_count(logical=True)
    physical_cores = psutil.cpu_count(logical=False)
    
    # AVX-512 check (Linux specific via /proc/cpuinfo)
    avx512 = False
    subnormal_trap = False
    try:
        with open('/proc/cpuinfo', 'r') as f:
            cpuinfo = f.read()
            if 'avx512' in cpuinfo:
                avx512 = True
            if 'flush_to_zero' in cpuinfo or 'denormals_are_zero' in cpuinfo:
                subnormal_trap = True
    except FileNotFoundError:
        pass # Not on Linux
        
    cpu_data = {
        "logical_cpu_cores": logical_cores or 2,
        "physical_cpu_cores": physical_cores or 1,
        "avx512_support": avx512,
        "subnormal_precision_trap": subnormal_trap
    }
    
    print_status(f"CPU Profile: {physical_cores} Physical Cores, AVX-512: {avx512}", "success")
    log.info(f"CPU Profile Matrix: {cpu_data}")
    return cpu_data

def get_ram_info() -> float:
    """Retrieves total system RAM, respecting cgroup container limits in Docker/Codespaces."""
    print_status("Profiling RAM & memory limits...", "info")
    total_ram_gb = psutil.virtual_memory().total / (1024**3)
    
    # Check for Docker/Cgroup hard limits which override physical RAM
    cgroup_mem_limit_file = "/sys/fs/cgroup/memory/memory.limit_in_bytes"
    if os.path.exists(cgroup_mem_limit_file):
        try:
            with open(cgroup_mem_limit_file, 'r') as f:
                cgroup_limit = int(f.read().strip())
                # Ignore if limit is set to effectively infinity (e.g. 9223372036854771712)
                if cgroup_limit < psutil.virtual_memory().total:
                     total_ram_gb = cgroup_limit / (1024**3)
                     print_status("Detected Docker/cgroup memory constraint.", "warning")
        except ValueError:
            pass

    print_status(f"Calculated usable RAM baseline: {total_ram_gb:.1f} GB", "success")
    return round(total_ram_gb, 1)

def get_gpu_info() -> dict:
    """Probes for NVIDIA GPUs using nvidia-smi."""
    print_status("Probing for NVIDIA CUDA architecture...", "info")
    gpu_data = {"gpu_profile": "None", "vram_gb": 0.0}
    try:
        result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total', '--format=csv,noheader'], 
                                capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split('\n')
        if lines and lines[0]:
            parts = lines[0].split(',')
            name = parts[0].strip()
            # Extract memory (e.g., "24256 MiB")
            vram_str = parts[1].replace('MiB', '').strip()
            vram_gb = float(vram_str) / 1024.0
            
            gpu_data["gpu_profile"] = name
            gpu_data["vram_gb"] = round(vram_gb, 1)
            print_status(f"Found GPU: {name} with {vram_gb:.1f} GB VRAM", "success")
            log.info(f"GPU Profile: {gpu_data}")
            return gpu_data
    except (subprocess.CalledProcessError, FileNotFoundError):
        print_status("No NVIDIA GPU detected or nvidia-smi failed. Defaulting CPU-Only execution modes.", "warning")
        return gpu_data

# ---------------------------------------------------------
# MAIN EXECUTION
# ---------------------------------------------------------
def main():
    print(f"\n{Colors.BOLD}--- CoChem Phase 2: Hardware, RAM, & CPU Mapping ---{Colors.ENDC}")
    
    cpu_data = get_cpu_info()
    ram_gb = get_ram_info()
    gpu_data = get_gpu_info()
    
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
        "os_target": "linux_x86_64" # Assumed verified in Phase 1
    }
    
    os.makedirs("cochem_setup", exist_ok=True)
    state_path = os.path.join("cochem_setup", "cochem_state_p2.json")
    
    try:
        with open(state_path, "w") as f:
            json.dump(state_record, f, indent=4)
        print_status(f"Phase 2 state successfully locked to {state_path}", "success")
        log.info("Phase 2 execution completed and state saved.")
    except IOError as e:
        print_status(f"Failed to write state file: {e}", "fail")
        log.error(f"IOError during state save: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()