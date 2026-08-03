# cochem_canvas_target: stage_0_0_setup_orchestrator.py
import os
import sys
import subprocess
import shutil
import json
from pathlib import Path

def inject_local_paths(env: dict) -> dict:
    """Automatically patches the terminal profile and active env to include .local/bin and miniconda."""
    local_bin = Path.home() / ".local" / "bin"
    miniconda_bin = Path.home() / ".local" / "miniconda" / "bin"
    
    paths_to_inject = []
    if local_bin.exists() and str(local_bin) not in env.get("PATH", ""):
        paths_to_inject.append(str(local_bin))
    if miniconda_bin.exists() and str(miniconda_bin) not in env.get("PATH", ""):
        paths_to_inject.append(str(miniconda_bin))
        
    if paths_to_inject:
        added_paths = ":".join(paths_to_inject)
        env["PATH"] = f"{added_paths}:{env.get('PATH', '')}"
        
    export_string = f'\n# CoChem Automated Path Injection\nexport PATH="{local_bin}:{miniconda_bin}:$PATH"\n'
    
    for rc_file in [".bashrc", ".zshrc"]:
        profile_path = Path.home() / rc_file
        if profile_path.exists():
            content = profile_path.read_text()
            if "# CoChem Automated Path Injection" not in content:
                with open(profile_path, "a") as f:
                    f.write(export_string)
                print(f"🔧 Automatically patched {rc_file} to include local binaries.")
                
    return env

def set_artifact_dir(repo_root: Path, env: dict) -> dict:
    """Enforces the strict Air-Gap directory for logs, state, and external binaries."""
    artifact_dir = Path.home() / "CoChem_Artifacts"
    engine_staging_dir = artifact_dir / "Registry" / "Engines"
    
    artifact_dir.mkdir(parents=True, exist_ok=True)
    engine_staging_dir.mkdir(parents=True, exist_ok=True)
    
    env["COCHEM_ARTIFACT_DIR"] = str(artifact_dir)
    env["COCHEM_ENGINE_REGISTRY"] = str(engine_staging_dir)
    print(f"🔒 Air-Gap Enforced: All logs and state files routed to {artifact_dir}")
    print(f"📦 Engine Staging Directory locked at: {engine_staging_dir}")
    print("📍 Place ORCA archives in this exact folder before rerunning setup if prompted.")

    # Air-Gap Enforcement: Auto-migrate ORCA archives accidentally dropped in common user locations
    source_dirs = [repo_root, Path.home(), Path.home() / "Downloads"]
    for source_dir in source_dirs:
        if not source_dir.exists():
            continue
        for pattern in ["orca*.tar.xz", "orca*.tz", "orca*.tar.gz", "ORCA*.tar.xz", "ORCA*.tz", "ORCA*.tar.gz"]:
            for file in source_dir.glob(pattern):
                if not file.is_file():
                    continue
                target_path = engine_staging_dir / file.name
                if target_path.exists():
                    continue
                print(f"\n⚠️  WARNING: ORCA archive detected outside Air-Gap staging: {file}")
                print(f"🔄 Moving {file.name} to Air-Gap Staging to prevent path drift...")
                shutil.move(str(file), str(target_path))
                print(f"✅ Securely moved to: {target_path}")

    return env

def phase4_torq_silo_active(repo_root: Path) -> bool:
    """Reads Phase 4 state to determine whether cochem_torq_silo exists for Phase 5 execution routing."""
    p4_state = repo_root / "cochem_setup" / "cochem_state_p4.json"
    if not p4_state.exists():
        return False
    try:
        with open(p4_state, "r") as f:
            data = json.load(f)
        return bool(data.get("torq_silo_active", False))
    except Exception:
        return False

