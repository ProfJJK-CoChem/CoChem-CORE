#!/usr/bin/env python3
"""
CoChem-CORE: Canonical Registry Schema

Defines the absolute, Pydantic-enforced structural blueprint for the 
CoChem ecosystem's authoritative state file (`cochem_system_config.json`).
By enforcing strict type hints, memory boundaries, and engine paths here, 
we prevent silent degradation or catastrophic node-crashing in HPC/local environments.
"""

import os
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Dict, Optional, Any, Literal

class EngineSpec(BaseModel):
    """Defines the required metadata for any computational engine."""
    path: str
    version: str
    hash: str
    status: str

class HardwareConfig(BaseModel):
    """Profiles the physical constraints of the execution node."""
    model_config = ConfigDict(extra='forbid')

    os_target: str = Field(..., description="Target OS Architecture")
    physical_cpu_cores: int = Field(..., ge=1, description="Number of physical CPU cores")
    logical_cpu_cores: int = Field(..., ge=1, description="Number of logical threads")
    ram_gb: float = Field(..., gt=0.0, description="Total physical RAM in Gigabytes")
    avx512_support: bool = Field(..., description="Boolean flag for AVX-512 vectorization support")
    gpu_profile: str = Field(..., description="VGA/3D Controller hardware string, or 'None'")
    vram_gb: float = Field(default=0.0, ge=0.0, description="Total VRAM available if GPU is present")
    subnormal_precision_trap: bool = Field(..., description="Flag indicating CPU subnormal handling")

class SiloConfig(BaseModel):
    """Paths to isolated micro-environments."""
    core_silo: str
    torq_silo: Optional[str] = None
    gpu_silo: Optional[str] = None

class RoutingPolicy(BaseModel):
    """Resource guarding and MLFF memory limits."""
    cpu_fallback: bool
    max_mlff_batch_size: int = Field(..., ge=1)
    memory_ceiling_gb_per_core: float = Field(..., gt=0.0)

class HPCConfig(BaseModel):
    """Telemetry and cluster-bridge settings."""
    provider: str
    remote_user: Optional[str] = None
    sync_interval_seconds: int = Field(..., ge=5)

class CoChemConfig(BaseModel):
    """
    The Master Blueprint for the CoChem Ecosystem.
    Ensures absolute parity with cochem_system_config.json.
    """
    registry_version: str
    project_root: str
    
    hardware: HardwareConfig
    engines: Dict[str, EngineSpec]
    silos: SiloConfig
    routing: RoutingPolicy
    hpc: HPCConfig
    active_jobs: Dict[str, Any] = Field(default_factory=dict)

    @field_validator('project_root')
    @classmethod
    def validate_absolute_path(cls, v: str) -> str:
        """Ensure the project root is an absolute path to prevent ghost-directory scattering."""
        if not os.path.isabs(v):
            raise ValueError(f"project_root must be an absolute path, got {v}")
        return v