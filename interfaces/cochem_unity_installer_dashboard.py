#!/usr/bin/env python3
"""
CoChem-UNITY: Stage 0.1 - Pipeline Installer Dashboard
Generates the dynamic GUI for provisioning the CoChem micro-silos.
Includes Option 3: Artifacts Directory Bridge for Offline Module Ingestion.
"""
import os
import json
import hashlib
import sys
import subprocess
import tempfile
import shutil
import zipfile
from pathlib import Path
import ipywidgets as widgets
from IPython.display import display, clear_output

ECOSYSTEM_REGISTRY = {
    "CoChem-CORE": {"desc": "Mandatory foundational registry and environment siloing.", "repo": "https://github.com/CoChem/CoChem-CORE", "mandatory": True},
    "CoChem-TOPOS": {"desc": "Topological mapping and Eckart frame alignment.", "repo": "https://github.com/CoChem/CoChem-TOPOS", "mandatory": False},
    "CoChem-TORQ": {"desc": "Torsional Discovery and Statistical Mechanics.", "repo": "https://github.com/CoChem/CoChem-TORQ", "mandatory": False}
}

class UnityInstallerGUI:
    def __init__(self):
        self.buttons = {}
        self.artifact_dir = Path(os.environ.get("COCHEM_ARTIFACT_DIR", str(Path.home() / "CoChem_Artifacts")))
        
        # Engine Registry for ORCA tarballs
        self.engine_registry = self.artifact_dir / "Registry" / "Engines"
        self.engine_registry.mkdir(parents=True, exist_ok=True)
        
        # Module Registry for CoChem GitHub Zips
        self.module_registry = self.artifact_dir / "Registry" / "Modules"
        self.module_registry.mkdir(parents=True, exist_ok=True)
        
        self.log_file = self.artifact_dir / "Logs" / "cochem_unity_deploy.log"
        self.hint_file = self.artifact_dir / "Registry" / "host_orca_path.txt"
        self._build_ui()

    def _get_git_hash(self):
        return hashlib.sha256(os.urandom(32)).hexdigest()[:16]

    def _workspace_root(self) -> Path:
        cwd = Path.cwd()
        if cwd.name == "CoChem-CORE":
            return cwd.parent
        return cwd

    def _clone_selected_repos(self, selected_modules: list) -> None:
        workspace_root = self._workspace_root()
        for module in selected_modules:
            if module == "CoChem-CORE":
                print("ℹ️ CoChem-CORE already present in current workspace.")
                continue

            target_dir = workspace_root / module
            if target_dir.exists():
                print(f"ℹ️ {module} already exists at: {target_dir}")
                continue

            repo_url = ECOSYSTEM_REGISTRY[module]["repo"]
            if not repo_url:
                print(f"ℹ️ {module} has no separate repository target.")
                continue

            # --- OPTION 3: ARTIFACTS BRIDGE SIDELOADING ---
            sideload_success = False
            possible_zips = [
                self.module_registry / f"{module}.zip",
                self.module_registry / f"{module}-main.zip",
                self.engine_registry / f"{module}.zip",
                self.artifact_dir / f"{module}.zip",
                self.artifact_dir / f"{module}-main.zip"
            ]
            
            for zpath in possible_zips:
                if zpath.exists():
                    print(f"📦 Air-Gap Bridge: Sideloading {module} from {zpath}...")
                    try:
                        with zipfile.ZipFile(zpath, 'r') as zip_ref:
                            zip_ref.extractall(workspace_root)
                        
                        # Handle GitHub's default "-main" or "-master" extraction suffix
                        for suffix in ["-main", "-master"]:
                            extracted_dir = workspace_root / f"{module}{suffix}"
                            if extracted_dir.exists() and not target_dir.exists():
                                extracted_dir.rename(target_dir)
                                
                        if target_dir.exists():
                            print(f"✅ Successfully extracted {module} into workspace. Network bypassed.")
                            sideload_success = True
                            break
                    except Exception as e:
                        print(f"⚠️ Failed to extract {zpath}: {e}")
            
            if sideload_success:
                continue
            # ----------------------------------------------

            try:
                # Pre-check remote visibility so optional module failures are explicit and non-blocking.
                print(f"🌐 Attempting network clone for {module}...")
                ls = subprocess.run(["git", "ls-remote", "--heads", repo_url], check=False, capture_output=True, text=True)
                if ls.returncode != 0:
                    alt_url = repo_url if repo_url.endswith(".git") else f"{repo_url}.git"
                    ls_alt = subprocess.run(["git", "ls-remote", "--heads", alt_url], check=False, capture_output=True, text=True)
                    if ls_alt.returncode != 0:
                        err = (ls.stderr or ls_alt.stderr or "").strip() or "remote not accessible"
                        print(f"⚠️ Skipping {module}: repository not reachable via network ({err}).")
                        print(f"💡 FIX: Download {module}.zip from GitHub and drop it into {self.module_registry}")
                        continue
                    repo_url = alt_url

                subprocess.run(["git", "clone", "--depth", "1", repo_url, str(target_dir)], check=True, capture_output=True, text=True)
                print(f"✅ Cloned {module} to: {target_dir}")
            except subprocess.CalledProcessError as e:
                err = (e.stderr or "").strip() or (e.stdout or "").strip() or str(e)
                print(f"⚠️ Clone skipped for {module}: {err}")

    def _resolve_host_orca_candidate(self, raw_path: str) -> Path:
        p = (raw_path or "").strip().strip('"').strip("'")
        if not p:
            return Path("")

        if len(p) > 2 and p[1] == ":":
            drive = p[0].lower()
            tail = p[2:].replace("\\", "/").lstrip("/")
            candidates = [
                Path(f"/mnt/{drive}/{tail}"),
                Path(f"/host_mnt/{drive}/{tail}"),
                Path(f"/run/desktop/mnt/host/{drive}/{tail}"),
                Path(f"/{drive}/{tail}"),
                Path(f"/host_orca/{Path(tail).name}"),
                Path("/host_orca/orca.exe"),
                Path("/host_orca/orca"),
            ]
            for c in candidates:
                if c.exists():
                    return c
            return candidates[0]

        return Path(p)

    def _existing_host_mount_roots(self) -> list:
        roots = [
            Path("/mnt/c"),
            Path("/host_mnt/c"),
            Path("/run/desktop/mnt/host/c"),
            Path("/host_orca"),
        ]
        return [str(r) for r in roots if r.exists()]

    def _verify_host_orca_path(self, raw_path: str) -> bool:
        candidate = self._resolve_host_orca_candidate(raw_path)
        if not str(candidate):
            print("⚠️ Host ORCA path is empty.")
            return False

        if candidate.is_dir():
            options = [candidate / "orca", candidate / "bin" / "orca", candidate / "orca.exe", candidate / "bin" / "orca.exe"]
            candidate = next((opt for opt in options if opt.exists()), candidate)

        if not candidate.exists():
            print(f"❌ Host ORCA path does not exist from container view: {candidate}")
            mounts = self._existing_host_mount_roots()
            if mounts:
                print(f"ℹ️ Detected host mount roots: {', '.join(mounts)}")
            else:
                print("⚠️ No host mount roots detected inside container (/mnt/c, /host_mnt/c, /run/desktop/mnt/host/c, /host_orca).")
            return False

        verify_dir = Path(tempfile.mkdtemp(prefix="cochem_orca_verify_", dir=str(self.artifact_dir)))
        inp = verify_dir / "verify_orca.inp"
        inp.write_text("! SP STO-3G\n*xyz 0 1\nHe 0 0 0\n*\n", encoding="utf-8")
        try:
            result = subprocess.run([str(candidate), str(inp)], cwd=str(verify_dir), capture_output=True, text=True, timeout=90)
            stdout_upper = (result.stdout or "").upper()
            out_file = verify_dir / "verify_orca.out"
            out_text = out_file.read_text(errors="replace").upper() if out_file.exists() else ""
            markers = ["ORCA TERMINATED NORMALLY", "O   R   C   A", "O R C A"]
            has_marker = any(m in stdout_upper or m in out_text for m in markers)
            if result.returncode == 0 and has_marker:
                print(f"✅ Host ORCA verification passed via: {candidate}")
                return True
            print("❌ Host ORCA verification failed.")
            return False
        except Exception as e:
            print(f"❌ Host ORCA verification exception: {e}")
            return False
        finally:
            shutil.rmtree(verify_dir, ignore_errors=True)

    def _has_staged_orca_archive(self) -> bool:
        patterns = ["orca*.tar.xz", "orca*.tz", "orca*.tar.gz", "ORCA*.tar.xz", "ORCA*.tz", "ORCA*.tar.gz"]
        for pattern in patterns:
            for candidate in self.engine_registry.glob(pattern):
                if candidate.is_file():
                    return True
        return False

    def _list_staged_archives(self, registry_path: Path, patterns: list) -> list:
        seen = set()
        staged = []
        for pattern in patterns:
            for candidate in registry_path.glob(pattern):
                if not candidate.is_file():
                    continue
                key = str(candidate.resolve())
                if key in seen:
                    continue
                seen.add(key)
                staged.append(candidate)
        staged.sort(key=lambda p: p.name.lower())
        return staged

    def _launch_setup_orchestrator(self) -> None:
        repo_root = Path.cwd()
        orchestrator = repo_root / "stage_0_0_setup_orchestrator.py"
        if not orchestrator.exists():
            print(f"❌ Missing orchestrator: {orchestrator}")
            return

        log_dir = self.artifact_dir / "Logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        try:
            log_handle = open(self.log_file, "a", encoding="utf-8")
            subprocess.Popen(
                [sys.executable, str(orchestrator)],
                cwd=str(repo_root),
                env=env,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            print(f"🚀 Setup started in background via {orchestrator.name}")
            print(f"📄 Live log: {self.log_file}")
            self._render_status()
        except Exception as e:
            print(f"❌ Failed to launch orchestrator: {e}")

    def _read_log_tail(self, max_lines: int = 120) -> str:
        if not self.log_file.exists():
            return "No deployment log found yet. Click Lock & Deploy to start setup."
        try:
            lines = self.log_file.read_text(errors="replace").splitlines()
        except Exception as e:
            return f"Failed to read deployment log: {e}"

        if not lines:
            return "Deployment log is present but currently empty."
        return "\n".join(lines[-max_lines:])

    def _render_status(self):
        with self.status_out:
            clear_output()
            print(self._read_log_tail())

    def _on_refresh_status(self, _):
        self._render_status()

    def _on_clear_status(self, _):
        with self.status_out:
            clear_output()
            print("Status panel cleared. Click Refresh Status to reload deployment log.")

    def _load_saved_host_orca_hint(self) -> str:
        if not self.hint_file.exists():
            return ""
        try:
            return self.hint_file.read_text(encoding="utf-8").strip()
        except Exception:
            return ""

    def _persist_host_orca_hint(self, raw_hint: str) -> bool:
        hint = (raw_hint or "").strip()
        if not hint:
            return False
        self.hint_file.parent.mkdir(parents=True, exist_ok=True)
        self.hint_file.write_text(hint, encoding="utf-8")
        return True

    def _on_save_host_orca_hint(self, _):
        with self.out:
            clear_output()
            if self._persist_host_orca_hint(self.host_orca_path.value):
                print(f"✅ Host ORCA hint saved to: {self.hint_file}")
                self.host_orca_help.value = "<span style='color: green;'>Host ORCA hint saved.</span>"
            else:
                print("⚠️ Host ORCA path is empty.")

    def _on_clear_host_orca_hint(self, _):
        with self.out:
            clear_output()
            self.host_orca_path.value = ""
            if self.hint_file.exists():
                try:
                    self.hint_file.unlink()
                    print(f"✅ Removed saved host ORCA hint.")
                except OSError as e:
                    print(f"❌ Failed to remove saved host ORCA hint: {e}")

    def _build_ui(self):
        self.out = widgets.Output()
        self.status_out = widgets.Output(layout=widgets.Layout(border="1px solid #ccc", padding="8px", max_height="260px", overflow_y="auto"))
        title = widgets.HTML("<h2>CoChem-UNITY: Ecosystem Deployment Dashboard</h2>")
        
        artifact_hint = widgets.HTML(
            f"<div style='background-color: #f8f9fa; padding: 10px; border-radius: 5px; border-left: 4px solid #0366d6; margin-bottom: 15px;'>"
            f"<b>CoChem Artifacts Bridge:</b> {self.artifact_dir}<br>"
            f"<b>1. ORCA Drop Target:</b> {self.engine_registry}<br>"
            f"<b>2. Module Drop Target (.zip):</b> {self.module_registry}<br>"
            f"<i style='font-size: 0.9em; color: #555;'>Offline? Download the Github .zip files and drop them into the target folder above.</i>"
            f"</div>"
        )
        
        checks = []
        for prog, info in ECOSYSTEM_REGISTRY.items():
            cb = widgets.Checkbox(value=info["mandatory"], description=prog, disabled=info["mandatory"])
            desc = widgets.HTML(f"<i style='color: gray; margin-left: 10px;'>{info['desc']}</i>")
            self.buttons[prog] = cb
            checks.append(widgets.HBox([cb, desc]))
            
        self.deploy_target = widgets.Dropdown(options=["Codespaces", "Local DevContainer", "HPC SLURM"], description="Target:")
        self.host_orca_path = widgets.Text(
            value="", placeholder="Optional: C:\\ORCA\\orca.exe", description="Host ORCA:",
            style={"description_width": "initial"}, layout=widgets.Layout(width="100%")
        )

        # Updated to accept .zip for Offline Sideloading
        self.orca_upload = widgets.FileUpload(
            accept=".tar.xz,.tz,.tar.gz,.zip",
            multiple=True,
            description="Drop Archives"
        )
        self.orca_upload.observe(self._on_orca_upload, names="value")
        self.stage_orca_btn = widgets.Button(description="Stage Uploads", button_style="primary")
        self.stage_orca_btn.on_click(self._on_stage_orca_click)

        self.submit_btn = widgets.Button(description="Lock & Deploy", button_style="success")
        self.submit_btn.on_click(self._on_submit)

        self.status_title = widgets.HTML("<h3>Deployment Status</h3>")
        self.status_info = widgets.HTML(
            f"<b>Live Log:</b> {self.log_file}<br>"
            "<span style='color: gray;'>Use Refresh to view latest deployment output.</span>"
        )
        self.host_orca_assist_title = widgets.HTML("<h4>Host ORCA Assist</h4>")
        self.host_orca_help = widgets.HTML("<span style='color: gray;'>Optional helper for host ORCA reuse.</span>")
        self.save_host_orca_btn = widgets.Button(description="Save Hint", button_style="primary")
        self.save_host_orca_btn.on_click(self._on_save_host_orca_hint)
        self.clear_host_orca_btn = widgets.Button(description="Clear Hint", button_style="warning")
        self.clear_host_orca_btn.on_click(self._on_clear_host_orca_hint)

        saved_hint = self._load_saved_host_orca_hint()
        if saved_hint and not self.host_orca_path.value:
            self.host_orca_path.value = saved_hint

        self.refresh_btn = widgets.Button(description="Refresh Status", button_style="info")
        self.refresh_btn.on_click(self._on_refresh_status)
        self.clear_btn = widgets.Button(description="Clear Status", button_style="warning")
        self.clear_btn.on_click(self._on_clear_status)

        self._render_status()
        
        self.main_ui = widgets.VBox([
            title,
            artifact_hint,
            widgets.VBox(checks),
            self.deploy_target,
            self.host_orca_path,
            widgets.HBox([self.orca_upload, self.stage_orca_btn]),
            self.submit_btn,
            self.status_title,
            self.status_info,
            self.host_orca_assist_title,
            self.host_orca_help,
            widgets.HBox([self.save_host_orca_btn, self.clear_host_orca_btn]),
            widgets.HBox([self.refresh_btn, self.clear_btn]),
            self.status_out,
            self.out
        ])

    def _extract_upload_entries(self, files):
        if not files:
            return []
        if isinstance(files, dict):
            return [(fname, fdata) for fname, fdata in files.items()]
        entries = []
        for entry in files:
            if isinstance(entry, dict):
                entries.append((entry.get("name", ""), entry))
            else:
                entries.append((getattr(entry, "name", ""), entry))
        return entries

    def _stage_orca_upload(self, files) -> bool:
        entries = self._extract_upload_entries(files)
        if not entries:
            print("⚠️ No upload payload detected yet.")
            return False

        staged_any = False
        for fname, fdata in entries:
            fname_lower = fname.lower()
            if not fname_lower.endswith((".tar.xz", ".tz", ".tar.gz", ".zip")):
                print(f"❌ Unsupported archive type: {fname or 'unknown'}")
                continue
            
            # Sort zip files to Modules registry, and tarballs to Engines registry
            if fname_lower.endswith(".zip"):
                target = self.module_registry / fname
            else:
                target = self.engine_registry / fname
                
            if isinstance(fdata, dict):
                content = fdata.get("content", b"")
            else:
                content = getattr(fdata, "content", b"")
            if isinstance(content, memoryview):
                content = content.tobytes()
            elif isinstance(content, bytearray):
                content = bytes(content)
            if not content:
                print(f"❌ Upload had no content: {fname}")
                continue
            with open(target, "wb") as f:
                f.write(content)
            size = target.stat().st_size if target.exists() else 0
            if size == 0:
                print(f"❌ Staging failed (zero bytes): {target}")
                continue
            print(f"✅ Archive staged to: {target} ({size} bytes)")
            staged_any = True

        return staged_any

    def _on_stage_orca_click(self, _):
        with self.out:
            clear_output()
            staged = self._stage_orca_upload(getattr(self.orca_upload, "value", None))
            if staged:
                print("➡️ Archives are staged and ready for setup.")
                
            eng_archives = self._list_staged_archives(self.engine_registry, ["*tar*"])
            if eng_archives:
                print("\n📦 Staged Engine archives:")
                for a in eng_archives: print(f" - {a.name} ({a.stat().st_size} bytes)")
                
            mod_archives = self._list_staged_archives(self.module_registry, ["*.zip"])
            if mod_archives:
                print("\n📦 Staged Module archives:")
                for a in mod_archives: print(f" - {a.name} ({a.stat().st_size} bytes)")

    def _on_orca_upload(self, change):
        files = change.get("new") if isinstance(change, dict) else getattr(change, "new", None)
        if not files: return
        self._on_stage_orca_click(None)

    def _on_submit(self, b):
        with self.out:
            clear_output()
            setup_dir = Path("cochem_setup")
            setup_dir.mkdir(parents=True, exist_ok=True)
            manifest_path = setup_dir / "cochem_deployment_manifest.json"
            lock_file = Path(".cochem_unity.lock")
            
            selected_modules = [p for p, cb in self.buttons.items() if cb.value]
            selected_repos = {p: ECOSYSTEM_REGISTRY[p]["repo"] for p in selected_modules}
            host_orca_path = self.host_orca_path.value.strip()
            host_orca_verified = False
            manifest = {
                "version": "2026.2",
                "git_provenance_hash": self._get_git_hash(),
                "deployment_target": self.deploy_target.value,
                "modules": selected_modules,
                "selected_modules": selected_repos,
                "host_orca_path": host_orca_path
            }
            
            with open(manifest_path, "w") as f:
                json.dump(manifest, f, indent=4)
            with open(lock_file, "w") as f:
                f.write(manifest["git_provenance_hash"])

            if host_orca_path:
                print("🔬 Verifying host ORCA execution pathway from container...")
                host_orca_verified = self._verify_host_orca_path(host_orca_path)
                if not host_orca_verified and not self._has_staged_orca_archive():
                    print("⚠️ Host ORCA verification failed. Fix path/mount access or stage ORCA archive instead.")
                    self.submit_btn.disabled = False
                    self.submit_btn.description = "Lock & Deploy"
                    self._render_status()
                    return
                elif self._persist_host_orca_hint(host_orca_path):
                    print(f"✅ Host ORCA hint recorded: {self.hint_file}")
                
            print(f"✅ SUCCESS: Manifest written to {manifest_path}")
            print(f"✅ Selected modules: {', '.join(selected_modules)}")

            print("\n🔄 Initializing Workspace Repositories (Air-Gap priority)...")
            self._clone_selected_repos(selected_modules)

            started = False
            staged_now = False
            if not host_orca_verified:
                staged_now = self._stage_orca_upload(getattr(self.orca_upload, "value", None))

            if host_orca_verified or staged_now or self._has_staged_orca_archive():
                print("\n🔄 Launching setup orchestrator...")
                self._launch_setup_orchestrator()
                started = True
            else:
                print("\n⚠️ ORCA archive not detected in engine registry.")
                print(f"📦 Expected location: {self.engine_registry}")
                print("➡️ Upload ORCA archive first, or type 'BYPASSED' into Host ORCA field if you wish to run in Python-Only mode.")

            if started:
                self.submit_btn.disabled = True
                self.submit_btn.description = "Deployment Triggered"
            else:
                self.submit_btn.disabled = False
                self.submit_btn.description = "Lock & Deploy"

            self._render_status()

if __name__ == "__main__":
    installer = UnityInstallerGUI()
    display(installer.main_ui)