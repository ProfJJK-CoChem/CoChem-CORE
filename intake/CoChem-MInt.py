#!/usr/bin/env python3
"""
CoChem-CORE: Stage 1.x - Consolidated Molecular Intake Backend
Module: intake/CoChem-MInt.py
Purpose: Jupyter-native unified GUI for directory scanning, structural 
         canonicalization, and real-time watchdog monitoring of the Input_Files directory.
         Includes the patched _find_path() recursive registry hunter.
"""

import os
import sys
import json
import time
import threading
import logging
from pathlib import Path
import ipywidgets as widgets
from IPython.display import display, clear_output

# Strict Dependency Gate
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    HAS_WATCHDOG = True
except ImportError:
    HAS_WATCHDOG = False

# =====================================================================
# TELEMETRY & LOGGING
# =====================================================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("CoChem-MInt")

def print_status(msg: str, status: str = "info") -> None:
    """Jupyter-safe HTML status printer."""
    colors = {"success": "green", "warning": "orange", "fail": "red", "info": "blue"}
    color = colors.get(status, "black")
    display(widgets.HTML(f"<span style='color:{color}; font-weight:bold;'>[{status.upper()}]</span> {msg}"))

# =====================================================================
# WATCHDOG EVENT HANDLER
# =====================================================================
class IngestionWatchdog(FileSystemEventHandler):
    """Monitors the Artifacts/Input_Files directory for new .xyz submissions."""
    
    def __init__(self, ui_callback):
        super().__init__()
        self.ui_callback = ui_callback

    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('.xyz'):
            logger.info(f"Watchdog detected new geometry: {event.src_path}")
            self.ui_callback(f"Detected: {Path(event.src_path).name}")

# =====================================================================
# UNIFIED MINT GUI CLASS
# =====================================================================
class CoChemMIntUI:
    def __init__(self):
        if not HAS_WATCHDOG:
            print_status("CRITICAL: 'watchdog' library missing from main environment. Cannot build data bridge.", "fail")
            # We don't exit so the UI can still render in degraded mode
            
        self.artifact_dir = self._find_path()
        self.input_dir = self.artifact_dir / "Input_Files"
        self.input_dir.mkdir(parents=True, exist_ok=True)
        
        self.observer = None
        self._build_ui()

    def _find_path(self) -> Path:
        """Recursive hunter to locate the authoritative CoChem_Artifacts directory."""
        # 1. Check local environment first
        local_target = Path.home() / "CoChem_Artifacts"
        if local_target.exists() and (local_target / "cochem_system_config.json").exists():
            return local_target
            
        # 2. Check explicitly mounted DevContainer volumes
        dev_target = Path("/workspaces/CoChem_Artifacts")
        if dev_target.exists():
            return dev_target
            
        # Fallback to current working directory if registry is totally lost
        logger.warning("Could not find global CoChem_Artifacts tier. Falling back to local workspace.")
        return Path.cwd()

    def _build_ui(self):
        """Constructs the Jupyter VBox interface."""
        self.out = widgets.Output(layout={'border': '1px solid #ccc', 'padding': '10px', 'height': '200px', 'overflow_y': 'auto'})
        
        self.title = widgets.HTML("<h2>🧪 CoChem-MInt: Molecular Intake & Canonicalization</h2>")
        
        self.btn_scan = widgets.Button(description="Scan Folder & Canonicalize", button_style="primary", icon="search")
        self.btn_build = widgets.Button(description="Build Molecule", button_style="info", icon="hammer")
        self.btn_watch = widgets.Button(description="Start Watchdog", button_style="success", icon="eye")
        
        self.btn_scan.on_click(self._on_scan_clicked)
        self.btn_build.on_click(self._on_build_clicked)
        self.btn_watch.on_click(self._on_watch_clicked)
        
        self.control_panel = widgets.HBox([self.btn_scan, self.btn_build, self.btn_watch])
        self.main_ui = widgets.VBox([self.title, self.control_panel, self.out])

    def _ui_log(self, message: str):
        """Appends logs directly to the widget output area."""
        with self.out:
            print(f"[{time.strftime('%H:%M:%S')}] {message}")

    def _on_scan_clicked(self, b):
        self._ui_log(f"Scanning {self.input_dir} for raw geometries...")
        files = list(self.input_dir.glob("*.xyz"))
        if not files:
            self._ui_log("No .xyz files found in the Input directory.")
            return
            
        self._ui_log(f"Found {len(files)} files. Handoff to Stage 1.0 Ingestor initiated.")
        # In a full run, this triggers cochem_stage2_ingestor.py's ThreadPool

    def _on_build_clicked(self, b):
        self._ui_log("Invoking RDKit 3D Coordinate Generator... (Requires CoChem-PLAY module)")
        # Placeholder for the RDKit bridging logic

    def _on_watch_clicked(self, b):
        if not HAS_WATCHDOG:
            self._ui_log("Watchdog module unavailable.")
            return
            
        if self.observer and self.observer.is_alive():
            self._ui_log("Stopping Watchdog Daemon...")
            self.observer.stop()
            self.observer.join()
            self.btn_watch.description = "Start Watchdog"
            self.btn_watch.button_style = "success"
        else:
            self._ui_log(f"Starting Watchdog Daemon on {self.input_dir}...")
            event_handler = IngestionWatchdog(self._ui_log)
            self.observer = Observer()
            self.observer.schedule(event_handler, str(self.input_dir), recursive=False)
            self.observer.start()
            self.btn_watch.description = "Stop Watchdog"
            self.btn_watch.button_style = "danger"

    def display(self):
        display(self.main_ui)

if __name__ == "__main__":
    # If run as a standard script, inform the user it is a Jupyter native tool.
    print("CoChem-MInt Backend initialized.")
    print("To launch the GUI, import CoChemMIntUI into a Jupyter Notebook cell and call .display()")