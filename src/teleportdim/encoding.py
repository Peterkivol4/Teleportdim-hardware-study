from __future__ import annotations

from .config import DEFAULT_AER_DT_NS_PER_DT

import math
from typing import cast
from typing import Iterable

import numpy as np


class EncodingError(ValueError):
    """Raised when logical-dimension embedding is invalid."""


def num_physical_qubits_for_dimension(dimension: int) -> int:
    """Return the minimum physical qubit count required for a logical dimension."""
    if dimension < 2:
        raise EncodingError("dimension must be at least 2")
    return math.ceil(math.log2(dimension))


def resolved_n_physical(dimension: int, n_physical: int | None = None) -> int:
    """Resolve and validate the physical qubit count used for an encoded logical dimension."""
    minimum = num_physical_qubits_for_dimension(dimension)
    if n_physical is None:
        return minimum
    if n_physical < minimum:
        raise EncodingError(
            f"n_physical={n_physical} is too small for dimension={dimension}; need at least {minimum}"
        )
    return int(n_physical)


def physical_hilbert_dimension_for_logical_dimension(
    dimension: int, n_physical: int | None = None
) -> int:
    """Return the physical Hilbert-space size associated with the chosen embedding."""
    return cast(int, 2 ** resolved_n_physical(dimension, n_physical))


def fill_ratio(dimension: int, n_physical: int | None = None) -> float:
    """Compute the logical-to-physical Hilbert-space fill ratio for an embedding."""
    return float(dimension / physical_hilbert_dimension_for_logical_dimension(dimension, n_physical))


def dt_seconds_to_ns(dt_seconds: float | None) -> float | None:
    """Convert one backend ``dt`` tick from seconds to nanoseconds."""
    if dt_seconds is None:
        return None
    return float(dt_seconds) * 1e9


def delay_dt_to_ns(
    delay_dt: int | float,
    *,
    dt_seconds: float | None = None,
    dt_ns_per_dt: float | None = None,
) -> float | None:
    """Convert a delay expressed in backend ``dt`` units into nanoseconds when calibrated."""
    scale_ns = float(dt_ns_per_dt) if dt_ns_per_dt is not None else dt_seconds_to_ns(dt_seconds)
    if scale_ns is None:
        return None
    return float(delay_dt) * scale_ns


def resolved_aer_dt_ns_per_dt(dt_ns_per_dt: float | None = None) -> float:
    """Return the Aer-lane ``dt`` calibration used for labels and delay relaxation."""
    if dt_ns_per_dt is None:
        return float(DEFAULT_AER_DT_NS_PER_DT)
    return float(dt_ns_per_dt)


def logical_basis_indices(dimension: int, n_physical: int | None = None) -> np.ndarray:
    """Return the computational-basis indices occupied by the logical codespace.

    The embedding always uses the first ``dimension`` computational basis states.
    ``n_physical`` therefore serves as an explicit embedding-size validation knob rather
    than changing which basis states are selected. Passing an invalid ``n_physical``
    raises immediately instead of silently falling back to the minimal encoding.
    """
    physical_dim = physical_hilbert_dimension_for_logical_dimension(dimension, n_physical)
    indices = np.arange(dimension, dtype=int)
    if indices[-1] >= physical_dim:
        raise EncodingError(
            f"logical basis for dimension={dimension} exceeds physical Hilbert dimension {physical_dim}"
        )
    return indices


def logical_subspace_projector(dimension: int, n_physical: int | None = None) -> np.ndarray:
    """Logical subspace projector for encoded logical-state analysis."""
    physical_dim = physical_hilbert_dimension_for_logical_dimension(dimension, n_physical)
    projector = np.zeros((physical_dim, physical_dim), dtype=complex)
    projector[:dimension, :dimension] = np.eye(dimension, dtype=complex)
    return projector


def normalize_logical_state(state: Iterable[complex], dimension: int) -> np.ndarray:
    """Normalize logical state for encoded logical-state analysis."""
    vec = np.asarray(list(state), dtype=complex)
    if vec.ndim != 1:
        raise EncodingError("state must be a 1D vector")
    if len(vec) != dimension:
        raise EncodingError(f"expected logical state of length {dimension}, got {len(vec)}")
    norm = np.linalg.norm(vec)
    if np.isclose(norm, 0.0):
        raise EncodingError("state must have non-zero norm")
    return cast(np.ndarray, vec / norm)


def embed_logical_state(
    state: Iterable[complex], dimension: int, n_physical: int | None = None
) -> np.ndarray:
    """Embed a logical state into the first ``dimension`` basis states of a qubit register.

    Parameters
    ----------
    state:
        Logical state amplitudes living in a ``dimension``-dimensional Hilbert space.
    dimension:
        Logical Hilbert-space dimension of the encoded information.
    n_physical:
        Optional explicit physical qubit count. When omitted, the minimal qubit count
        ``ceil(log2(dimension))`` is used. When provided, it must be large enough to host
        the logical space and defines the ambient physical Hilbert space size ``2**n``.
    """
    logical = normalize_logical_state(state, dimension)
    physical_dim = physical_hilbert_dimension_for_logical_dimension(dimension, n_physical)
    embedded = np.zeros(physical_dim, dtype=complex)
    embedded[:dimension] = logical
    return embedded


def extract_logical_density_subspace(
    rho: np.ndarray, dimension: int, n_physical: int | None = None
) -> np.ndarray:
    """Extract logical density subspace for encoded logical-state analysis."""
    rho = np.asarray(rho, dtype=complex)
    expected = physical_hilbert_dimension_for_logical_dimension(dimension, n_physical)
    if rho.shape != (expected, expected):
        raise EncodingError(
            f"expected density matrix shape {(expected, expected)}, got {rho.shape}"
        )
    return rho[:dimension, :dimension]


__all__ = [
    "EncodingError",
    "num_physical_qubits_for_dimension",
    "physical_hilbert_dimension_for_logical_dimension",
    "fill_ratio",
    "dt_seconds_to_ns",
    "delay_dt_to_ns",
    "resolved_aer_dt_ns_per_dt",
    "logical_basis_indices",
    "logical_subspace_projector",
    "normalize_logical_state",
    "embed_logical_state",
    "extract_logical_density_subspace",
    "resolved_n_physical",
]
