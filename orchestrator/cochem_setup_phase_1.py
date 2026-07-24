#!/usr/bin/env python3
"""
CoChem Setup Phase 1: Core System Auditing & Profiling
Executes baseline OS checks, stack size expansion, memory auditing,
and sanitizes ghost dependencies to prevent library collisions.
"""
import os
import sys
import platform
import json
import logging
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

def setup_logging() -> logging.Logger:
    """Initializes the diagnostic rotating logger."""
    log_dir = "Logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "cochem_setup.log")
    
    handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=3)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    
    log = logging.getLogger("CoChem_Phase1")
    log.setLevel(logging.DEBUG)
    if not log.handlers:
        log.addHandler(handler)
    return log

log = setup_logging()

# ---------------------------------------------------------
# SYSTEM AUDIT PROTOCOLS
# ---------------------------------------------------------
def sanitize_environment() -> None:
    """
    Scrub environment variables that break OpenMPI or Conda isolation.
    Uses atomic pop to prevent KeyError if modified asynchronously.
    """
    print_status("Sanitizing ghost dependencies ($LD_LIBRARY_PATH, $PYTHONPATH)...", "info")
    for var in ['LD_LIBRARY_PATH', 'PYTHONPATH']:
        old_val = os.environ.pop(var, None)
        if old_val is not None:
            log.warning(f"Sanitized environment variable {var} (was: {old_val})")

def audit_os() -> dict:
    """Audits OS specifications to ensure Linux/Mint compatibility."""
    print_status("Auditing Operating System specifications...", "info")
    os_info = {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine()
    }
    
    if os_info["system"].lower() != "linux":
        print_status(f"Non-Linux OS detected ({os_info['system']}). CoChem strictly targets Linux Mint/Ubuntu.", "warning")
        log.warning(f"OS mismatch: {os_info}")
    else:
        print_status("Linux OS verified.", "success")
        log.info(f"OS verification passed: {os_info}")
        
    return os_info

def expand_stack_size() -> None:
    """
    Expands the OS stack limit. Prevents ORCA Coupled-Cluster (CCSD) 
    routines from throwing hard segfaults on massive density matrices.
    """
    try:
        import resource
        soft, hard = resource.getrlimit(resource.RLIMIT_STACK)
        # Attempt to set soft limit to hard limit, or 8MB if infinity isn't allowed
        if hard == resource.RLIM_INFINITY or hard > 8192000:
            new_soft = hard if hard != resource.RLIM_INFINITY else 8192000
            resource.setrlimit(resource.RLIMIT_STACK, (new_soft, hard))
            print_status("Stack size expanded for massive Coupled-Cluster calculations.", "success")
            log.info(f"Stack size expanded. Soft limit updated.")
    except Exception as e:
        print_status("Could not expand stack size automatically. Non-POSIX OS?", "warning")
        log.warning(f"Stack expansion failed: {e}")

# ---------------------------------------------------------
# MAIN EXECUTION
# ---------------------------------------------------------
def main():
    print(f"\n{Colors.BOLD}--- CoChem Phase 1: System Audit ---{Colors.ENDC}")
    
    sanitize_environment()
    expand_stack_size()
    os_metadata = audit_os()
    
    # Store parameters for downstream Phase 5 aggregation
    state_record = {
        "phase": 1,
        "os_info": os_metadata,
        "python_executable": sys.executable,
        "python_version": platform.python_version()
    }
    
    os.makedirs("cochem_setup", exist_ok=True)
    state_path = os.path.join("cochem_setup", "cochem_state_p1.json")
    
    try:
        with open(state_path, "w") as f:
            json.dump(state_record, f, indent=4)
        print_status(f"Phase 1 state successfully locked to {state_path}", "success")
        log.info("Phase 1 execution completed and state saved.")
    except IOError as e:
        print_status(f"Failed to write state file: {e}", "fail")
        log.error(f"IOError during state save: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()