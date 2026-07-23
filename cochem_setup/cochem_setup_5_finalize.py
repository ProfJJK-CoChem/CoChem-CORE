#!/usr/bin/env python3
"""
CoChem Setup Phase 5: Inter-Process Communication (IPC) Config Lock
Merges hardware profiles, engine paths, and silo registries into cochem_system_config.json.
[AUDIT REPAIR]: Fixed fatal SyntaxError in dictionary assignment to ensure clean parsing.
"""

import json
import os

def finalize_config():
    print("[Phase 5] Locking Authoritative Registry (cochem_system_config.json)...")
    
    config = {}
    
    # Safely load physical hardware topology
    if os.path.exists("Processed/hardware_profile.json"):
        with open("Processed/hardware_profile.json", "r") as f:
            config["hardware"] = json.load(f)
            
    # Safely load computational engine paths
    if os.path.exists("Processed/engine_paths.json"):
        with open("Processed/engine_paths.json", "r") as f:
            config["engines"] = json.load(f)
            
    # Safely load Micro-Silo mappings (Repaired Logic)
    if os.path.exists("Processed/silo_registry.json"):
        with open("Processed/silo_registry.json", "r") as f:
            config["silos"] = json.load(f)
    else:
        config["silos"] = {}
        
    # Write to root execution folder
    with open("cochem_system_config.json", "w") as f:
        json.dump(config, f, indent=2)
        
    print("✓ Authoritative Registry Locked successfully.")

if __name__ == "__main__":
    finalize_config()