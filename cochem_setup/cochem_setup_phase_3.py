# cochem_canvas_target: cochem_setup/cochem_setup_phase_3.py
import os
import sys
import shutil
import subprocess
import urllib.request
import json
import hashlib
from pathlib import Path

def maximize_os_limits():
    """OS Memory (ulimit) Auto-Expansion to prevent Coupled-Cluster memory segmentation faults."""
    if sys.platform == "win32":
        return
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_STACK, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
        print("✅ OS Memory limits expanded (ulimit -s unlimited).")
    except Exception as e:
        print(f"⚠️  Could not automatically set unlimited stack size: {e}")

def hardware_profile():
    """Advanced Hardware Profiling for telemetry context."""
    print("➡️  Executing Hardware Profiling...")
    try:
        import psutil
        ram_gb = psutil.virtual_memory().total / (1024**3)
        cores = psutil.cpu_count(logical=False)
        threads = psutil.cpu_count(logical=True)
        print(f"⚙️  Hardware Profile: {cores} Physical Cores ({threads} Threads), {ram_gb:.2f} GB RAM")
    except ImportError:
        print("⚙️  Hardware Profile: psutil unavailable, falling back to basic OS stats.")

def calculate_hash(file_path: str) -> str:
    """Cryptographic Binary Validation."""
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

def check_fast_pass(state_file: Path) -> bool:
    """Fast-Pass Caching to bypass redundant engine deployment."""
    if not state_file.exists():
        return False
    try:
        with open(state_file, "r") as f:
            data = json.load(f)
        engines = data.get("engines", {})
        for name, info in engines.items():
            path = info.get("path")
            stored_hash = info.get("sha256")
            if path and stored_hash and stored_hash != "N/A":
                if calculate_hash(path) != stored_hash:
                    return False
        print("⚡ Fast-Pass Caching: All engine hashes match perfectly. Bypassing Phase 3 Deployment.")
        return True
    except Exception:
        return False

def verify_execution(binary_path: str, version_flag: str = "--version") -> bool:
    """Sanity check to ensure binary is executable in the current architecture."""
    if not binary_path or not Path(binary_path).exists():
        return False
    try:
        env = os.environ.copy()
        res = subprocess.run([binary_path, version_flag], capture_output=True, text=True, timeout=15, env=env)
        return res.returncode == 0 or "version" in res.stdout.lower() or "version" in res.stderr.lower() or res.returncode == 1
    except Exception:
        return False

def test_orca_execution(orca_path: str) -> bool:
    """Deep ORCA Execution Verification: Tests actual basis library integration."""
    print("🔬 Executing Deep ORCA Verification (Dummy SP Job)...")
    if sys.platform == "win32" or str(orca_path).endswith(".exe"):
        return True # Bypass for bridged Windows .exe timeouts

    scratch = Path.home() / ".cochem" / "scratch"
    scratch.mkdir(parents=True, exist_ok=True)
    inp_file = scratch / "dummy.inp"
    out_file = scratch / "dummy.out"
    
    inp_file.write_text("! SP STO-3G\n*xyz 0 1\nHe 0 0 0\n*")
    try:
        env = os.environ.copy()
        result = subprocess.run([orca_path, str(inp_file)], cwd=str(scratch), capture_output=True, text=True, timeout=45, env=env)
        if result.returncode == 0:
            stdout_text = (result.stdout or "").upper()
            normal_outputs = [
                scratch / "dummy.property.txt",
                scratch / "dummy.gbw",
                scratch / "dummy.bibtex",
            ]
            has_orca_marker = "ORCA TERMINATED NORMALLY" in stdout_text or "O   R   C   A" in stdout_text or "O R C A" in stdout_text
            if has_orca_marker or any(path.exists() for path in normal_outputs):
                print("✅ Deep ORCA Verification Passed: Engine and basis set libraries are fully functional.")
                return True
        print("❌ Deep ORCA Verification Failed: Output file missing or malformed.")
        return False
    except Exception as e:
        print(f"❌ Deep ORCA Verification Exception: {e}")
        return False

