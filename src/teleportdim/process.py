from __future__ import annotations

from .encoding import normalize_logical_state
from .metrics import pure_state_fidelity
from .states import computational_basis_state
from .tomography import project_to_physical_density_matrix
from typing import cast

from collections.abc import Sequence

import numpy as np


def process_tomography_probe_states(dimension: int) -> list[np.ndarray]:
    """Return a pure-state probe set that spans the logical density-operator space."""
    if dimension < 2:
        raise ValueError("dimension must be >= 2")

    states = [computational_basis_state(dimension, index) for index in range(dimension)]
    for left in range(dimension):
        for right in range(left + 1, dimension):
            plus = np.zeros(dimension, dtype=complex)
            plus[left] = 1.0
            plus[right] = 1.0
            states.append(normalize_logical_state(plus, dimension))

            plus_i = np.zeros(dimension, dtype=complex)
            plus_i[left] = 1.0
            plus_i[right] = 1.0j
            states.append(normalize_logical_state(plus_i, dimension))
    return states


def vectorize_operator(operator: np.ndarray) -> np.ndarray:
    """Column-stack an operator into Liouville form."""
    op = np.asarray(operator, dtype=complex)
    if op.ndim != 2 or op.shape[0] != op.shape[1]:
        raise ValueError("operator must be a square matrix")
    return op.reshape(-1, order="F")


def apply_superoperator(superoperator: np.ndarray, rho: np.ndarray) -> np.ndarray:
    """Apply a reconstructed superoperator to a density matrix."""
    sop = np.asarray(superoperator, dtype=complex)
    state = np.asarray(rho, dtype=complex)
    if state.ndim != 2 or state.shape[0] != state.shape[1]:
        raise ValueError("rho must be a square matrix")
    d = state.shape[0]
    if sop.shape != (d * d, d * d):
        raise ValueError(f"expected superoperator shape {(d * d, d * d)}, got {sop.shape}")
    return cast(np.ndarray, (sop @ vectorize_operator(state)).reshape((d, d), order="F"))


def reconstruct_superoperator(
    input_densities: Sequence[np.ndarray],
    output_densities: Sequence[np.ndarray],
) -> np.ndarray:
    """Reconstruct a logical superoperator from input/output density-matrix pairs."""
    if len(input_densities) != len(output_densities):
        raise ValueError("input_densities and output_densities must have the same length")
    if not input_densities:
        raise ValueError("input_densities cannot be empty")

    inputs = [np.asarray(rho, dtype=complex) for rho in input_densities]
    outputs = [np.asarray(rho, dtype=complex) for rho in output_densities]
    dimension = inputs[0].shape[0]
    expected = (dimension, dimension)
    for rho in inputs + outputs:
        if rho.shape != expected:
            raise ValueError(f"all density matrices must have shape {expected}")

    basis_matrix = np.column_stack([vectorize_operator(rho) for rho in inputs])
    if np.linalg.matrix_rank(basis_matrix) < dimension * dimension:
        raise ValueError("input probe states are not informationally complete for process tomography")
    outputs_matrix = np.column_stack([vectorize_operator(rho) for rho in outputs])
    return outputs_matrix @ np.linalg.pinv(basis_matrix)


def choi_matrix_from_superoperator(superoperator: np.ndarray, dimension: int) -> np.ndarray:
    """Convert a Liouville superoperator into its Choi matrix."""
    sop = np.asarray(superoperator, dtype=complex)
    expected = (dimension * dimension, dimension * dimension)
    if sop.shape != expected:
        raise ValueError(f"expected superoperator shape {expected}, got {sop.shape}")

    choi = np.zeros(expected, dtype=complex)
    for row in range(dimension):
        for col in range(dimension):
            basis = np.zeros((dimension, dimension), dtype=complex)
            basis[row, col] = 1.0
            evolved = apply_superoperator(sop, basis)
            choi += np.kron(evolved, basis)
    return choi


def process_fidelity_to_identity(
    superoperator: np.ndarray,
    dimension: int,
    *,
    project_physical: bool = True,
) -> float:
    """Compute the process fidelity of a reconstructed channel against the identity."""
    choi = choi_matrix_from_superoperator(superoperator, dimension) / float(dimension)
    if project_physical:
        choi = project_to_physical_density_matrix(choi)
    maximally_entangled = np.eye(dimension, dtype=complex).reshape(-1, order="F") / np.sqrt(dimension)
    return pure_state_fidelity(maximally_entangled, choi)


__all__ = [
    "process_tomography_probe_states",
    "vectorize_operator",
    "apply_superoperator",
    "reconstruct_superoperator",
    "choi_matrix_from_superoperator",
    "process_fidelity_to_identity",
]
