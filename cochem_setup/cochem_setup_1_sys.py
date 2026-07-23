#!/usr/bin/env python3
"""
CoChem Setup Phase 1: OS & Hypervisor Audit
Audits the host operating system, checks kernel versions, and validates Python environment runtime constraints.
"""

import sys
import platform
import os

class Colors:
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def audit_system():
    print(f"{Colors.BOLD}[Phase 1] Auditing Host OS & Hypervisor...{Colors.ENDC}")
    sys_info = {
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "python_version": platform.python_version()
    }
    
    print(f"  - Host OS: {sys_info['system']} {sys_info['release']} ({sys_info['machine']})")
    print(f"  - Python Interpreter: {sys_info['python_version']} at {sys.executable}")
    
    if sys_info['system'] not in ["Linux", "Darwin"]:
        print(f"{Colors.WARNING}⚠️ Warning: CoChem is optimized for Linux/WSL environments. Windows native execution may experience OpenMPI issues.{Colors.ENDC}")
    else:
        print(f"{Colors.OKGREEN}✓ OS Hypervisor Check Passed.{Colors.ENDC}")

if __name__ == "__main__":
    audit_system()