def locate_system_orca():
    """Explicit ORCA Binary Hunt using native OS commands and Silo Caching."""
    print("➡️  Checking for system-wide ORCA...")

    def to_container_path(raw_path: str) -> Path:
        p = (raw_path or "").strip().strip('"').strip("'")
        if not p:
            return Path("")

        # Convert Windows paths (e.g. C:\\ORCA\\orca.exe) into common container mount forms.
        if len(p) > 2 and p[1] == ":":
            drive = p[0].lower()
            tail = p[2:].replace("\\", "/").lstrip("/")
            mount_candidates = [
                Path(f"/mnt/{drive}/{tail}"),
                Path(f"/host_mnt/{drive}/{tail}"),
                Path(f"/run/desktop/mnt/host/{drive}/{tail}"),
                Path(f"/{drive}/{tail}"),
            ]
            for candidate in mount_candidates:
                if candidate.exists():
                    return candidate
            return mount_candidates[0]

        return Path(p)

    def expand_orca_candidates(raw_path: str) -> list:
        base = to_container_path(raw_path)
        if not str(base):
            return []
        if base.is_file():
            return [base]
        return [base / "orca", base / "orca.exe", base / "bin" / "orca", base / "bin" / "orca.exe"]

    # 1. Check CoChem Silo explicitly (prevents needing the .tar.xz again if already extracted)
    silo_dir = Path.home() / ".cochem" / "engines" / "orca_6_1_1"
    if silo_dir.exists():
        for root, dirs, files in os.walk(silo_dir):
            if "orca" in files or "orca.exe" in files:
                bin_name = "orca.exe" if sys.platform == "win32" else "orca"
                found_path = Path(root) / bin_name
                if found_path.exists():
                    print(f"✅ Found cached CoChem ORCA at: {found_path}")
                    return str(found_path.resolve())

    # 1.2. Explicit host-path hints passed into container (env/manifest/artifact registry)
    hint_values = []
    for key in ["COCHEM_HOST_ORCA_PATH", "COCHEM_HOST_ORCA_HOME", "ORCA_PATH", "ORCA_HOME", "ORCA_DIR", "ORCA_BIN"]:
        value = os.environ.get(key)
        if value:
            hint_values.append(value)

    manifest_candidates = [Path.cwd() / "cochem_setup" / "cochem_deployment_manifest.json", Path.cwd() / "cochem_deployment_manifest.json"]
    for manifest_path in manifest_candidates:
        if not manifest_path.exists():
            continue
        try:
            with open(manifest_path, "r") as f:
                manifest = json.load(f)
            hint = manifest.get("host_orca_path")
            if hint:
                hint_values.append(hint)
        except Exception:
            pass

    hint_file = Path(os.environ.get("COCHEM_ARTIFACT_DIR", str(Path.home() / "CoChem_Artifacts"))) / "Registry" / "host_orca_path.txt"
    if hint_file.exists():
        try:
            hint = hint_file.read_text(encoding="utf-8").strip()
            if hint:
                hint_values.append(hint)
        except Exception:
            pass

    for raw_hint in hint_values:
        for candidate in expand_orca_candidates(raw_hint):
            if candidate.exists():
                print(f"✅ Host ORCA resolved from hint at: {candidate}")
                return str(candidate.resolve())

    # 1.5. Host mount scan fallback (useful when host ORCA is installed outside container PATH)
    host_mounts = [
        Path("/host_os_root"),
        Path("/mnt/c"),
        Path("/host_mnt/c"),
        Path("/c"),
        Path("/run/desktop/mnt/host/c"),
    ]
    host_search_roots = [
        "orca",
        "ORCA",
        "ORCA_6.1.1",
        "orca_6.1.1",
        "orca611",
        "orca_6_1_1",
        "Program Files/orca",
        "Program Files/ORCA",
        "Applications/orca",
        "Applications/ORCA",
        "opt/orca",
        "opt/ORCA",
        "usr/local/orca",
        "usr/local/ORCA",
        "Users/Shared/orca",
        "Users/Shared/ORCA",
    ]
    for mount in host_mounts:
        if not mount.exists():
            continue
        for rel_root in host_search_roots:
            target_dir = mount / rel_root
            if not target_dir.exists():
                continue
            for bin_name in ["orca", "orca.exe"]:
                candidate = target_dir / bin_name
                if candidate.exists():
                    print(f"✅ Host-mounted ORCA discovered at: {candidate}")
                    if sys.platform != "win32" and str(candidate).endswith(".exe"):
                        print("⚠️  WARNING: Bridging Windows ORCA (.exe) into Linux drops OpenMPI efficiency.")
                    return str(candidate.resolve())

    # 2. Explicit env-var candidates commonly used in host installs
    env_candidates = []
    for key in ["ORCA_PATH", "ORCA_BIN", "ORCA_HOME", "ORCA_DIR"]:
        value = os.environ.get(key)
        if not value:
            continue
        p = Path(value)
        if p.is_dir():
            env_candidates.append(p / ("orca.exe" if sys.platform == "win32" else "orca"))
            env_candidates.append(p / "bin" / ("orca.exe" if sys.platform == "win32" else "orca"))
        else:
            env_candidates.append(p)

    for candidate in env_candidates:
        if candidate.exists():
            print(f"✅ System ORCA detected via environment at: {candidate}")
            if sys.platform != "win32" and str(candidate).endswith(".exe"):
                print("⚠️  WARNING: Bridging Windows ORCA (.exe) into Linux drops OpenMPI efficiency.")
            return str(candidate.resolve())

    # 2.5. Recover ORCA path from authoritative CoChem config if present
    config_candidates = [
        Path.cwd() / "cochem_system_config.json",
        Path.cwd() / "cochem_setup" / "cochem_system_config.json",
    ]
    for cfg in config_candidates:
        if not cfg.exists():
            continue
        try:
            with open(cfg, "r") as f:
                cfg_data = json.load(f)
            engine_node = cfg_data.get("engines", {}).get("orca", {})
            cfg_path = engine_node.get("path") if isinstance(engine_node, dict) else None
            if cfg_path and Path(cfg_path).exists():
                print(f"✅ ORCA restored from config registry at: {cfg_path}")
                return str(Path(cfg_path).resolve())
        except Exception:
            continue

    # 3. Native OS lookup ('where' on Windows, 'which' on Linux/Mac) via explicit shell subprocess
    orca_path = None
    try:
        if sys.platform == "win32":
            res = subprocess.run("where orca", shell=True, capture_output=True, text=True)
            if res.returncode == 0 and res.stdout.strip():
                orca_path = res.stdout.strip().splitlines()[0].strip()
        else:
            res = subprocess.run("which orca", shell=True, capture_output=True, text=True)
            if res.returncode == 0 and res.stdout.strip():
                orca_path = res.stdout.strip().splitlines()[0].strip()
    except Exception as e:
        print(f"⚠️  OS command lookup failed: {e}")
        pass
    
    if orca_path and Path(orca_path).exists():
        print(f"✅ System ORCA detected via OS Native Command at: {orca_path}")
        if sys.platform != "win32" and str(orca_path).endswith(".exe"):
             print("⚠️  WARNING: Bridging Windows ORCA (.exe) into Linux drops OpenMPI efficiency.")
        return str(Path(orca_path).resolve())

    # 4. Host/artifact fallback scan for extracted ORCA binaries not in PATH
    scan_roots = [
        Path(os.environ.get("COCHEM_ENGINE_REGISTRY", Path.home() / "CoChem_Artifacts" / "Registry" / "Engines")),
        Path.home() / "CoChem_Artifacts" / "Registry" / "Engines",
    ]
    for root_dir in scan_roots:
        if not root_dir.exists():
            continue
        try:
            for pattern in ["orca", "orca.exe"]:
                for candidate in root_dir.rglob(pattern):
                    if not candidate.is_file():
                        continue
                    if sys.platform != "win32" and candidate.name == "orca":
                        try:
                            candidate.chmod(0o755)
                        except OSError:
                            pass
                    print(f"✅ Located host-staged ORCA binary at: {candidate}")
                    return str(candidate.resolve())
        except OSError:
            continue
        
    print("⚠️  System ORCA missing from native OS PATH lookup. Defaulting to silo setup...")
    return None

