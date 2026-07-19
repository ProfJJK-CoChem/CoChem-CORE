# **CoChem-CORE 🧪**

**CoChem-CORE** is the master orchestrator and foundational initialization tier for the CoChem ecosystem. It generates isolated micro-silos for dependency management, audits hardware topologies, and safely bridges computational chemistry engines (ORCA, PySCF, MACE) into Jupyter notebook workflows.

## **🚀 Installation and Setup Guide**

Due to the deep Linux-native dependencies of quantum chemistry engines (like OpenMPI and ORCA), CoChem utilizes a Docker/DevContainer methodology to guarantee a reproducible, error-free environment across all operating systems.

Choose your operating system below to begin.

### **Option 1: Windows 11 (VS Code \+ WSL2)**

Windows 11 requires a compatibility layer to run the CoChem Linux-based toolchain. Do **not** attempt to run the engine router natively on Windows CMD or PowerShell.

1. **Install WSL2:** Open PowerShell as Administrator and run wsl \--install. Restart your PC if prompted. Ensure Ubuntu is your default WSL distribution.  
2. **Install Docker Desktop:** Download and install [Docker Desktop](https://www.docker.com/products/docker-desktop/). In its settings, ensure the **WSL2 backend** is enabled.  
3. **Setup VS Code:** \- Install Visual Studio Code.  
   * Install the **Dev Containers** and **WSL** extensions in VS Code.  
4. **Clone & Open:**  
   * Open a WSL terminal (Ubuntu).  
   * Clone the repository: git clone https://github.com/ProfJJK/CoChem-CORE.git  
   * Open the folder in VS Code: code CoChem-CORE  
5. **Launch Container:** VS Code will prompt "Folder contains a Dev Container configuration file." Click **Reopen in Container**.  
6. **Initialize:** Open Stage\_0.0\_Setup.ipynb inside the container and run the master execution cell.

### **Option 2: macOS (Apple Silicon M1/M2/M3 or Intel)**

macOS uses the DevContainer to simulate the required Ubuntu/Mint Linux environment. *Note: For Apple Silicon (M-series) Macs, Docker will utilize Rosetta 2 x86\_64 emulation to support the pre-compiled ORCA binaries.*

1. **Install Docker Desktop:** Download and install [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/). Ensure "Use Rosetta for x86/amd64 emulation on Apple Silicon" is enabled in Docker settings.  
2. **Setup VS Code:**  
   * Install Visual Studio Code.  
   * Install the **Dev Containers** extension.  
3. **Clone & Open:**  
   * Open your Mac Terminal.  
   * Clone the repository: git clone https://github.com/ProfJJK/CoChem-CORE.git  
   * Open the folder in VS Code: code CoChem-CORE  
4. **Launch Container:** Click the blue \>\< icon in the bottom-left corner of VS Code and select **Reopen in Container**.  
5. **Initialize:** Open Stage\_0.0\_Setup.ipynb inside the container and run the master execution cell.

### **Option 3: Linux (Ubuntu / Linux Mint)**

Linux users can either use the DevContainer for a strictly sandboxed experience or run the pipeline natively.

**Native Installation:**

1. Clone the repository: git clone https://github.com/ProfJJK/CoChem-CORE.git  
2. Ensure Python 3.11+ and pip are installed on your system.  
3. Install Jupyter: pip install jupyterlab  
4. Open the directory: cd CoChem-CORE  
5. Launch Jupyter: jupyter lab  
6. Open Stage\_0.0\_Setup.ipynb and run the master execution cell. The orchestrator will autonomously map your native hardware and handle engine isolation in \~/.cochem/.

**DevContainer Installation (Optional):**

Follow the macOS steps above using Docker Engine and the VS Code Dev Containers extension.

### **Option 4: GitHub Codespaces (Cloud Execution)**

If you lack the local hardware (e.g., 16GB+ RAM) to run the ML potentials locally:

1. Navigate to the GitHub repository.  
2. Click the green **Code** button, select the **Codespaces** tab, and click **Create codespace on main**.  
3. Wait for the browser-based VS Code environment to build.  
4. Open Stage\_0.0\_Setup.ipynb and run the master execution cell.

## **Next Steps**

Once Stage\_0.0\_Setup.ipynb successfully executes, it will generate the cochem\_system\_config.json registry. You are now ready to clone downstream CoChem modules (like CoChem-TOPOS or CoChem-TORQ) into your workspace.