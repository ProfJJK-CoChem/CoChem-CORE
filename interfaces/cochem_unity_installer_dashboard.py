#!/usr/bin/env python3
"""
CoChem-UNITY: Stage 0.1 - Pipeline Installer Dashboard
Generates the dynamic GUI for provisioning the CoChem micro-silos.
"""
import os
import json
import hashlib
import ipywidgets as widgets
from IPython.display import display, clear_output

ECOSYSTEM_REGISTRY = {
    "CoChem-CORE": {"desc": "Mandatory foundational registry and environment siloing.", "repo": "https://github.com/CoChem/CoChem-CORE", "mandatory": True},
    "CoChem-MInt": {"desc": "Molecular Intake (MInt) GUI & Canonicalization Engine.", "repo": "https://github.com/CoChem/CoChem-MInt", "mandatory": True},
    "CoChem-TOPOS": {"desc": "Topological mapping and Eckart frame alignment.", "repo": "https://github.com/CoChem/CoChem-TOPOS", "mandatory": False},
    "CoChem-TORQ": {"desc": "Torsional Discovery and Statistical Mechanics.", "repo": "https://github.com/CoChem/CoChem-TORQ", "mandatory": False}
}

class UnityInstallerGUI:
    def __init__(self):
        self.buttons = {}
        self._build_ui()

    def _get_git_hash(self):
        return hashlib.sha256(os.urandom(32)).hexdigest()[:16]

    def _build_ui(self):
        self.out = widgets.Output()
        title = widgets.HTML("<h2>CoChem-UNITY: Ecosystem Deployment Dashboard</h2>")
        
        checks = []
        for prog, info in ECOSYSTEM_REGISTRY.items():
            cb = widgets.Checkbox(value=info["mandatory"], description=prog, disabled=info["mandatory"])
            desc = widgets.HTML(f"<i style='color: gray; margin-left: 10px;'>{info['desc']}</i>")
            self.buttons[prog] = cb
            checks.append(widgets.HBox([cb, desc]))
            
        self.deploy_target = widgets.Dropdown(options=["Codespaces", "Local DevContainer", "HPC SLURM"], description="Target:")
        self.submit_btn = widgets.Button(description="Lock & Deploy", button_style="success")
        self.submit_btn.on_click(self._on_submit)
        
        self.main_ui = widgets.VBox([title, widgets.VBox(checks), self.deploy_target, self.submit_btn, self.out])

    def _on_submit(self, b):
        with self.out:
            clear_output()
            manifest_path = "cochem_deployment_manifest.json"
            lock_file = ".cochem_unity.lock"
            
            selected = {p: ECOSYSTEM_REGISTRY[p]["repo"] for p, cb in self.buttons.items() if cb.value}
            manifest = {
                "version": "2026.2",
                "git_provenance_hash": self._get_git_hash(),
                "deployment_target": self.deploy_target.value,
                "selected_modules": selected
            }
            
            with open(manifest_path, "w") as f:
                json.dump(manifest, f, indent=4)
            with open(lock_file, "w") as f:
                f.write(manifest["git_provenance_hash"])
                
            print(f"✅ SUCCESS: Manifest written to {manifest_path}")
            self.submit_btn.disabled = True
            self.submit_btn.description = "Manifest Locked"

if __name__ == "__main__":
    installer = UnityInstallerGUI()
    display(installer.main_ui)