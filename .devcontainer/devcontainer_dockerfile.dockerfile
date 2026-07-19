# Base image matches Linux Mint/Ubuntu architecture expected by ORCA and PySCF
FROM mcr.microsoft.com/devcontainers/miniconda:0-3

# Install underlying HPC requirements for Quantum Engines
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends \
        build-essential \
        libopenmpi-dev \
        openmpi-bin \
        wget \
        tar \
        git \
        pciutils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Pre-install Jupyter ecosystem and standard scientific math stack 
# to the base environment, mapping Python 3.10 for stable C++ bindings
RUN conda install -y python=3.10 jupyterlab ipywidgets psutil \
    && pip install --no-cache-dir aiohttp numpy scipy networkx

# Switch to standard user
USER vscode
WORKDIR /workspace