#!/usr/bin/env python3
"""
CoChem Setup Phase 3: ORCA, OpenMPI, & xTB Binary Verification
Scans the local environment for quantum chemical executables and MPI wrappers.
"""

import shutil
import json
import os

def verify_engines():
    print("[Phase 3] Verifying Quantum Engines (ORCA, OpenMPI, xTB)...")
    
    orca_path = shutil.which("orca")
    mpirun_path = shutil.which("mpirun")
    xtb_path = shutil.which("xtb")
    
    engines = {
        "orca": orca_path or "Not Found in PATH",
        "mpirun": mpirun_path or "Not Found in PATH",
        "xtb": xtb_path or "Not Found in PATH"
    }
    
    for k, v in engines.items():
        print(f"  - {k.upper()}: {v}")
        
    os.makedirs("Processed", exist_ok=True)
    with open("Processed/engine_paths.json", "w") as f:
        json.dump(engines, f, indent=2)
    print("✓ Engine Verification Complete.")

if __name__ == "__main__":
    verify_engines()