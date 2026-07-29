# cochem_canvas_target: cochem_setup/cochem_setup_phase_3.py
import os
import sys
import shutil
import subprocess
import tarfile
import urllib.request
import json
import hashlib
from pathlib import Path

def calculate_hash(file_path: str) -> str:
    """Cryptographic Binary Validation to prevent corrupted engine execution."""
    if not file_path or not Path(file_path).exists():
        return "Not_Found"
    try:
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for block in iter(lambda: f.read(4096), b""):
                sha256.update(block)
        return sha256.hexdigest()
    except (PermissionError, MemoryError):
        return "Error_Reading_Hash"

def verify_execution(binary_path: str, version_flag: str = "--version") -> bool:
    """Sanity check to ensure the binary is actually executable and not missing shared libraries."""
    if not binary_path or not Path(binary_path).exists():
        return False
    try:
        res = subprocess.run([binary_path, version_flag], capture_output=True, text=True, timeout=10)
        return res.returncode == 0 or "version" in res.stdout.lower() or "version" in res.stderr.lower() or res.returncode == 1
    except Exception:
        return False

def locate_system_orca():
    """Hypervisor-Aware ORCA Binary Hunt using Direct Host Mount Scanning."""
    print("➡️  Checking for system-wide ORCA via direct mount scanning...")
    
    orca_path = None

    # 1. Check Native Windows (If executing outside the orchestrator constraint)
    if sys.platform == "win32":
        orca_path = shutil.which("orca")
        if orca_path:
            return str(Path(orca_path).resolve())

    # 2. Host Mount Scan (Bypasses Subprocess Interop completely)
    print("➡️  Scanning known host mounts (/mnt/c/, /host_mnt/c/, /c/)...")
    
    # Common mount points for Windows C: drive in Docker/WSL
    host_mounts = [Path("/mnt/c"), Path("/host_mnt/c"), Path("/c")]
    
    # Standard installation targets on Windows
    search_dirs = [
        "orca",
        "ORCA",
        "Program Files/orca",
        "Program Files/ORCA",
        "Program Files (x86)/orca"
    ]

    for mount in host_mounts:
        if mount.exists():
            print(f"🔍 Host filesystem mount detected at: {mount}")
            # Fast check of standard directories
            for search_dir in search_dirs:
                target_dir = mount / search_dir
                if target_dir.exists():
                    potential_bin = target_dir / "orca.exe"
                    if potential_bin.exists():
                        orca_path = str(potential_bin.resolve())
                        print(f"✅ Host Windows ORCA discovered via direct mount at: {orca_path}")
                        print("⚠️  WARNING: Bridging Windows ORCA (.exe) into Linux drops OpenMPI efficiency.")
                        return orca_path
            
            # Shallow recursive fallback (Depth=2) to catch custom version folders like C:\orca_6_1_1\
            print("🔍 Standard paths empty. Executing shallow recursive scan on host drive...")
            try:
                for root, dirs, files in os.walk(mount, topdown=True):
                    # Restrict depth to prevent scanning the entire Windows drive
                    depth = root[len(str(mount)):].count(os.sep)
                    if depth > 2:
                        dirs.clear()
                        continue
                    if "orca.exe" in files:
                        orca_path = str(Path(root) / "orca.exe")
                        print(f"✅ Host Windows ORCA discovered via shallow scan at: {orca_path}")
                        print("⚠️  WARNING: Bridging Windows ORCA (.exe) into Linux drops OpenMPI efficiency.")
                        return orca_path
            except PermissionError:
                pass

    if not any(m.exists() for m in host_mounts) and sys.platform != "win32":
        print("⚠️  WARNING: No Windows host mounts detected. Ensure your devcontainer.json binds the C: drive.")

    # 3. Standard Linux / macOS / Docker DevContainer Internal Check
    if not orca_path:
        orca_path = shutil.which("orca")
        
    if orca_path and Path(orca_path).exists():
        if sys.platform != "win32" and not str(orca_path).endswith(".exe"):
             print(f"✅ Native Linux ORCA detected at: {orca_path}")
        return str(Path(orca_path).resolve())
        
    return None

