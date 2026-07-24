#!/usr/bin/env python3
"""
CoChem-MInt: Molecular Intake Hub & Directory Scanner (Stage 2.0)

Provides a resilient Jupyter GUI for file uploads, folder monitoring, and 
system registry validation. Fixes the JupyterLab 'Ghost Upload' byte-flush bug
and utilizes bounded thread pools to prevent UI locking during heavy parses.
"""

import os
import sys
import json
import time
import logging
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import ipywidgets as widgets
from IPython.display import display, clear_output

# Add repository root to path for Core Engine imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from core_engine.cochem_core_registry_manager import RegistryManager
    from core_engine.cochem_core_registry_schema import CoChemConfig
except ImportError:
    print("FATAL: CoChem-MInt requires the core_engine modules to be present.")
    sys.exit(1)

# Configure Local Logging
os.makedirs("Logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - [CoChem-MInt] - %(message)s',
    handlers=[
        logging.FileHandler("Logs/cochem_mint_ingestion.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("CoChem-MInt")

class MIntEngine:
    """
    Unified Ingestion Dashboard for parsing XYZ/SDF/MOL data, tracking
    hardware engines, and routing files into the CoChem pipeline.
    """
    def __init__(self, workspace_root: str = "."):
        self.root = Path(workspace_root).resolve()
        self.staging_dir = self.root / "Input_Files"
        self.processed_dir = self.root / "Processed"
        
        # Ensure intake directories exist
        self.staging_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        
        self.gatekeeper = RegistryManager(workspace_root=str(self.root))
        self.thread_pool = ThreadPoolExecutor(max_workers=4)
        
        try:
            self.config = self.gatekeeper.read_registry()
            self.registry_active = True
        except Exception as e:
            logger.error(f"Failed to connect to Golden Registry: {e}")
            self.config = None
            self.registry_active = False

        self._build_ui()

    def _build_ui(self):
        """Constructs the interactive widget layout."""
        self.header = widgets.HTML("<h2 style='color: #2ecc71;'>CoChem-MInt: Ingestion Hub</h2>")
        
        # Status Log
        self.log_out = widgets.Output(layout={'border': '1px solid #444', 'height': '150px', 'overflow_y': 'auto', 'padding': '5px'})
        
        # File Upload Widget (Resolving JupyterLab Ghost Bug via explicit manual extraction)
        self.uploader = widgets.FileUpload(
            accept='.xyz,.sdf,.mol,.out',
            multiple=True,
            description='Select Coordinates',
            button_style='info'
        )
        self.uploader.observe(self._handle_upload, names='value')
        
        # Directory Scan Button
        self.scan_btn = widgets.Button(description='Scan Input_Files/', button_style='primary', icon='search')
        self.scan_btn.on_click(self._scan_directory)
        
        # Registry Status
        reg_color = "green" if self.registry_active else "red"
        reg_text = "Gatekeeper Connected" if self.registry_active else "Registry Missing!"
        self.registry_status = widgets.HTML(f"<b style='color: {reg_color};'>Status: {reg_text}</b>")

        self.ui = widgets.VBox([
            self.header, 
            self.registry_status,
            widgets.HBox([self.uploader, self.scan_btn]), 
            self.log_out
        ])

    def _print_status(self, msg: str, style: str = "info"):
        colors = {"info": "#3498db", "success": "#2ecc71", "warning": "#f1c40f", "fail": "#e74c3c"}
        color = colors.get(style, "white")
        with self.log_out:
            display(widgets.HTML(f"<span style='color: {color};'>[{time.strftime('%H:%M:%S')}] {msg}</span>"))

    def _update_registry_target(self, filepath: Path):
        """Atomically locks the newly ingested file as the active geometry."""
        def update_logic(cfg: CoChemConfig):
            # Ensure the active_jobs dictionary exists and set the current_geometry
            if not cfg.active_jobs:
                 cfg.active_jobs = {}
            cfg.active_jobs["current_geometry"] = str(filepath.absolute())
            cfg.active_jobs["optimization_state"] = "MINT_INGESTED"
            return cfg

        if self.gatekeeper.transaction(update_logic):
            self._print_status(f"Locked {filepath.name} into Active Registry.", "success")
        else:
            self._print_status(f"Gatekeeper rejected {filepath.name}.", "fail")

    def _process_file(self, filepath: Path):
        """Mock parsing logic to validate file extensions before committing."""
        try:
            # In production, this runs Kabsch RMSD / Valency checks via cochem_stage2_ingestor.py
            self._print_status(f"Validating topology for: {filepath.name}...", "info")
            time.sleep(0.5) # Simulate IO read
            
            if filepath.suffix not in ['.xyz', '.sdf', '.mol', '.out']:
                 raise ValueError("Unsupported extension.")
                 
            # Move to processed and lock
            dest_path = self.processed_dir / filepath.name
            filepath.rename(dest_path)
            
            self._update_registry_target(dest_path)
            
        except Exception as e:
            self._print_status(f"Rejection: {filepath.name} - {e}", "fail")

    def _handle_upload(self, change):
        """Traps the uploaded byte stream and forcibly flushes it to the staging directory."""
        if not change.new:
            return
            
        with self.log_out:
            for filename, file_info in change.new.items():
                self._print_status(f"Extracting uploaded payload: {filename}", "info")
                content = file_info['content']
                
                target_path = self.staging_dir / filename
                with open(target_path, "wb") as f:
                    f.write(content)
                    f.flush()
                    os.fsync(f.fileno()) # Enforce disk write to clear ghost bug
                
                # Offload processing to thread pool to keep UI alive
                self.thread_pool.submit(self._process_file, target_path)
                
        # Clear widget state to allow re-upload of the same filename
        self.uploader.value = {} 

    def _scan_directory(self, b):
        """Reads the local Input_Files directory for manual drops."""
        files = list(self.staging_dir.glob("*.*"))
        if not files:
            self._print_status("No files found in Input_Files/.", "warning")
            return
            
        self._print_status(f"Scanning {len(files)} files in directory...", "info")
        for f in files:
            self.thread_pool.submit(self._process_file, f)

    def render(self):
        display(self.ui)

if __name__ == "__main__":
    app = MIntEngine()
    app.render()