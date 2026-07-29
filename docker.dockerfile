# cochem_canvas_target: Dockerfile
# Native NVIDIA CUDA Runtime ensures PyTorch/MACE-OFF23 hardware acceleration
FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04

# Prevent interactive prompts from hanging the build
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

# 1. Install Massive Core Dependencies for CoChem Engines
# Includes OpenMPI dependencies, ORCA C++ bindings, and extraction utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    wget \
    curl \
    git \
    tar \
    xz-utils \
    bzip2 \
    ssh \
    openssh-client \
    openmpi-bin \
    libopenmpi-dev \
    libomp-dev \
    libstdc++6 \
    python3.11 \
    python3.11-dev \
    python3.11-venv \
    python3-pip \
    sudo \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 2. Symlink Python 3.11 as the default system python
RUN ln -sf /usr/bin/python3.11 /usr/bin/python && \
    ln -sf /usr/bin/pip3 /usr/bin/pip

# 3. Provision the non-root 'vscode' user for DevContainer compliance
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m -s /bin/bash $USERNAME \
    && echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME

# 4. Enforce user execution and inject local binary paths
USER $USERNAME

RUN echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc \
    && echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc

WORKDIR /workspaces/CoChem-CORE