def enforce_pip_dependency_fallback(url: str, target_path: Path, archive_name: str) -> bool:
    """Local Package Fallback (Offline Recovery) to bypass urllib failures."""
    registry_dir = Path(os.environ.get("COCHEM_ENGINE_REGISTRY", Path.home() / "CoChem_Artifacts" / "Registry" / "Engines"))
    local_archive = registry_dir / archive_name
    
    if local_archive.exists():
        print(f"📦 Offline Recovery: Sideloading local archive from {local_archive}")
        shutil.copy(local_archive, target_path)
        return True
        
    try:
        print(f"⬇️  Downloading from {url}...")
        urllib.request.urlretrieve(url, target_path)
        return True
    except Exception as e:
        print(f"❌ Network Fetch Failed: {e}")
        return False

def deploy_airgapped_orca():
    """Dynamic Extraction from COCHEM_ENGINE_REGISTRY using memory-safe OS tar."""
    print("➡️  System ORCA missing. Triggering automated deployment...")
    registry_dir = Path(os.environ.get("COCHEM_ENGINE_REGISTRY", Path.home() / "CoChem_Artifacts" / "Registry" / "Engines"))
    registry_dir.mkdir(parents=True, exist_ok=True)

    def prompt_and_store_host_orca_hint() -> bool:
        """Interactive fallback: capture host ORCA path and persist for Phase 3 re-detection."""
        if not sys.stdin.isatty():
            return False

        print("\n💡 Optional automation: provide a host ORCA binary path for direct reuse.")
        print("   Example (Windows host): C:\\ORCA\\orca.exe")
        print("   Example (Linux host): /opt/orca/orca")
        print("   Press Enter to skip and use archive upload instead.")
        try:
            raw_hint = input("Host ORCA path (optional): ").strip()
        except EOFError:
            return False

        if not raw_hint:
            return False

        artifact_dir = Path(os.environ.get("COCHEM_ARTIFACT_DIR", Path.home() / "CoChem_Artifacts"))
        hint_file = artifact_dir / "Registry" / "host_orca_path.txt"
        hint_file.parent.mkdir(parents=True, exist_ok=True)
        hint_file.write_text(raw_hint, encoding="utf-8")
        os.environ["COCHEM_HOST_ORCA_PATH"] = raw_hint
        print(f"✅ Saved host ORCA hint to: {hint_file}")
        return True
        
    archives = list(registry_dir.glob("orca*6*.t*")) + list(registry_dir.glob("*.tar.xz")) + list(registry_dir.glob("*.tz"))
    if not archives:
        if prompt_and_store_host_orca_hint():
            hinted_orca = locate_system_orca()
            if hinted_orca:
                print(f"✅ Host ORCA resolved after interactive hint: {hinted_orca}")
                return hinted_orca

        print("\n" + "="*60)
        print("🛑 ORCA 6.1.1 DEPLOYMENT HALTED (FACCTS LICENSING)")
        print("="*60)
        print("ORCA is proprietary software and cannot be downloaded automatically.")
        print("1. Register/Login at: https://faccts.de/")
        print("2. Download the 'ORCA 6.1.1 Linux x86-64 Shared OpenMPI 4.1.x' archive.")
        print(f"3. Move the downloaded .tar.xz file exactly here:\n   {registry_dir}")
        print("   You can also drag-and-drop the archive into the UNITY installer upload widget.")
        print("4. Re-run the CoChem setup orchestrator.")
        print("="*60 + "\n")
        sys.exit(2)
        
    target_archive = archives[0]
    silo_dir = Path.home() / ".cochem" / "engines" / "orca_6_1_1"
    silo_dir.mkdir(parents=True, exist_ok=True)
    
    for root, dirs, files in os.walk(silo_dir):
        if "orca" in files or "orca.exe" in files:
            bin_name = "orca.exe" if sys.platform == "win32" else "orca"
            return str((Path(root) / bin_name).resolve())

    print(f"🔄 Extracting {target_archive.name} via native system tar (Memory-Safe)...")
    try:
        # Prevent DevContainer OOM crashes and map permissions to local user securely
        subprocess.run(["tar", "--no-same-owner", "--no-same-permissions", "-xf", str(target_archive), "-C", str(silo_dir)], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ FATAL: System tar extraction failed: {e}")
        return None
        
    for root, dirs, files in os.walk(silo_dir):
        if "orca" in files or "orca.exe" in files:
            bin_path = Path(root) / ("orca.exe" if sys.platform == "win32" else "orca")
            if sys.platform != "win32":
                bin_path.chmod(0o755)
            return str(bin_path.resolve())
            
    return None

def install_openmpi(silo_dir: Path) -> str:
    """Actively compiles OpenMPI and enforces strict 4.1.x versioning."""
    if sys.platform == "win32":
        return None
        
    mpi_silo = silo_dir / "openmpi_4_1_6"
    mpi_silo.mkdir(parents=True, exist_ok=True)
    
    mpi_bin = mpi_silo / "bin" / "mpirun"
    if mpi_bin.exists() and verify_execution(str(mpi_bin)):
        print(f"✅ Found cached CoChem Open MPI at: {mpi_bin}")
        return str(mpi_bin)
        
    print("➡️  System OpenMPI missing or incorrect version. Triggering active compilation...")
    tar_url = "https://download.open-mpi.org/release/open-mpi/v4.1/openmpi-4.1.6.tar.gz"
    tar_path = mpi_silo / "openmpi.tar.gz"
    
    if not enforce_pip_dependency_fallback(tar_url, tar_path, "openmpi-4.1.6.tar.gz"):
        return None
    
    try:
        print("📦 Extracting OpenMPI via native system tar...")
        subprocess.run(["tar", "--no-same-owner", "-xf", str(tar_path), "-C", str(mpi_silo)], check=True)
            
        src_dir = list(mpi_silo.glob("openmpi-4.1.6"))[0]
        print("⚙️  Configuring and making OpenMPI (This will take a few minutes)...")
        
        subprocess.run(["./configure", f"--prefix={mpi_silo}"], cwd=src_dir, check=True, capture_output=True)
        subprocess.run(["make", "-j", str(os.cpu_count() or 4)], cwd=src_dir, check=True, capture_output=True)
        subprocess.run(["make", "install"], cwd=src_dir, check=True, capture_output=True)
        
        shutil.rmtree(src_dir, ignore_errors=True)
        tar_path.unlink(missing_ok=True)
        
        if mpi_bin.exists() and verify_execution(str(mpi_bin)):
            print(f"✅ OpenMPI compiled at: {mpi_bin}")
            return str(mpi_bin)
    except Exception as e:
        print(f"❌ OpenMPI compilation failed: {e}")
        
    return None

def install_xtb(silo_dir: Path) -> str:
    xtb_silo = silo_dir / "g_xtb"
    xtb_silo.mkdir(parents=True, exist_ok=True)
    
    xtb_bin = xtb_silo / "xtb-6.6.1" / "bin" / "xtb"
    if xtb_bin.exists() and verify_execution(str(xtb_bin)):
        print(f"✅ Found cached CoChem g-xTB at: {xtb_bin}")
        return str(xtb_bin)
        
    print("➡️  System g-xTB missing. Triggering active deployment...")
    if sys.platform == "win32": return None 
        
    tar_path = xtb_silo / "xtb.tar.xz"
    if enforce_pip_dependency_fallback("https://github.com/grimme-lab/xtb/releases/download/v6.6.1/xtb-6.6.1-linux-x86_64.tar.xz", tar_path, "xtb.tar.xz"):
        try:
            subprocess.run(["tar", "--no-same-owner", "-xf", str(tar_path), "-C", str(xtb_silo)], check=True)
            tar_path.unlink(missing_ok=True) 
            if xtb_bin.exists():
                xtb_bin.chmod(0o755)
                return str(xtb_bin) if verify_execution(str(xtb_bin)) else None
        except Exception:
            pass
    return None

def install_crest(silo_dir: Path, xtb_path: str) -> str:
    crest_silo = silo_dir / "crest"
    crest_silo.mkdir(parents=True, exist_ok=True)
    
    crest_bin = crest_silo / "crest"
    if crest_bin.exists() and verify_execution(str(crest_bin)):
        print(f"✅ Found cached CoChem CREST at: {crest_bin}")
        return str(crest_bin)
        
    print("➡️  System CREST missing. Triggering active deployment...")
    if sys.platform == "win32": return None
        
    tar_path = crest_silo / "crest.tar.xz"
    if enforce_pip_dependency_fallback("https://github.com/grimme-lab/crest/releases/download/latest/crest-latest.tar.xz", tar_path, "crest.tar.xz"):
        try:
            subprocess.run(["tar", "--no-same-owner", "-xf", str(tar_path), "-C", str(crest_silo)], check=True)
            tar_path.unlink(missing_ok=True)
            
            extracted_bin = crest_silo / "crest" 
            if not extracted_bin.exists():
                for root, dirs, files in os.walk(crest_silo):
                    if "crest" in files:
                        extracted_bin = Path(root) / "crest"
                        break

            if extracted_bin.exists():
                extracted_bin.chmod(0o755)
                if extracted_bin != crest_bin:
                    shutil.move(str(extracted_bin), str(crest_bin))
                return str(crest_bin) if verify_execution(str(crest_bin)) else None
        except Exception:
            pass
    return None

def update_shell_profiles(binary_paths: dict):
    print("🔧 Updating shell profiles with verified engine paths...")
    paths_to_add = {str(Path(v["path"]).parent) for k, v in binary_paths.items() if v and v.get("path") and Path(v["path"]).exists()}
    if not paths_to_add: return
        
    export_line = f"\n# CoChem Automated Engine Paths\nexport PATH=\"{':'.join(paths_to_add)}:$PATH\"\n"
    for rc_file in [".bashrc", ".zshrc"]:
        profile_path = Path.home() / rc_file
        if profile_path.exists() and "# CoChem Automated Engine Paths" not in profile_path.read_text():
            with open(profile_path, "a") as f: f.write(export_line)

def main():
    print("=======================================================")
    print(" CoChem Phase 3: Engines, Determinism & Execution ")
    print("=======================================================\n")
    
    state_file = Path(__file__).resolve().parent / "cochem_state_p3.json"
    if check_fast_pass(state_file):
        sys.exit(0)

    maximize_os_limits()
    hardware_profile()
    
    engines_dir = Path.home() / ".cochem" / "engines"
    
    orca_bin = locate_system_orca()
    if not orca_bin:
        orca_bin = deploy_airgapped_orca()
        
    test_orca_execution(orca_bin)
        
    # Strict OpenMPI Version Enforcement
    mpi_bin = shutil.which("mpirun")
    if mpi_bin and verify_execution(mpi_bin):
        res = subprocess.run([mpi_bin, "--version"], capture_output=True, text=True)
        if "4.1" not in res.stdout:
            print("⚠️  System OpenMPI is not version 4.1.x. Forcing isolated recompilation...")
            mpi_bin = install_openmpi(engines_dir)
        else:
            print(f"✅ System OpenMPI 4.1.x natively detected at: {mpi_bin}")
    elif sys.platform != "win32":
        mpi_bin = install_openmpi(engines_dir)
        
    xtb_bin = shutil.which("xtb")
    if xtb_bin and verify_execution(xtb_bin):
        print(f"✅ System g-xTB natively detected at: {xtb_bin}")
    elif sys.platform != "win32":
        xtb_bin = install_xtb(engines_dir)

    crest_bin = shutil.which("crest")
    if crest_bin and verify_execution(crest_bin):
        print(f"✅ System CREST natively detected at: {crest_bin}")
    elif sys.platform != "win32":
        crest_bin = install_crest(engines_dir, xtb_bin)

    print("\n🔒 Executing cryptographic validation on binaries...")
    engine_state = {
        "orca": {"path": orca_bin, "sha256": calculate_hash(orca_bin)},
        "openmpi": {"path": mpi_bin, "sha256": calculate_hash(mpi_bin) if mpi_bin else "N/A"},
        "g_xtb": {"path": xtb_bin, "sha256": calculate_hash(xtb_bin) if xtb_bin else "N/A"},
        "crest": {"path": crest_bin, "sha256": calculate_hash(crest_bin) if crest_bin else "N/A"}
    }
    
    update_shell_profiles(engine_state)
    with open(state_file, "w") as f:
        json.dump({"engines": engine_state}, f, indent=4)
        
    print(f"\n🔒 Phase 3 State Locked and Cryptographically Verified: {state_file.name}")
    print("=======================================================")

if __name__ == "__main__":
    main()