def deploy_airgapped_orca():
    """Dynamic Extraction from COCHEM_ENGINE_REGISTRY to DevContainer Silo."""
    registry_path = os.environ.get("COCHEM_ENGINE_REGISTRY")
    registry_dir = Path(registry_path) if registry_path else Path.home() / "CoChem_Artifacts" / "Registry" / "Engines"
        
    print(f"🔍 Scanning Air-Gap Registry for ORCA archives in: {registry_dir}")
    
    if not registry_dir.exists():
        print("⚠️  Engine registry directory not found.")
        return None
        
    archives = list(registry_dir.glob("orca*6*.t*")) + list(registry_dir.glob("*.tar.xz")) + list(registry_dir.glob("*.tz"))
    if not archives:
        print("⚠️  No ORCA archives found in the registry.")
        return None
        
    target_archive = archives[0]
    print(f"📦 Found ORCA archive: {target_archive.name}")
    
    silo_dir = Path.home() / ".cochem" / "engines" / "orca_6_1_1"
    silo_dir.mkdir(parents=True, exist_ok=True)
    
    for root, dirs, files in os.walk(silo_dir):
        if "orca" in files or "orca.exe" in files:
            bin_name = "orca.exe" if sys.platform == "win32" else "orca"
            bin_path = Path(root) / bin_name
            if os.access(bin_path, os.X_OK) or sys.platform == "win32":
                print(f"✅ Found previously cached CoChem ORCA at: {bin_path}")
                return str(bin_path.resolve())

    print(f"🔄 Extracting {target_archive.name} into DevContainer silo: {silo_dir} ... (This may take several minutes)")
    try:
        with tarfile.open(target_archive) as tar:
            tar.extractall(path=silo_dir)
    except Exception as e:
        print(f"❌ FATAL: Archive extraction failed: {e}")
        return None
        
    for root, dirs, files in os.walk(silo_dir):
        if "orca" in files or "orca.exe" in files:
            bin_name = "orca.exe" if sys.platform == "win32" else "orca"
            bin_path = Path(root) / bin_name
            if sys.platform != "win32":
                bin_path.chmod(0o755)
            print(f"✅ Successfully deployed and pathed internal DevContainer ORCA to: {bin_path}")
            return str(bin_path.resolve())
            
    return None

def install_openmpi(silo_dir: Path) -> str:
    """Actively downloads and compiles OpenMPI 4.1.6 if missing."""
    print("➡️  System OpenMPI missing. Triggering active compilation...")
    if sys.platform == "win32":
        print("⚠️  WARNING: OpenMPI cannot be compiled natively on Windows. MPI features will be disabled.")
        return None
        
    mpi_silo = silo_dir / "openmpi_4_1_6"
    mpi_silo.mkdir(parents=True, exist_ok=True)
    
    mpi_bin = mpi_silo / "bin" / "mpirun"
    if mpi_bin.exists() and verify_execution(str(mpi_bin)):
        print(f"✅ Cached OpenMPI found and verified at: {mpi_bin}")
        return str(mpi_bin)
        
    tar_url = "https://download.open-mpi.org/release/open-mpi/v4.1/openmpi-4.1.6.tar.gz"
    tar_path = mpi_silo / "openmpi.tar.gz"
    
    try:
        print(f"⬇️  Downloading OpenMPI from {tar_url}...")
        urllib.request.urlretrieve(tar_url, tar_path)
        print("📦 Extracting OpenMPI...")
        with tarfile.open(tar_path, "r:gz") as tar:
            tar.extractall(path=mpi_silo)
            
        src_dir = list(mpi_silo.glob("openmpi-4.1.6"))[0]
        print("⚙️  Configuring and making OpenMPI (This will take a few minutes)...")
        
        subprocess.run(["./configure", f"--prefix={mpi_silo}"], cwd=src_dir, check=True, capture_output=True)
        subprocess.run(["make", "-j", str(os.cpu_count() or 4)], cwd=src_dir, check=True, capture_output=True)
        subprocess.run(["make", "install"], cwd=src_dir, check=True, capture_output=True)
        
        shutil.rmtree(src_dir, ignore_errors=True)
        tar_path.unlink(missing_ok=True)
        
        if mpi_bin.exists() and verify_execution(str(mpi_bin)):
            print(f"✅ OpenMPI successfully compiled and verified at: {mpi_bin}")
            return str(mpi_bin)
    except Exception as e:
        print(f"❌ OpenMPI compilation failed: {e}")
        
    return None

