from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from itertools import product
from typing import Final, Literal, cast

import numpy as np

from .encoding import (
    embed_logical_state,
    physical_hilbert_dimension_for_logical_dimension,
    resolved_n_physical,
)
from .metrics import pure_state_density
from .simulation import (
    amplitude_damping_kraus,
    correlated_memory_density_trajectory,
    dephasing_kraus,
    depolarizing_kraus,
    random_telegraph_dephasing_density_trajectory,
)


NoiseBodyName = Literal[
    "ideal",
    "dephasing",
    "amplitude_damping",
    "depolarizing",
    "relaxation",
    "leakage_mixing",
    "coherent_z_drift",
    "coherent_x_drift",
    "correlated_memory",
    "random_telegraph",
    "readout",
    "hardware",
]

VALID_NOISE_BODIES: Final[frozenset[str]] = frozenset(
    {
        "ideal",
        "dephasing",
        "amplitude_damping",
        "depolarizing",
        "relaxation",
        "leakage_mixing",
        "coherent_z_drift",
        "coherent_x_drift",
        "correlated_memory",
        "random_telegraph",
        "readout",
        "hardware",
    }
)


@dataclass(slots=True)
class NoiseBodyConfig:
    """Configuration for one phenomenological channel-deformation body.

    Parameters are unitless unless explicitly calibrated by a caller. ``strength`` is the
    generic per-body error scale, ``memory_strength`` is restricted to ``[0, 1]`` for the
    correlated-memory lane, and ``leakage_rate`` / ``readout_error`` are probabilities.
    ``hardware`` is accepted as a record label but cannot be synthesized by the local
    theory sweep.
    """

    body: str
    strength: float
    correlation: float = 0.0
    memory_strength: float = 0.0
    coherent_angle: float = 0.0
    leakage_rate: float = 0.0
    readout_error: float = 0.0
    seed: int | None = None

    def __post_init__(self) -> None:
        if self.body not in VALID_NOISE_BODIES:
            raise ValueError(
                f"unsupported noise body: {self.body}; expected one of {sorted(VALID_NOISE_BODIES)}"
            )
        if self.strength < 0.0:
            raise ValueError("strength must be nonnegative")
        if self.correlation < 0.0:
            raise ValueError("correlation must be nonnegative")
        if not 0.0 <= self.memory_strength <= 1.0:
            raise ValueError("memory_strength must be in [0, 1]")
        if not 0.0 <= self.leakage_rate <= 1.0:
            raise ValueError("leakage_rate must be in [0, 1]")
        if not 0.0 <= self.readout_error <= 1.0:
            raise ValueError("readout_error must be in [0, 1]")


def delay_dt_to_body_steps(delay_dt: int, *, step_dt: int = 64, max_steps: int = 64) -> int:
    """Convert backend-style delay ticks into bounded model-update steps.

    The body models are phenomenological and should not run thousands of Monte-Carlo
    updates for large IBM ``dt`` grids. A ``64 dt`` step maps the common hardware grid
    ``0,64,128`` to ``1,1,2`` model updates while keeping long Aer grids tractable.
    """
    if step_dt < 1:
        raise ValueError("step_dt must be >= 1")
    if max_steps < 1:
        raise ValueError("max_steps must be >= 1")
    delay = max(0, int(delay_dt))
    steps = max(1, int(round(delay / float(step_dt))))
    return min(steps, max_steps)


def effective_body_probability(strength: float, delay_dt: int, *, step_dt: int = 64) -> float:
    """Map a unitless body strength and delay coordinate to a probability in ``[0, 1]``."""
    if strength < 0.0:
        raise ValueError("strength must be nonnegative")
    steps = delay_dt_to_body_steps(delay_dt, step_dt=step_dt)
    return float(np.clip(1.0 - np.exp(-float(strength) * float(steps)), 0.0, 1.0))


def _tensor_kraus(single_qubit_ops: Sequence[np.ndarray], n_qubits: int) -> list[np.ndarray]:
    """Tensor a single-qubit Kraus channel over the physical register."""
    ops: list[np.ndarray] = []
    for choices in product(range(len(single_qubit_ops)), repeat=n_qubits):
        op = np.array([[1.0]], dtype=complex)
        for idx in choices:
            op = np.kron(op, single_qubit_ops[idx])
        ops.append(op)
    return ops


def _apply_kraus(rho: np.ndarray, kraus_ops: Sequence[np.ndarray]) -> np.ndarray:
    """Apply a finite Kraus representation to a density matrix."""
    out = np.zeros_like(rho, dtype=complex)
    for op in kraus_ops:
        out += op @ rho @ op.conj().T
    return out


def _single_qubit_rotation(axis: Literal["x", "z"], angle: float) -> np.ndarray:
    """Return a one-qubit coherent rotation used for drift-body fingerprints."""
    half = 0.5 * float(angle)
    if axis == "z":
        return np.array(
            [[np.exp(-1j * half), 0.0], [0.0, np.exp(1j * half)]],
            dtype=complex,
        )
    cos = np.cos(half)
    sin = np.sin(half)
    return np.array([[cos, -1j * sin], [-1j * sin, cos]], dtype=complex)


def _tensor_unitary(single_qubit_unitary: np.ndarray, n_qubits: int) -> np.ndarray:
    """Tensor a coherent one-qubit drift over all physical qubits."""
    unitary = np.array([[1.0]], dtype=complex)
    for _ in range(n_qubits):
        unitary = np.kron(unitary, single_qubit_unitary)
    return unitary


