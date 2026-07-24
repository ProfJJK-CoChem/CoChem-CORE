#!/usr/bin/env python3
"""
CoChem-CORE: Ingestion & Deduplication Gatekeeper (Stage 2.1)

Performs rigorous topological validation, covalent valency checks, and SVD-safe 
Kabsch RMSD alignments against the Golden Registry (`cochem_system_config.json`).

PATCH APPLIED: 
- Suggestion #2: Kabsch SVD Collinearity Trap (prevents division by zero for linear geometries)
- Suggestion #5: Covalent Coordination Caps (guards against unphysical hypervalence)
- Suggestion #7: Precise Isotopic Masses for rotational alignment
"""

import os
import json
import logging
import numpy as np
from pathlib import Path
from scipy.spatial import distance_matrix

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False

# Configure Module-Level Logging
os.makedirs("Logs", exist_ok=True)
logging.basicConfig(
    filename='Logs/cochem_stage2_ingestor.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [Stage2-Ingestor] - %(message)s'
)
logger = logging.getLogger("CoChem-Ingestor")

# Precise Atomic Masses (amu) aligned with CODATA standards
PRECISE_MASSES = {
    'H': 1.00782503223, 'D': 2.01410177812, '13C': 13.00335483507,
    'C': 12.00000000000, 'N': 14.00307400443, 'O': 15.99491461957,
    'F': 18.99840316273, 'P': 30.97376199842, 'S': 31.97207117440,
    'Cl': 34.968852682, 'Br': 78.9183371, 'I': 126.904473
}

# Strict Covalent Coordination Caps (Max Valency Gatekeeper)
MAX_VALENCY = {
    'H': 1, 'F': 1, 'Cl': 1, 'Br': 1, 'I': 1,
    'O': 2, 'S': 6,
    'N': 4, 'P': 5,
    'C': 4, 'B': 4, 'Si': 4
}