def run_setup_phases(repo_root: Path, env: dict) -> bool:
    """Executes the core 5 phases sequentially using pure Python and Conda silos."""
    setup_dir = repo_root / "cochem_setup"
    
    phases = [
        setup_dir / "cochem_setup_phase_1.py",
        setup_dir / "cochem_setup_phase_2.py",
        setup_dir / "cochem_setup_phase_3.py",
        setup_dir / "cochem_setup_phase_4.py",
        setup_dir / "cochem_setup_phase_5.py"
    ]
    
    print("\n🚀 Initiating CoChem Core Bootstrapper...")
    for phase in phases:
        if not phase.exists():
            print(f"❌ FATAL: Missing setup phase script: {phase}")
            sys.exit(1)
            
        print(f"\n▶️ Executing {phase.name}...")
        try:
            if phase.name == "cochem_setup_phase_5.py":
                # Evaluate Conda path AFTER Phase 4 potentially installs it
                conda_path = shutil.which("mamba") or shutil.which("conda")
                if not conda_path:
                    local_conda = Path.home() / ".local" / "miniconda" / "bin" / "conda"
                    if local_conda.exists():
                        conda_path = str(local_conda)
                
                if conda_path and phase4_torq_silo_active(repo_root):
                    print(f"🔄 Routing Phase 5 through {conda_path} inside cochem_torq_silo...")
                    subprocess.run([conda_path, "run", "-n", "cochem_torq_silo", "python", str(phase)], env=env, check=True)
                else:
                    print("⚠️  TORQ silo unavailable; running Phase 5 with orchestrator Python.")
                    subprocess.run([sys.executable, str(phase)], env=env, check=True)
            else:
                subprocess.run([sys.executable, str(phase)], env=env, check=True)
        except subprocess.CalledProcessError as e:
            if phase.name == "cochem_setup_phase_3.py" and e.returncode == 2:
                print("\n⚠️  Setup paused: ORCA archive is required before Phase 3 can complete.")
                print("📤 Opening CoChem-UNITY so you can upload/drag-drop the ORCA archive now.")
                return False
            print(f"\n❌ Phase Execution Failed (Exit code: {e.returncode}).")
            print("Please check the logs in ~/CoChem_Artifacts/Logs/ for details.")
            sys.exit(e.returncode)
    return True

def launch_unity_dashboard(repo_root: Path, env: dict):
    """Hands off execution to the GUI only after silos are built."""
    start_notebook = repo_root / "Start_Here.ipynb"
    if not start_notebook.exists():
        print(f"\n⚠️  WARNING: Start notebook not found at {start_notebook}.")
        print("CoChem Core is installed, but the UI is missing. Proceeding via CLI only.")
        return

    print("\n✅ Bootstrapping complete. Using local Jupyter notebook GUI path.")
    print(f"📓 Open this notebook in VS Code: {start_notebook}")
    print("▶️ Run cells in order to execute setup and render the deployment widget dashboard.")

def main():
    print("=======================================================")
    print(" CoChem Pipeline Initialization Orchestrator ")
    print("=======================================================\n")

    # OS Platform verification loop
    if sys.platform == "win32":
        print(f"❌ FATAL: Native Windows execution detected.")
        print("CoChem architecture requires a Linux backend for ORCA and OpenMPI.")
        print("Please run this setup within WSL2 (Ubuntu) or a Docker DevContainer.")
        print("See CoChem Master User Manual for detailed Windows 11 instructions.")
        sys.exit(1)

    repo_root = Path(__file__).resolve().parent
    print(f"📂 Repository Root: {repo_root}")

    env = os.environ.copy()
    env = inject_local_paths(env)
    
    # Pass repo_root to trigger the auto-migration sweeper
    env = set_artifact_dir(repo_root, env)
    
    # 1. Run the headless setup scripts to generate the Conda silos
    setup_completed = run_setup_phases(repo_root, env)

    # 2. Hand off to the UI
    launch_unity_dashboard(repo_root, env)

    if not setup_completed:
        print("\n⚠️  Setup is waiting on ORCA archive intake. Resume setup after upload.")

if __name__ == "__main__":
    main()