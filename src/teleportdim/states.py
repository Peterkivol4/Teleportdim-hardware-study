from __future__ import annotations

from typing import cast

import numpy as np


def random_haar_state(dimension: int, seed: int | None = None) -> np.ndarray:
    """Construct random haar state for simulation, tomography, or benchmarking."""
    rng = np.random.default_rng(seed)
    real = rng.normal(size=dimension)
    imag = rng.normal(size=dimension)
    vec = real + 1j * imag
    return cast(np.ndarray, vec / np.linalg.norm(vec))


def computational_basis_state(dimension: int, index: int) -> np.ndarray:
    """Construct computational basis state for simulation, tomography, or benchmarking."""
    if index < 0 or index >= dimension:
        raise ValueError("basis index out of range")
    vec = np.zeros(dimension, dtype=complex)
    vec[index] = 1.0
    return vec


def fourier_state(dimension: int, k: int = 0) -> np.ndarray:
    """Construct fourier state for simulation, tomography, or benchmarking."""
    n = np.arange(dimension)
    omega = np.exp(2j * np.pi / dimension)
    vec = omega ** (k * n)
    return cast(np.ndarray, vec / np.linalg.norm(vec))


def canonical_probe_states(dimension: int) -> list[np.ndarray]:
    """Construct canonical probe states for simulation, tomography, or benchmarking."""
    return [computational_basis_state(dimension, idx) for idx in range(dimension)] + [fourier_state(dimension, 0)]


__all__ = [
    "random_haar_state",
    "computational_basis_state",
    "fourier_state",
    "canonical_probe_states",
]