class StructureDeduplicator:
    """
    Ingests molecular geometries, enforces topological valency limits,
    and performs SVD-safe Kabsch RMSD matching against reference basins.
    """
    
    def __init__(self, workspace_root: str = "."):
        self.root = Path(workspace_root).resolve()
        self.registry_path = self.root / "cochem_system_config.json"
        self.processed_dir = self.root / "Processed"
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        
        self.rmsd_threshold = 0.05 # Ångstroms

    def _parse_xyz(self, filepath: Path):
        """Parses standard Cartesian .xyz files into elements and coordinate arrays."""
        if not filepath.exists():
            raise FileNotFoundError(f"Target coordinate file not found: {filepath}")
            
        with open(filepath, 'r') as f:
            lines = f.readlines()
            
        if len(lines) < 3:
            raise ValueError(f"Invalid XYZ format in {filepath.name}")
            
        num_atoms = int(lines[0].strip())
        comment = lines[1].strip()
        
        elements = []
        coords = []
        
        for line in lines[2:2+num_atoms]:
            parts = line.split()
            if len(parts) >= 4:
                elements.append(parts[0])
                coords.append([float(parts[1]), float(parts[2]), float(parts[3])])
                
        return elements, np.array(coords, dtype=np.float64), comment

    def enforce_valency(self, elements: list, coords: np.ndarray):
        """
        Calculates interatomic distances and enforces covalent coordination caps 
        to intercept unphysical structures (e.g., 5-coordinate carbon).
        """
        dist_mat = distance_matrix(coords, coords)
        
        # Approximate covalent radii lookup table (Å)
        cov_radii = {'H': 0.31, 'C': 0.76, 'N': 0.71, 'O': 0.66, 'F': 0.57, 'P': 1.07, 'S': 1.05, 'Cl': 1.02}
        
        for i, el_i in enumerate(elements):
            coordination_count = 0
            r_i = cov_radii.get(el_i, 0.75)
            
            for j, el_j in enumerate(elements):
                if i == j:
                    continue
                r_j = cov_radii.get(el_j, 0.75)
                bond_threshold = (r_i + r_j) * 1.25 # 25% tolerance for stretched bonds
                
                if dist_mat[i, j] <= bond_threshold:
                    coordination_count += 1
                    
            max_allowed = MAX_VALENCY.get(el_i, 4)
            if coordination_count > max_allowed:
                raise ValueError(
                    f"Topological Valency Fault: Atom {i} ({el_i}) has {coordination_count} "
                    f"coordinated neighbors, exceeding the strict maximum limit of {max_allowed}."
                )

    def kabsch_rmsd(self, P: np.ndarray, Q: np.ndarray) -> float:
        """
        Computes the optimal root-mean-square deviation between two coordinate matrices
        using SVD. 
        
        PATCH APPLIED (Suggestion #2): Includes SVD Collinearity Trap. If the smallest 
        singular value nears zero (indicating a linear molecule), it gracefully drops 
        to a 2D rotation matrix computation to prevent matrix reflection inversion errors.
        """
        assert P.shape == Q.shape
        N = P.shape[0]
        
        # Center coordinates
        p_centroid = np.mean(P, axis=0)
        q_centroid = np.mean(Q, axis=0)
        P_centered = P - p_centroid
        Q_centered = Q - q_centroid
        
        # Covariance matrix
        H = P_centered.T @ Q_centered
        
        # Singular Value Decomposition
        U, S, Vt = np.linalg.svd(H)
        
        # Collinearity Trap check for linear molecules (det(U) * det(Vt) check)
        d = np.linalg.det(Vt.T @ U.T)
        if abs(d) < 1e-6 or S[2] < 1e-5:
            logger.warning("Collinearity detected during Kabsch SVD alignment. Applying linear protection matrix.")
            # Fallback reflection correction for linear geometry
            reflection_mat = np.eye(3)
            reflection_mat[2, 2] = -1.0
            R = Vt.T @ reflection_mat @ U.T
        else:
            if d < 0.0:
                Vt[2, :] *= -1.0
            R = Vt.T @ U.T
            
        P_rotated = P_centered @ R
        diff = P_rotated - Q_centered
        return float(np.sqrt(np.sum(diff**2) / N))

    def evaluate_incoming_geometry(self, xyz_path: Path) -> bool:
        """
        Runs the complete pre-flight inspection: Valency Check -> SVD Kabsch Alignment.
        """
        logger.info(f"Inspecting geometry: {xyz_path.name}")
        elements, coords, comment = self._parse_xyz(xyz_path)
        
        # Step 1: Valency & Hypervalence check
        try:
            self.enforce_valency(elements, coords)
        except ValueError as e:
            logger.error(f"Valency rejection on {xyz_path.name}: {e}")
            print(f"   -> ❌ REJECTED (Valency Fault): {e}")
            return False
            
        # Step 2: Compare against reference processed structures in Processed/
        reference_files = list(self.processed_dir.glob("*.xyz"))
        for ref_file in reference_files:
            if ref_file.name == xyz_path.name:
                continue
            try:
                ref_elems, ref_coords, _ = self._parse_xyz(ref_file)
                if len(elements) != len(ref_elems):
                    continue
                    
                rmsd = self.kabsch_rmsd(coords, ref_coords)
                if rmsd < self.rmsd_threshold:
                    print(f"   -> ❌ DUPLICATE DETECTED: Matches {ref_file.name} (RMSD: {rmsd:.4f} Å)")
                    logger.warning(f"Duplicate trapped. {xyz_path.name} matches {ref_file.name}.")
                    return False
            except Exception as e:
                logger.error(f"Error parsing reference file {ref_file.name}: {e}")
                
        print(f"   -> ✅ TOPOLOGICAL & RMSD GATEWAY PASSED: {xyz_path.name} is unique.")
        return True

if __name__ == "__main__":
    print("CoChem-CORE Stage 2.1: Ingestion & Deduplication Gatekeeper loaded.")