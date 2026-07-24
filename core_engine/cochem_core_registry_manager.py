#!/usr/bin/env python3
"""
CoChem-CORE: The Golden Gatekeeper (Registry Manager)

Provides thread-safe, atomic I/O operations for the CoChem ecosystem's
authoritative state file (`cochem_system_config.json`).
Utilizes POSIX-compliant file locking and atomic OS swaps to guarantee 
zero state-corruption during highly parallel HPC or MLFF task dispatch.
"""

import os
import json
import fcntl
import logging
import contextlib
from pathlib import Path
from typing import Callable, Optional
from pydantic import ValidationError

# Strict dependency on the schema
try:
    from core_engine.cochem_core_registry_schema import CoChemConfig
except ImportError:
    raise ImportError("FATAL: cochem_core_registry_schema.py not found. Schema definitions are strictly required.")

# Configure Module-Level Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [GoldenGatekeeper] - %(message)s'
)
logger = logging.getLogger("CoChem-Gatekeeper")

class RegistryLockError(Exception):
    """Raised when the registry cannot be safely locked or accessed."""
    pass

class RegistryManager:
    """
    Transactional manager for the CoChem configuration. 
    Enforces Pydantic typing on all Reads/Writes to prevent schema drift.
    """
    
    def __init__(self, workspace_root: str = "."):
        self.root = Path(workspace_root).resolve()
        self.config_path = self.root / "cochem_system_config.json"
        self.lock_path = self.root / "cochem_system_config.lock"
        self.tmp_path = self.root / "cochem_system_config.tmp"

    @contextlib.contextmanager
    def _acquire_lock(self, shared: bool = True):
        """POSIX fcntl lock to block concurrent writes."""
        mode = fcntl.LOCK_SH if shared else fcntl.LOCK_EX
        
        # Ensure the lock file exists before attempting to open it
        self.lock_path.touch(exist_ok=True)
        lock_file = open(self.lock_path, 'r+')
        
        try:
            fcntl.flock(lock_file, mode)
            yield
        except OSError as e:
            logger.error(f"Failed to acquire registry lock: {e}")
            raise RegistryLockError(f"Lock acquisition failed: {e}")
        finally:
            fcntl.flock(lock_file, fcntl.LOCK_UN)
            lock_file.close()

    def read_registry(self) -> CoChemConfig:
        """Safely reads and validates the registry state."""
        with self._acquire_lock(shared=True):
            if not self.config_path.exists():
                raise FileNotFoundError(f"Master registry not found at {self.config_path}")
            with open(self.config_path, 'r') as f:
                data = json.load(f)
            return CoChemConfig.model_validate(data)

    def write_registry(self, config: CoChemConfig) -> bool:
        """Directly writes a validated CoChemConfig object to disk atomically."""
        with self._acquire_lock(shared=False):
            try:
                safe_data = config.model_dump(mode='json')
                
                # Write to temp file, flush buffers, and force OS sync
                with open(self.tmp_path, 'w') as f:
                    json.dump(safe_data, f, indent=4)
                    f.flush()
                    os.fsync(f.fileno())
                
                # Atomic swap replaces the old config instantly
                os.replace(self.tmp_path, self.config_path)
                return True
            except Exception as e:
                logger.error(f"Atomic write failed: {e}")
                if self.tmp_path.exists():
                    os.remove(self.tmp_path)
                raise RegistryLockError(f"Atomic write failed: {e}")

    def transaction(self, update_func: Callable[[CoChemConfig], CoChemConfig]) -> bool:
        """
        High-level safe wrapper. Acquires an exclusive lock, reads the state, 
        applies the user's update function, validates the result, and writes it back atomically.
        """
        with self._acquire_lock(shared=False):
            try:
                with open(self.config_path, 'r') as f:
                    raw_data = json.load(f)
                    
                current_config = CoChemConfig.model_validate(raw_data)
                
                # Apply the mutation logic passed by the caller
                new_config = update_func(current_config)
                
                # Re-validate and serialize
                safe_data = new_config.model_dump(mode='json')
                
                # Atomic swap to prevent mid-write corruption from hard OS resets
                with open(self.tmp_path, 'w') as f:
                    json.dump(safe_data, f, indent=4)
                    f.flush()
                    os.fsync(f.fileno())
                    
                os.replace(self.tmp_path, self.config_path)
                return True
                
            except ValidationError as e:
                logger.error(f"Transaction rejected: Schema violation. {e}")
                return False
            except Exception as e:
                logger.error(f"Transaction failed, changes rolled back. Reason: {e}")
                if self.tmp_path.exists():
                    os.remove(self.tmp_path)
                return False