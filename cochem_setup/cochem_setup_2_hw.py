#!/usr/bin/env python3
"""
CoChem Setup Phase 2: Hardware, RAM, & CPU Topology Mapping
Profiles available physical cores, thread limits, and system RAM availability.
"""

import os
import psutil
import json

def map_hardware():
    print("[Phase 2] Mapping Hardware Topology & RAM Constraints...")
    cpu_count_physical = psutil.cpu_count(logical=False)
    cpu_count_logical = psutil.cpu_count(logical=True)
    mem = psutil.virtual_memory()
    
    hw_data = {
        "physical_cores": cpu_count_physical or 4,
        "logical_threads": cpu_count_logical or 8,
        "total_ram_gb": round(mem.total / (1024**3), 2),
        "available_ram_gb": round(mem.available / (1024**3), 2)
    }
    
    print(f"  - Physical Cores: {hw_data['physical_cores']}")
    print(f"  - Logical Threads: {hw_data['logical_threads']}")
    print(f"  - Total System RAM: {hw_data['total_ram_gb']} GB")
    
    os.makedirs("Processed", exist_ok=True)
    with open("Processed/hardware_profile.json", "w") as f:
        json.dump(hw_data, f, indent=2)
    print("✓ Hardware Profile Mapped and Cached.")

if __name__ == "__main__":
    map_hardware()