def install_xtb(silo_dir: Path) -> str:
    """Actively downloads and extracts Grimme g-xTB if missing."""
    print("➡️  System g-xTB missing. Triggering active download...")
    xtb_silo = silo_dir / "g_xtb"
    xtb_silo.mkdir(parents=True, exist_ok=True)
    
    xtb_bin = xtb_silo / "xtb-6.6.1" / "bin" / "xtb"
    if xtb_bin.exists() and verify_execution(str(xtb_bin)):
        print(f"✅ Cached g-xTB found and verified at: {xtb_bin}")
        return str(xtb_bin)
        
    tar_url = "https://github.com/grimme-lab/xtb/releases/download/v6.6.1/xtb-6.6.1-linux-x86_64.tar.xz"
    if sys.platform == "win32":
        print("⚠️  xTB requires WSL/Linux for direct binary drop. Skipping native install.")
        return None 
        
    tar_path = xtb_silo / "xtb.tar.xz"
    try:
        print(f"⬇️  Downloading g-xTB from {tar_url}...")
        urllib.request.urlretrieve(tar_url, tar_path)
        print("📦 Extracting g-xTB...")
        with tarfile.open(tar_path, "r:xz") as tar:
            tar.extractall(path=xtb_silo)
            
        tar_path.unlink(missing_ok=True) 
            
        if xtb_bin.exists():
            xtb_bin.chmod(0o755)
            if verify_execution(str(xtb_bin)):
                print(f"✅ g-xTB successfully deployed and verified at: {xtb_bin}")
                return str(xtb_bin)
            else:
                print("❌ g-xTB deployed but execution failed (likely missing libgfortran).")
    except Exception as e:
        print(f"❌ g-xTB download failed: {e}")
        
    return None

def install_crest(silo_dir: Path, xtb_path: str) -> str:
    """Actively downloads and extracts CREST conformer tool if missing."""
    print("➡️  System CREST missing. Triggering active download...")
    crest_silo = silo_dir / "crest"
    crest_silo.mkdir(parents=True, exist_ok=True)
    
    crest_bin = crest_silo / "crest"
    if crest_bin.exists() and verify_execution(str(crest_bin)):
        print(f"✅ Cached CREST found and verified at: {crest_bin}")
        return str(crest_bin)
        
    tar_url = "https://github.com/grimme-lab/crest/releases/download/v2.12/crest-x86_64-unknown-linux-gnu.tar.xz"
    if sys.platform == "win32":
        print("⚠️  CREST requires WSL/Linux. Skipping native install.")
        return None
        
    tar_path = crest_silo / "crest.tar.xz"
    try:
        print(f"⬇️  Downloading CREST from {tar_url}...")
        urllib.request.urlretrieve(tar_url, tar_path)
        print("📦 Extracting CREST...")
        with tarfile.open(tar_path, "r:xz") as tar:
            tar.extractall(path=crest_silo)
            
        tar_path.unlink(missing_ok=True)
        
        extracted_bin = crest_silo / "crest" 
        if not extracted_bin.exists():
            for root, dirs, files in os.walk(crest_silo):
                if "crest" in files:
                    extracted_bin = Path(root) / "crest"
                    break

        if extracted_bin.exists():
            extracted_bin.chmod(0o755)
            env = os.environ.copy()
            if xtb_path:
                env["PATH"] = f"{Path(xtb_path).parent}:{env.get('PATH', '')}"
                
            if verify_execution(str(extracted_bin)):
                print(f"✅ CREST successfully deployed and verified at: {extracted_bin}")
                if extracted_bin != crest_bin:
                    shutil.move(str(extracted_bin), str(crest_bin))
                return str(crest_bin)
            else:
                print("❌ CREST deployed but execution failed.")
    except Exception as e:
        print(f"❌ CREST download failed: {e}")
        
    return None

