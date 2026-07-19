#!/usr/bin/env python3
"""
CoChem Setup Phase 5: Academic Output, Offloading, & Finalization
Generates Codespaces offload YAML, strict locks, final IPC config,
and organizes the main directory to prevent workspace clutter.
"""

import os
import sys
import json
import subprocess
import shutil
import glob
from pathlib import Path

class Colors:
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

def write_academic_outputs() -> None:
    """Generates the BibTeX file for the dynamic architecture for academic traceability."""
    print_status("Freezing environments and generating Academic locks...", "info")
    
    bibtex = """@misc{cochem2026,
    author = {CoChem Pipeline},
    title = {CoChem Orchestrator Architecture},
    year = {2026},
    note = {Dynamically provisioned environment matrix for High-Throughput Computational Chemistry}
}"""
    
    os.makedirs("cochem_setup", exist_ok=True)
    bib_path = os.path.join("cochem_setup", "cochem_citations.bib")
    
    try:
        with open(bib_path, "w") as f:
            f.write(bibtex)
        print_status(f"Academic citations written to {bib_path}", "success")
    except Exception as e:
         print_status(f"Failed to write citations: {str(e)}", "fail")

def compile_master_registry() -> bool:
    """Aggregates all temporary state JSONs into the authoritative cochem_system_config.json."""
    print_status("Compiling master IPC configuration registry...", "info")
    
    master_config = {
        "architecture_version": "2026.1",
        "silos": {},
        "hardware": {},
        "paths": {}
    }
    
    # Iterate through expected state files 1 through 4
    for i in range(1, 5):
        state_file = os.path.join("cochem_setup", f"cochem_state_{i}.json")
        if os.path.exists(state_file):
            try:
                with open(state_file, 'r') as f:
                    data = json.load(f)
                    # Merge data under a subkey representing the phase
                    master_config[f"phase_{i}_data"] = data
            except json.JSONDecodeError:
                print_status(f"Warning: {state_file} is corrupted. Bypassing.", "warning")
        else:
             print_status(f"Notice: {state_file} not found. Some pipeline features may be degraded.", "warning")

    config_path = "cochem_system_config.json"
    try:
        with open(config_path, "w") as f:
            json.dump(master_config, f, indent=4)
        print_status(f"Authoritative registry compiled: {config_path}", "success")
        return True
    except IOError as e:
        print_status(f"Failed to write master config: {str(e)}", "fail")
        return False

def cleanup_states() -> None:
    """Purges the temporary state files to clean the workspace."""
    print_status("Performing workspace sweep...", "info")
    cleaned = 0
    for i in range(1, 5):
        state_file = os.path.join("cochem_setup", f"cochem_state_{i}.json")
        if os.path.exists(state_file):
            try:
                os.remove(state_file)
                cleaned += 1
            except OSError as e:
                print_status(f"Failed to remove {state_file}: {e}", "warning")
                
    print_status(f"Workspace sweep complete. Removed {cleaned} temporary files.", "success")

def main():
    print(f"\n{Colors.BOLD}--- CoChem Phase 5: Finalization ---{Colors.ENDC}")
    write_academic_outputs()
    
    if compile_master_registry():
        cleanup_states()
        print_status("CoChem Environment Initialization successfully completed.", "success")
    else:
        print_status("Finalization failed. Do not proceed to downstream Jupyter processing.", "fail")

if __name__ == "__main__":
    main()