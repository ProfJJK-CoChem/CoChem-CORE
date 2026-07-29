# cochem_canvas_target: stage_0_0_setup_orchestrator.py
import os
import sys
import subprocess
import shutil
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

    # Air-Gap Enforcement: Auto-migrate ORCA archives accidentally dropped in the repo root
    for ext in ["*.tar.xz", "*.tz", "*.tar.gz"]:
        for file in repo_root.glob(f"orca_6_1_1{ext}"):
            target_path = engine_staging_dir / file.name
            print(f"\n⚠️  WARNING: Large ORCA archive detected inside Git repository!")
            print(f"🔄 Moving {file.name} to Air-Gap Staging to prevent Git tracking lockups...")
            shutil.move(str(file), str(target_path))
            print(f"✅ Securely moved to: {target_path}")

    return env

def run_setup_phases(repo_root: Path, env: dict):
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
                
                if conda_path:
                    print(f"🔄 Routing Phase 5 through {conda_path} inside cochem_torq_silo...")
                    subprocess.run([conda_path, "run", "-n", "cochem_torq_silo", "python", str(phase)], env=env, check=True)
                else:
                    subprocess.run([sys.executable, str(phase)], env=env, check=True)
            else:
                subprocess.run([sys.executable, str(phase)], env=env, check=True)
        except subprocess.CalledProcessError as e:
            print(f"\n❌ Phase Execution Failed (Exit code: {e.returncode}).")
            print("Please check the logs in ~/CoChem_Artifacts/Logs/ for details.")
            sys.exit(e.returncode)

def launch_unity_dashboard(repo_root: Path, env: dict):
    """Hands off execution to the GUI only after silos are built."""
    gui_script = repo_root / "interfaces" / "cochem_unity_installer_dashboard.py"
    if not gui_script.exists():
        print(f"\n⚠️  WARNING: GUI Dashboard not found at {gui_script}.")
        print("CoChem Core is installed, but the UI is missing. Proceeding via CLI only.")
        return

    print("\n🌐 Bootstrapping complete. Launching CoChem-UNITY Dashboard...")
    
    # Check standard paths and the custom local bootstrap path
    conda_path = shutil.which("mamba") or shutil.which("conda")
    if not conda_path:
        local_conda = Path.home() / ".local" / "miniconda" / "bin" / "conda"
        if local_conda.exists():
            conda_path = str(local_conda)

    if conda_path:
        try:
            # Execute the GUI inside the properly configured conda environment
            print(f"🔄 Routing GUI through {conda_path} inside cochem_torq_silo...")
            subprocess.run([conda_path, "run", "-n", "cochem_torq_silo", "python", str(gui_script)], env=env, check=True)
        except subprocess.CalledProcessError as e:
             print(f"\n❌ GUI Launch failed via Conda: {e}")
    else:
         print("\n⚠️  Conda not found in path. Attempting to launch GUI with system python...")
         subprocess.run([sys.executable, str(gui_script)], env=env)

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
    run_setup_phases(repo_root, env)
    
    # 2. Hand off to the UI
    launch_unity_dashboard(repo_root, env)

if __name__ == "__main__":
    main()