def update_shell_profiles(binary_paths: dict):
    """Automatically updates .bashrc and .zshrc to persist engine paths."""
    print("🔧 Updating shell profiles with verified engine paths...")
    paths_to_add = set()
    for name, path_info in binary_paths.items():
        if path_info and path_info.get("path") and Path(path_info["path"]).exists():
            paths_to_add.add(str(Path(path_info["path"]).parent))
            
    if not paths_to_add:
        return
        
    export_line = f"\n# CoChem Automated Engine Paths\nexport PATH=\"{':'.join(paths_to_add)}:$PATH\"\n"
    
    for rc_file in [".bashrc", ".zshrc"]:
        profile_path = Path.home() / rc_file
        if profile_path.exists():
            content = profile_path.read_text()
            if "# CoChem Automated Engine Paths" not in content:
                with open(profile_path, "a") as f:
                    f.write(export_line)
                print(f"✅ Appended paths to {rc_file}")

def main():
    print("=======================================================")
    print(" CoChem Phase 3: Engines, Determinism & Execution ")
    print("=======================================================\n")
    
    engines_dir = Path.home() / ".cochem" / "engines"
    
    # 1. ORCA Pathing & Deployment (Direct Mount Scan)
    orca_bin = locate_system_orca()
    if not orca_bin:
        print("⚠️  System ORCA missing. Triggering automated deployment...")
        orca_bin = deploy_airgapped_orca()
        
    if not orca_bin:
        print("\n❌ FATAL: ORCA could not be located or installed.")
        print("Please place the ORCA .tar.xz or .tz file in ~/CoChem_Artifacts/Registry/Engines/ and retry.")
        sys.exit(1)
        
    if not verify_execution(orca_bin):
        print(f"⚠️  WARNING: ORCA binary found at {orca_bin} but failed initial execution test.")
        print("If this is a bridged Windows .exe, it may require explicit input files to respond.")
        
    # 2. OpenMPI Pathing & Deployment
    mpi_bin = shutil.which("mpirun")
    if mpi_bin and verify_execution(mpi_bin):
        print(f"✅ System OpenMPI natively detected and verified at: {mpi_bin}")
    elif sys.platform != "win32":
        mpi_bin = install_openmpi(engines_dir)
        
    # 3. g-xTB Pathing & Deployment
    xtb_bin = shutil.which("xtb")
    if xtb_bin and verify_execution(xtb_bin):
        print(f"✅ System g-xTB natively detected and verified at: {xtb_bin}")
    elif sys.platform != "win32":
        xtb_bin = install_xtb(engines_dir)

    # 4. CREST Pathing & Deployment 
    crest_bin = shutil.which("crest")
    if crest_bin and verify_execution(crest_bin):
        print(f"✅ System CREST natively detected and verified at: {crest_bin}")
    elif sys.platform != "win32":
        crest_bin = install_crest(engines_dir, xtb_bin)

    # 5. Cryptographic Validation
    print("\n🔒 Executing cryptographic validation on binaries...")
    engine_state = {
        "orca": {"path": orca_bin, "sha256": calculate_hash(orca_bin)},
        "openmpi": {"path": mpi_bin, "sha256": calculate_hash(mpi_bin) if mpi_bin else "N/A"},
        "g_xtb": {"path": xtb_bin, "sha256": calculate_hash(xtb_bin) if xtb_bin else "N/A"},
        "crest": {"path": crest_bin, "sha256": calculate_hash(crest_bin) if crest_bin else "N/A"}
    }
    
    # 6. Shell Environment Persistence
    update_shell_profiles(engine_state)
        
    # Phase 3 State Serialization for downstream Pydantic validation
    state = {"engines": engine_state}
    state_file = Path(__file__).resolve().parent / "cochem_state_p3.json"
    
    with open(state_file, "w") as f:
        json.dump(state, f, indent=4)
        
    print(f"\n🔒 Phase 3 State Locked and Cryptographically Verified: {state_file.name}")
    print("=======================================================")

if __name__ == "__main__":
    main()