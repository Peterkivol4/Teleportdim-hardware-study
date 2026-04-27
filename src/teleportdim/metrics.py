from __future__ import annotations

from .encoding import (
    extract_logical_density_subspace,
    fill_ratio,
    logical_subspace_projector,
    physical_hilbert_dimension_for_logical_dimension,
)
from typing import cast

import numpy as np



def counts_to_probabilities(counts: dict[str, int]) -> dict[str, float]:
    """Normalize raw shot counts into outcome probabilities.

    Parameters
    ----------
    counts:
        Mapping from measured computational-basis bitstrings to shot counts for one
        tomography or readout setting.

    Returns
    -------
    dict[str, float]
        A probability distribution over the same bitstrings, normalized by the total
        number of shots in ``counts``.
    """
    total = sum(counts.values())
    if total <= 0:
        raise ValueError("counts must contain at least one shot")
    return {bitstring: value / total for bitstring, value in counts.items()}


def expectation_from_counts(counts: dict[str, int]) -> float:
    """Estimate a Z-parity expectation value from measured bitstring counts.

    Each bitstring is assigned eigenvalue ``+1`` for even parity and ``-1`` for odd
    parity, which matches the Pauli-string expectation values used by the tomography
    reconstruction helpers in this module.
    """
    total = sum(counts.values())
    if total <= 0:
        raise ValueError("counts must contain at least one shot")
    acc = 0.0
    for bitstring, c in counts.items():
        parity = sum(int(bit) for bit in bitstring) % 2
        acc += (1.0 if parity == 0 else -1.0) * c
    return acc / total


def pure_state_density(psi: np.ndarray) -> np.ndarray:
    """Construct the density matrix ``|psi><psi|`` for a normalized statevector ``psi``."""
    psi = np.asarray(psi, dtype=complex)
    return np.outer(psi, psi.conj())


def pure_state_fidelity(psi: np.ndarray, rho: np.ndarray) -> float:
    """Compute the fidelity between a pure target state and a density matrix.

    Parameters
    ----------
    psi:
        Logical or embedded target statevector.
    rho:
        Density matrix reconstructed from tomography or produced by one of the noise
        models in this package. ``rho`` must act on the same Hilbert space as ``psi``.
    """
    psi = np.asarray(psi, dtype=complex)
    rho = np.asarray(rho, dtype=complex)
    value = np.vdot(psi, rho @ psi)
    return float(np.real_if_close(value))


def leakage_probability(rho: np.ndarray, dimension: int, n_physical: int | None = None) -> float:
    """Return the population that has left the encoded logical subspace.

    Parameters
    ----------
    rho:
        Density matrix on the full ``2**n_physical`` Hilbert space.
    dimension:
        Logical Hilbert-space dimension ``d`` of the encoded subspace.
    n_physical:
        Physical qubit count ``n`` used for the embedding. When omitted, the minimal
        embedding that can represent ``dimension`` is used.

    Returns
    -------
    float
        Probability mass found outside the first ``dimension`` logical basis states of
        the embedding. This is the quantity reported as leakage in the thesis figures.
    """
    rho = np.asarray(rho, dtype=complex)
    projector = logical_subspace_projector(dimension, n_physical)
    if rho.shape != projector.shape:
        expected = projector.shape
        raise ValueError(f"expected density matrix shape {expected}, got {rho.shape}")
    population_in_codespace = np.trace(projector @ rho)
    leakage = 1.0 - float(np.real_if_close(population_in_codespace))
    return float(np.clip(leakage, 0.0, 1.0))


def logical_subspace_population(rho: np.ndarray, dimension: int, n_physical: int | None = None) -> float:
    """Logical subspace population for encoded logical-state analysis."""
    return 1.0 - leakage_probability(rho, dimension, n_physical)


def renormalized_logical_subspace_density(
    rho: np.ndarray, dimension: int, n_physical: int | None = None
) -> np.ndarray:
    """Utility function used by the TeleportDim experiment toolkit."""
    subspace = extract_logical_density_subspace(rho, dimension, n_physical)
    trace = np.trace(subspace)
    if np.isclose(trace, 0.0):
        return np.zeros_like(subspace)
    return cast(np.ndarray, subspace / trace)


def in_subspace_fidelity(
    logical_target: np.ndarray, rho: np.ndarray, dimension: int, n_physical: int | None = None
) -> float:
    """Compute fidelity after renormalizing onto the logical codespace.

    This separates logical damage inside the occupied subspace from population that has
    leaked into unused computational-basis states. ``logical_target`` is expressed in the
    ``dimension``-dimensional logical basis, while ``rho`` lives on the full physical
    Hilbert space.
    """
    logical_target = np.asarray(logical_target, dtype=complex)
    if logical_target.ndim != 1 or logical_target.shape[0] != dimension:
        raise ValueError(
            f"logical_target must be a 1D vector of length {dimension}; "
            f"got shape {logical_target.shape}"
        )
    reduced = renormalized_logical_subspace_density(rho, dimension, n_physical)
    if not np.any(reduced):
        return 0.0
    return pure_state_fidelity(logical_target, reduced)


def physical_and_logical_summary(dimension: int, n_physical: int | None = None) -> dict[str, float | int]:
    """Return the physical Hilbert-space size associated with the chosen embedding."""
    physical_dim = physical_hilbert_dimension_for_logical_dimension(dimension, n_physical)
    return {
        "dimension": dimension,
        "physical_hilbert_dimension": physical_dim,
        "fill_ratio": fill_ratio(dimension, n_physical),
        "leakage_capacity": physical_dim - dimension,
    }


def average_gate_fidelity_from_process_fidelity(process_fidelity: float, dimension: int) -> float:
    """Convert entanglement/process fidelity into average gate fidelity.

    The formula used is ``F_avg = (d * F_process + 1) / (d + 1)`` for a ``d``-dimensional
    logical channel.
    """
    fp = float(process_fidelity)
    d = float(dimension)
    return (d * fp + 1.0) / (d + 1.0)


__all__ = [
    "counts_to_probabilities",
    "expectation_from_counts",
    "pure_state_density",
    "pure_state_fidelity",
    "leakage_probability",
    "logical_subspace_population",
    "renormalized_logical_subspace_density",
    "in_subspace_fidelity",
    "physical_and_logical_summary",
    "average_gate_fidelity_from_process_fidelity",
]
