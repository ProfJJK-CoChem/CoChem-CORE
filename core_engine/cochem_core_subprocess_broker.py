#!/usr/bin/env python3
"""
CoChem-CORE: Subprocess Broker & Zombie Reaper (Stage 0.0.5)

The ultimate execution wrapper for ORCA, OpenMPI, and MACE.
Guarantees that no computational engine outlives its parent Python kernel by 
isolating runs into discrete Process Groups and deploying rigorous psutil sweeps.

PATCH APPLIED: Deep Suggestion #10 - Zombie Reaper Escalation
Upgrades simplistic `os.killpg` with recursive `psutil.children()` sweeps to terminate
deeply nested, unresponsive MPI threads.
"""

import os
import signal
import subprocess
import asyncio
import atexit
import logging
from typing import List, Dict, Optional, Any

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("WARNING: psutil not installed. Zombie Reaper capabilities degraded to fallback os.killpg.")

# Configure Module-Level Logging
logger = logging.getLogger("CoChem-Broker")
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - [SubprocessBroker] - %(message)s'))
    logger.addHandler(ch)

class SubprocessBroker:
    """
    Manages isolated, crash-resilient executions of quantum chemistry engines.
    """
    
    # Known high-risk binaries that tend to orphan themselves
    TARGET_ENGINES = {'orca', 'mpirun', 'orted', 'xtb', 'spcat', 'spfit'}

    def __init__(self):
        self.active_pids = set()
        # Arm the global shutdown hook to catch unexpected Python exits
        atexit.register(self._arm_global_reaper)
        
    def _log_telemetry(self, level: str, message: str, meta: Optional[Dict[str, Any]] = None):
        """Standardized internal telemetry stream formatter."""
        if level == "INFO":
            logger.info(f"{message} | Meta: {meta}")
        elif level == "CRITICAL":
            logger.critical(f"{message} | Meta: {meta}")
            
    def _reap_process_tree(self, parent_pid: int):
        """
        Recursively annihilates a process tree. Prevents OpenMPI 'orted' 
        daemons from surviving a parent crash.
        """
        if PSUTIL_AVAILABLE:
            try:
                parent = psutil.Process(parent_pid)
                children = parent.children(recursive=True)
                for child in children:
                    self._log_telemetry("INFO", f"Reaping zombie child process", {"pid": child.pid, "name": child.name()})
                    child.kill()
                parent.kill()
                psutil.wait_procs(children + [parent], timeout=3)
            except psutil.NoSuchProcess:
                pass
            except Exception as e:
                self._log_telemetry("CRITICAL", f"psutil tree reap failed. Falling back to OS signals: {e}")
                self._fallback_killpg(parent_pid)
        else:
            self._fallback_killpg(parent_pid)

    def _fallback_killpg(self, pgid: int):
        """OS-level process group termination when psutil is missing."""
        try:
            os.killpg(os.getpgid(pgid), signal.SIGKILL)
        except OSError:
            pass # Process already dead or invalid PGID

    def _arm_global_reaper(self):
        """Emergency sweep triggered if the Python runtime closes violently."""
        for pid in list(self.active_pids):
            self._reap_process_tree(pid)
            self.active_pids.discard(pid)

    async def execute(self, cmd: List[str], cwd: str = ".", env: Optional[Dict[str, str]] = None, timeout: int = 3600) -> str:
        """
        Asynchronously executes a shell command in a detached session group.
        
        Args:
            cmd: Command array (e.g., ["mpirun", "-np", "4", "orca", "input.inp"])
            cwd: Working directory
            env: OS environment dictionary
            timeout: Max execution time in seconds before SIGKILL
        """
        process = None
        try:
            self._log_telemetry("INFO", f"Dispatching command: {cmd[0]}")
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=cwd,
                env=env or os.environ.copy(),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                start_new_session=True # Critical: Isolates PGID for safe kill sweeps
            )
            self.active_pids.add(process.pid)
            
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
            
            if process.returncode != 0:
                self._log_telemetry("CRITICAL", f"Subprocess failed with exit code {process.returncode}.", {"cmd": cmd[0], "exit_code": process.returncode})
                raise subprocess.CalledProcessError(process.returncode, cmd, output=stdout)
                
            self.active_pids.discard(process.pid)
            return stdout.decode('utf-8') if stdout else ""

        except (KeyboardInterrupt, asyncio.TimeoutError) as e:
            # Annihilate the entire process tree using the psutil tree search.
            if process:
                self._log_telemetry("CRITICAL", f"Execution interrupted ({type(e).__name__}). Eradicating child process group.", {"pid": process.pid})
                self._reap_process_tree(process.pid)
                self.active_pids.discard(process.pid)
            raise

if __name__ == "__main__":
    broker = SubprocessBroker()
    print("Subprocess Broker initialized. Zombie Reaper armed.")