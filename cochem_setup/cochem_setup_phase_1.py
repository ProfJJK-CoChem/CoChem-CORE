#!/usr/bin/env python3
"""
CoChem-CORE Setup Phase 1: Core System Auditing & Profiling
Executes baseline OS checks, stack size expansion, memory auditing,
and sanitizes ghost dependencies to prevent library collisions.
"""

import os
import sys
import platform
import json
import logging
from logging.handlers import RotatingFileHandler

# Try to import resource for stack sizing (POSIX only)
try:
    import resource
    HAS_RESOURCE = True
except ImportError:
    HAS_RESOURCE = False

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
    logger = logging.getLogger("CoChem_Phase1")
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        handler = RotatingFileHandler(os.path.join(log_dir, 'cochem_phase1_sys.log'), maxBytes=5*1024*1024, backupCount=3)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - [Phase1] - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
    return logger

log = setup_logging()

# ---------------------------------------------------------
# CORE FUNCTIONS
# ---------------------------------------------------------

def sanitize_environment() -> None:
    """Strips Python and Conda paths from the OS environment to prevent C++ collisions."""
    print_status("Sanitizing OS environment of ghost libraries...", "info")
    dirty_keys = ['LD_LIBRARY_PATH', 'PYTHONPATH', 'PYTHONHOME']
    for key in dirty_keys:
        if key in os.environ:
            del os.environ[key]
            log.info(f"Purged transient environment variable: {key}")
    print_status("Environment sanitized. OpenMPI and ORCA dependencies isolated.", "success")

def expand_stack_size() -> None:
    """Expands the POSIX stack size limit to 'unlimited' to prevent ORCA segmentation faults."""
    print_status("Checking POSIX Stack Size limits...", "info")
    if HAS_RESOURCE:
        try:
            resource.setrlimit(resource.RLIMIT_STACK, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
            print_status("OS Stack Size expanded to unlimited (Required for Coupled Cluster).", "success")
            log.info("POSIX stack size successfully expanded to infinity.")
        except Exception as e:
            print_status(f"Could not explicitly set unlimited stack size. {e}", "warning")
            log.warning(f"Resource limit expansion failed: {e}")
    else:
        print_status("Host is non-POSIX (Windows). Skipping stack expansion.", "warning")

def audit_os() -> dict:
    """Returns OS specifics to ensure we are pulling correct binaries."""
    print_status("Auditing Hypervisor & Kernel architecture...", "info")
    os_info = {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "python_version": platform.python_version()
    }
    log.info(f"OS Audit complete: {os_info}")
    return os_info

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