def _apply_coherent_rotation(rho: np.ndarray, *, axis: Literal["x", "z"], angle: float, n_qubits: int) -> np.ndarray:
    """Apply a register-wide coherent rotation to a density matrix."""
    unitary = _tensor_unitary(_single_qubit_rotation(axis, angle), n_qubits)
    return cast(np.ndarray, unitary @ rho @ unitary.conj().T)


def _apply_leakage_mixing(
    rho: np.ndarray,
    *,
    dimension: int,
    n_physical: int,
    probability: float,
) -> np.ndarray:
    """Move probability from the code subspace into unused computational basis states."""
    physical_dim = physical_hilbert_dimension_for_logical_dimension(dimension, n_physical)
    unused_indices = list(range(dimension, physical_dim))
    if not unused_indices:
        return np.asarray(rho, dtype=complex).copy()
    leakage_density = np.zeros((physical_dim, physical_dim), dtype=complex)
    weight = 1.0 / float(len(unused_indices))
    for index in unused_indices:
        leakage_density[index, index] = weight
    p = float(np.clip(probability, 0.0, 1.0))
    return cast(np.ndarray, (1.0 - p) * rho + p * leakage_density)


def _readout_bit_flip_kraus(probability: float) -> list[np.ndarray]:
    """Approximate readout distortion as a final classical bit-flip channel."""
    p = float(np.clip(probability, 0.0, 1.0))
    identity = np.eye(2, dtype=complex)
    bit_flip = np.array([[0, 1], [1, 0]], dtype=complex)
    return [np.sqrt(1.0 - p) * identity, np.sqrt(p) * bit_flip]


def apply_noise_body_to_density(
    logical_state: np.ndarray,
    dimension: int,
    config: NoiseBodyConfig,
    *,
    n_physical: int | None = None,
    delay_dt: int = 0,
    samples: int = 2048,
) -> np.ndarray:
    """Apply one modeled body to an embedded logical input state.

    The return value is a density matrix on the full ``2**n_physical`` Hilbert space. It
    is a controlled phenomenological model, not a substitute for the circuit-faithful Aer
    or IBM hardware lanes.
    """
    if config.body == "hardware":
        raise ValueError("hardware body records must come from hardware data, not a synthetic body model")
    resolved_n = resolved_n_physical(dimension, n_physical)
    embedded = embed_logical_state(logical_state, dimension, resolved_n)
    rho = pure_state_density(embedded)
    probability = effective_body_probability(config.strength, delay_dt)

    if config.body == "ideal":
        return rho
    if config.body == "dephasing":
        return _apply_kraus(rho, _tensor_kraus(dephasing_kraus(probability), resolved_n))
    if config.body == "amplitude_damping":
        return _apply_kraus(rho, _tensor_kraus(amplitude_damping_kraus(probability), resolved_n))
    if config.body == "depolarizing":
        return _apply_kraus(rho, _tensor_kraus(depolarizing_kraus(probability), resolved_n))
    if config.body == "relaxation":
        damped = _apply_kraus(rho, _tensor_kraus(amplitude_damping_kraus(probability), resolved_n))
        return _apply_kraus(damped, _tensor_kraus(dephasing_kraus(0.5 * probability), resolved_n))
    if config.body == "leakage_mixing":
        leakage_probability = config.leakage_rate if config.leakage_rate > 0.0 else probability
        return _apply_leakage_mixing(
            rho,
            dimension=dimension,
            n_physical=resolved_n,
            probability=leakage_probability,
        )
    if config.body == "coherent_z_drift":
        angle = config.coherent_angle if not np.isclose(config.coherent_angle, 0.0) else config.strength * delay_dt_to_body_steps(delay_dt)
        return _apply_coherent_rotation(rho, axis="z", angle=float(angle), n_qubits=resolved_n)
    if config.body == "coherent_x_drift":
        angle = config.coherent_angle if not np.isclose(config.coherent_angle, 0.0) else config.strength * delay_dt_to_body_steps(delay_dt)
        return _apply_coherent_rotation(rho, axis="x", angle=float(angle), n_qubits=resolved_n)
    if config.body == "correlated_memory":
        steps = delay_dt_to_body_steps(delay_dt)
        trajectory = correlated_memory_density_trajectory(
            logical_state,
            dimension,
            n_physical=resolved_n,
            steps=steps,
            base_phase_flip_probability=probability,
            memory_strength=config.memory_strength,
            samples=samples,
            seed=config.seed or 7,
        )
        return trajectory[-1]
    if config.body == "random_telegraph":
        steps = delay_dt_to_body_steps(delay_dt)
        coupling_strength = config.correlation if config.correlation > 0.0 else 0.4
        trajectory = random_telegraph_dephasing_density_trajectory(
            logical_state,
            dimension,
            n_physical=resolved_n,
            steps=steps,
            coupling_strength=coupling_strength,
            switching_probability=probability,
            samples=samples,
            seed=config.seed or 7,
        )
        return trajectory[-1]
    if config.body == "readout":
        readout_probability = config.readout_error if config.readout_error > 0.0 else probability
        return _apply_kraus(rho, _tensor_kraus(_readout_bit_flip_kraus(readout_probability), resolved_n))
    raise ValueError(f"unsupported noise body: {config.body}")


__all__ = [
    "NoiseBodyName",
    "VALID_NOISE_BODIES",
    "NoiseBodyConfig",
    "delay_dt_to_body_steps",
    "effective_body_probability",
    "apply_noise_body_to_density",
]
