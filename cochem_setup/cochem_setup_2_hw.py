#!/usr/bin/env python3
"""
CoChem Setup Phase 2: Hardware, RAM, & CPU Mapping
Profiles the physical hardware limits to prevent OOM faults during heavy
quantum mechanical calculations. Outputs to cochem_state_2.json.
"""
import os
import sys
import subprocess
import json
import logging
from logging.handlers import RotatingFileHandler
import psutil

class Colors:
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

os.makedirs("cochem_setup", exist_ok=True)
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler = RotatingFileHandler('cochem_setup/cochem_phase2_hw.log', maxBytes=1000000, backupCount=3)
file_handler.setFormatter(log_formatter)

logger = logging.getLogger('Phase2_HW')
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)

def print_status(msg: str, status: str = "info") -> None:
    if status == "success":
        print(f" {Colors.OKGREEN}✅ {msg}{Colors.ENDC}")
    elif status == "warning":
        print(f" {Colors.WARNING}⚠️ {msg}{Colors.ENDC}")
    elif status == "fail":
        print(f" {Colors.FAIL}❌ {msg}{Colors.ENDC}")
    else:
        print(f" {Colors.OKCYAN}➡️ {msg}{Colors.ENDC}")

def get_physical_ram() -> dict:
    """Uses POSIX sysconf for absolute physical RAM to bypass VM lies."""
    try:
        pages = os.sysconf('SC_PHYS_PAGES')
        page_size = os.sysconf('SC_PAGE_SIZE')
        total_bytes = pages * page_size
        gb = total_bytes / (1024 ** 3)
        return {"bytes": total_bytes, "gb": round(gb, 2)}
    except ValueError:
        # Fallback to psutil if sysconf fails
        total_bytes = psutil.virtual_memory().total
        return {"bytes": total_bytes, "gb": round(total_bytes / (1024 ** 3), 2)}

def get_gpu_info() -> str:
    """Uses lspci to find bare-metal GPUs (Intel/AMD/Nvidia)."""
    try:
        result = subprocess.run(["lspci"], capture_output=True, text=True, check=True)
        gpus = [line for line in result.stdout.split('\n') if 'VGA' in line or '3D controller' in line]
        if gpus:
            return gpus[0].strip()
        return "None Detected"
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "lspci unavailable - GPU unknown"

def main():
    print(f"\n{Colors.BOLD}--- CoChem Phase 2: Hardware Profiling ---{Colors.ENDC}")
    
    cpu_cores = os.cpu_count() or 1
    ram_info = get_physical_ram()
    gpu_info = get_gpu_info()
    
    print_status(f"CPU Cores detected: {cpu_cores}", "success")
    print_status(f"Physical RAM detected: {ram_info['gb']} GB", "success")
    print_status(f"GPU Profile: {gpu_info}", "success" if gpu_info != "None Detected" else "warning")
    
    logger.info(f"Hardware Profile - CPU: {cpu_cores}, RAM: {ram_info['gb']}GB, GPU: {gpu_info}")
    
    # Store parameters for downstream Phase 5 aggregation
    state_record = {
        "phase": 2,
        "cpu_cores": cpu_cores,
        "ram_gb": ram_info['gb'],
        "gpu_profile": gpu_info
    }
    
    state_path = os.path.join("cochem_setup", "cochem_state_2.json")
    with open(state_path, "w") as f:
        json.dump(state_record, f, indent=4)
        
    print_status(f"Phase 2 Complete. Hardware map saved to {state_path}.", "success")
    
    # Remove dangling handler to free memory
    logger.removeHandler(file_handler)
    file_handler.close()

if __name__ == "__main__":
    main()