#!/usr/bin/env python3
"""
CoChem-CORE: Central Exception & Telemetry Logger (Stage 0.0.4)

Globally intercepts kernel crashes, OOM faults, and pipeline exceptions.
Formats stack traces into structured JSONL for consumption by the CoChem-ORACLE 
diagnostic LLM, ensuring exact state capture at the exact millisecond of failure.
"""

import os
import sys
import json
import logging
import traceback
import platform
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# Local Module Logger
logger = logging.getLogger("CoChem-Telemetry")
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - [Telemetry] - %(message)s'))
    logger.addHandler(ch)

class TelemetryLogger:
    """
    Singleton-patterned exception interceptor and structured logger.
    Routes critical diagnostic data into Logs/cochem_telemetry_stream.jsonl.
    """
    
    def __init__(self, workspace_root: str = "."):
        self.root = Path(workspace_root).resolve()
        self.logs_dir = self.root / "Logs"
        self.telemetry_file = self.logs_dir / "cochem_telemetry_stream.jsonl"
        
        # Ensure fallback existence if WorkspaceManager hasn't run yet
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Preserve the original excepthook to avoid completely silencing the console
        self._original_excepthook = sys.excepthook

    def _capture_hardware_state(self) -> Dict[str, Any]:
        """Captures instantaneous hardware metrics during a fault."""
        state = {
            "os": platform.system(),
            "python_version": platform.python_version()
        }
        if PSUTIL_AVAILABLE:
            state["cpu_percent"] = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()
            state["ram_used_gb"] = round((mem.total - mem.available) / (1024**3), 2)
            state["ram_total_gb"] = round(mem.total / (1024**3), 2)
            state["ram_percent"] = mem.percent
        return state

    def global_exception_handler(self, exc_type, exc_value, exc_traceback):
        """Intercepts unhandled exceptions, formatting them for ORACLE ingestion."""
        tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        tb_text = "".join(tb_lines)
        
        metadata = {
            "exception_type": exc_type.__name__,
            "traceback": tb_text,
            "hardware_state": self._capture_hardware_state()
        }
        
        self.log_event("CRITICAL", "GlobalExceptionHook", str(exc_value), metadata=metadata)
        
        # Pass through to the default handler to ensure it still prints to the console
        self._original_excepthook(exc_type, exc_value, exc_traceback)

    def log_event(self, level: str, module: str, message: str, metadata: Optional[Dict[str, Any]] = None):
        """Constructs and dispatches the telemetry JSON payload."""
        payload = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": level.upper(),
            "module": module,
            "message": message,
            "metadata": metadata or {}
        }
        self._write_jsonl(payload)
        
    def _write_jsonl(self, payload: Dict[str, Any]):
        """Appends a dictionary as a single JSON line."""
        try:
            with open(self.telemetry_file, 'a') as f:
                f.write(json.dumps(payload) + '\n')
                f.flush()
                os.fsync(f.fileno()) # Force write to prevent buffer loss during OS hard-crash
        except Exception as e:
            # Fallback to standard logging if the file lock fails
            logger.error(f"Failed to write to telemetry stream: {e}")

    def hook_system(self):
        """Activates the global interceptor."""
        sys.excepthook = self.global_exception_handler
        self.log_event("INFO", "TelemetryLogger", "Global exception interceptor activated.")
        logger.info("CoChem Telemetry Logger successfully hooked into sys.excepthook.")

if __name__ == "__main__":
    # Self-test block
    telemetry = TelemetryLogger()
    telemetry.hook_system()
    print("Telemetry hooked. Triggering a safe divide-by-zero test...")
    try:
        1 / 0
    except Exception as e:
        # Manually triggering the hook for the test
        sys.excepthook(type(e), e, e.__traceback__)
    print("Check Logs/cochem_telemetry_stream.jsonl for the output.")