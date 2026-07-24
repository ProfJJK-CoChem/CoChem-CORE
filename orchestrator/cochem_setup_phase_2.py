#!/usr/bin/env python3
"""
CoChem Setup Phase 2: Deep Hardware, RAM, & CPU Mapping

Profiles the physical hardware limits to prevent OOM faults during heavy
quantum mechanical calculations. Includes AVX-512 detection and cgroup 
container limit awareness for GitHub Codespaces and Docker DevContainers.
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
    log_file = os.path.join(log_dir, "cochem_phase2_hw.log")
    
    handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=3)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    
    log = logging.getLogger("CoChem_Phase2")
    log.setLevel(logging.DEBUG)
    if not log.handlers:
        log.addHandler(handler)
    return log

log = setup_logging()

# ---------------------------------------------------------
# HARDWARE PROFILING PROTOCOLS
# ---------------------------------------------------------
def get_cpu_info() -> dict:
    """Isolates physical vs logical cores to prevent thread contention."""
    print_status("Profiling CPU Architecture...", "info")
    physical = psutil.cpu_count(logical=False) or 1
    logical = psutil.cpu_count(logical=True) or 1
    
    avx512_support = False
    subnormal_trap = False
    try:
        with open('/proc/cpuinfo', 'r') as f:
            cpu_flags = f.read().lower()
            if 'avx512' in cpu_flags:
                avx512_support = True
            # Basic subnormal heuristic: older architectures handle them poorly via microcode
            if 'pentium' in cpu_flags or 'atom' in cpu_flags:
                subnormal_trap = True
    except FileNotFoundError:
        log.warning("/proc/cpuinfo not found (macOS/Windows?). AVX-512 checks bypassed.")
        
    print_status(f"CPU Cores: {physical} Physical, {logical} Logical (AVX-512: {avx512_support})", "success")
    log.info(f"CPU Profile: Physical={physical}, Logical={logical}, AVX512={avx512_support}")
    
    return {
        "physical_cpu_cores": physical,
        "logical_cpu_cores": logical,
        "avx512_support": avx512_support,
        "subnormal_precision_trap": subnormal_trap
    }

def get_ram_info() -> float:
    """Reads true RAM, respecting Docker/Codespace CGroup limits if active."""
    print_status("Profiling Memory Limits (cgroup aware)...", "info")
    host_ram_gb = psutil.virtual_memory().total / (1024**3)
    cgroup_limit_gb = float('inf')
    
    try:
        # Check cgroup v2 limit
        if os.path.exists('/sys/fs/cgroup/memory.max'):
            with open('/sys/fs/cgroup/memory.max', 'r') as f:
                val = f.read().strip()
                if val != 'max': 
                    cgroup_limit_gb = int(val) / (1024**3)
        # Check cgroup v1 limit
        elif os.path.exists('/sys/fs/cgroup/memory/memory.limit_in_bytes'):
            with open('/sys/fs/cgroup/memory/memory.limit_in_bytes', 'r') as f:
                val = f.read().strip()
                if val and int(val) < 9000000000000000000:  # Ignore 'unlimited' integers
                    cgroup_limit_gb = int(val) / (1024**3)
    except Exception as e:
        log.warning(f"Failed to read cgroup limits: {e}")
        
    effective_ram_gb = min(host_ram_gb, cgroup_limit_gb)
    print_status(f"Effective RAM: {effective_ram_gb:.2f} GB (Host: {host_ram_gb:.2f} GB)", "success")
    log.info(f"Memory Profile: Host={host_ram_gb:.2f}GB, CGroup={cgroup_limit_gb}, Effective={effective_ram_gb:.2f}GB")
    
    return round(effective_ram_gb, 2)

def get_gpu_info() -> dict:
    """Safely cascades through nvidia-smi to lspci for hardware detection."""
    print_status("Probing for GPU accelerators (NVIDIA/AMD)...", "info")
    gpu_data = {"gpu_profile": "None", "vram_gb": 0.0}
    
    # Primary: Execute nvidia-smi
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, check=True
        )
        gpu_info = result.stdout.strip()
        if gpu_info:
            parts = gpu_info.split(',')
            gpu_data["gpu_profile"] = parts[0].strip()
            if len(parts) > 1:
                vram_mb = int(parts[1].replace('MiB', '').strip())
                gpu_data["vram_gb"] = round(vram_mb / 1024.0, 2)
            print_status(f"GPU Detected: {gpu_data['gpu_profile']} ({gpu_data['vram_gb']} GB VRAM)", "success")
            log.info(f"NVIDIA GPU Profiled: {gpu_data}")
            return gpu_data
    except (subprocess.CalledProcessError, FileNotFoundError):
        log.debug("nvidia-smi unavailable or failed. Initiating lspci fallback.")

    # Fallback: lspci text parsing
    try:
        result = subprocess.run(["lspci"], capture_output=True, text=True, check=True)
        gpus = [line for line in result.stdout.split('\n') if 'VGA' in line or '3D controller' in line]
        if gpus:
            gpu_data["gpu_profile"] = gpus[0].split(':')[-1].strip()
            print_status(f"VGA/3D Controller found via lspci: {gpu_data['gpu_profile']}", "warning")
            log.info(f"lspci GPU Profiled: {gpu_data}")
            return gpu_data
    except (subprocess.CalledProcessError, FileNotFoundError):
        log.debug("lspci unavailable or failed.")

    print_status("No discrete GPU detected. Routing to CPU-only execution paths.", "warning")
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