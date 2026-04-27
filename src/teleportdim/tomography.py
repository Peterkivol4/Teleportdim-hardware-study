from __future__ import annotations

from functools import lru_cache
from typing import cast

from itertools import product
from typing import Iterable

import numpy as np


_SINGLE_Q_PAULI = {
    "I": np.array([[1, 0], [0, 1]], dtype=complex),
    "X": np.array([[0, 1], [1, 0]], dtype=complex),
    "Y": np.array([[0, -1j], [1j, 0]], dtype=complex),
    "Z": np.array([[1, 0], [0, -1]], dtype=complex),
}


@lru_cache(maxsize=None)
def _all_measurement_bases_cached(n_qubits: int) -> tuple[str, ...]:
    """Return or manipulate  all measurement bases cached used in tomography and simulation."""
    return tuple("".join(labels) for labels in product("XYZ", repeat=n_qubits))


def all_measurement_bases(n_qubits: int) -> list[str]:
    """Return or manipulate all measurement bases used in tomography and simulation."""
    return list(_all_measurement_bases_cached(n_qubits))


@lru_cache(maxsize=None)
def _all_pauli_strings_cached(n_qubits: int) -> tuple[str, ...]:
    """Return or manipulate  all pauli strings cached used in tomography and simulation."""
    return tuple("".join(labels) for labels in product("IXYZ", repeat=n_qubits))


def all_pauli_strings(n_qubits: int) -> list[str]:
    """Return or manipulate all pauli strings used in tomography and simulation."""
    return list(_all_pauli_strings_cached(n_qubits))


@lru_cache(maxsize=None)
def pauli_operator(label: str) -> np.ndarray:
    """Return or manipulate pauli operator used in tomography and simulation."""
    op = np.array([[1]], dtype=complex)
    # Labels are tracked in low-to-high qubit order, while matrix tensor products are
    # conventionally assembled in high-to-low order for the computational basis.
    for char in reversed(label):
        op = np.kron(op, _SINGLE_Q_PAULI[char])
    return op


def _bitstring_expectation(counts: dict[str, int], active_positions: list[int]) -> float:
    """Utility function used by the TeleportDim experiment toolkit."""
    total = sum(counts.values())
    if total <= 0:
        raise ValueError("counts must contain at least one shot")
    value = 0.0
    for bitstring, count in counts.items():
        # Qiskit bitstrings print classical bits from high to low index.
        bits = bitstring.replace(" ", "")
        bits = bits[::-1]
        parity = sum(int(bits[pos]) for pos in active_positions) % 2
        value += (1.0 if parity == 0 else -1.0) * count
    return value / total


def compatible_measurement_setting(pauli_label: str) -> str:
    """Return or manipulate compatible measurement setting used in tomography and simulation."""
    return "".join("Z" if char == "I" else char for char in pauli_label)


def project_to_physical_density_matrix(rho: np.ndarray, *, atol: float = 1e-12) -> np.ndarray:
    """Project a reconstructed matrix back onto the physical density-matrix cone."""
    rho = np.asarray(rho, dtype=complex)
    if rho.ndim != 2 or rho.shape[0] != rho.shape[1]:
        raise ValueError("rho must be a square matrix")
    hermitian = 0.5 * (rho + rho.conj().T)
    eigenvalues, eigenvectors = np.linalg.eigh(hermitian)
    clipped = np.clip(np.real_if_close(eigenvalues), 0.0, None)
    total = float(np.sum(clipped))
    if total <= atol:
        return cast(np.ndarray, np.eye(rho.shape[0], dtype=complex) / rho.shape[0])
    projected = eigenvectors @ np.diag(clipped / total) @ eigenvectors.conj().T
    projected = 0.5 * (projected + projected.conj().T)
    return cast(np.ndarray, projected)


def reconstruct_density_matrix(
    setting_counts: dict[str, dict[str, int]], *, project_physical: bool = True
) -> np.ndarray:
    """Reconstruct a density matrix from Pauli-basis tomography counts.

    The reconstruction uses linear inversion over the Pauli basis and, by default, projects
    the estimate back onto the physical density-matrix set (Hermitian, PSD, unit trace).
    This keeps downstream fidelity and leakage calculations meaningful under finite-shot noise.
    """
    if not setting_counts:
        raise ValueError("setting_counts cannot be empty")
    n_qubits = len(next(iter(setting_counts)))
    identity_label = "I" * n_qubits
    expectations: dict[str, float] = {identity_label: 1.0}

    for pauli_label in _all_pauli_strings_cached(n_qubits):
        if pauli_label == identity_label:
            continue
        setting = compatible_measurement_setting(pauli_label)
        counts = setting_counts.get(setting)
        if counts is None:
            raise ValueError(f"missing counts for compatible setting {setting}")
        active_positions = [i for i, char in enumerate(pauli_label) if char != "I"]
        expectations[pauli_label] = _bitstring_expectation(counts, active_positions)

    rho = np.zeros((2**n_qubits, 2**n_qubits), dtype=complex)
    for label, expval in expectations.items():
        rho += expval * pauli_operator(label)
    rho /= 2**n_qubits
    if project_physical:
        rho = project_to_physical_density_matrix(rho)
    return rho


__all__ = [
    "all_measurement_bases",
    "all_pauli_strings",
    "pauli_operator",
    "compatible_measurement_setting",
    "project_to_physical_density_matrix",
    "reconstruct_density_matrix",
]
