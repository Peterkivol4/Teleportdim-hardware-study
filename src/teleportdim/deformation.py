from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

from .process import apply_superoperator


@dataclass(slots=True)
class ChannelDeformationRecord:
    """Standard row schema for channel-body deformation artifacts.

    Fidelity-like quantities and leakage are unitless probabilities. ``delay_dt`` is an
    IBM-style integer delay coordinate; callers should include a separate ``dt_ns`` field
    in exported dictionaries when a physical calibration is available.
    """

    dimension: int
    n_physical: int
    fill_ratio: float
    body: str
    body_strength: float
    delay_dt: int
    fidelity: float
    leakage: float
    in_subspace_fidelity: float
    process_fidelity: float | None
    average_gate_fidelity: float | None
    blp_score: float | None
    nonunitality: float | None
    anisotropy: float | None
    state_spread: float | None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dictionary representation of the record."""
        return asdict(self)


def nonunitality_from_superoperator(superoperator: np.ndarray, dimension: int) -> float:
    """Measure how far a reconstructed channel moves the maximally mixed logical state.

    The output is the Frobenius norm ``||E(I/d) - I/d||_F`` and is therefore unitless.
    It is zero for identity, depolarizing, and dephasing channels, and positive for
    non-unital bodies such as amplitude damping.
    """
    mixed = np.eye(dimension, dtype=complex) / float(dimension)
    output = apply_superoperator(superoperator, mixed)
    return float(np.linalg.norm(output - mixed, ord="fro"))


def state_fidelity_spread(fidelities: Sequence[float]) -> tuple[float, float]:
    """Return ``(anisotropy, state_spread)`` for a probe-fidelity ensemble."""
    if not fidelities:
        raise ValueError("fidelities cannot be empty")
    values = np.asarray([float(value) for value in fidelities], dtype=float)
    anisotropy = float(np.max(values) - np.min(values))
    state_spread = float(np.std(values))
    return anisotropy, state_spread


def _optional_float(record: Mapping[str, Any], key: str) -> float | None:
    """Extract a nullable float from a mapping-based deformation record."""
    value = record.get(key)
    if value is None:
        return None
    return float(value)


def _delta_from_fidelity(value: float | None) -> float | None:
    """Convert a fidelity-like score into a deformation coordinate."""
    if value is None:
        return None
    return float(1.0 - value)


def compute_channel_deformation_vector(record: Mapping[str, Any]) -> dict[str, Any]:
    """Convert a metric record into the canonical deformation-vector coordinates."""
    process_fidelity = _optional_float(record, "process_fidelity")
    average_gate_fidelity = _optional_float(record, "average_gate_fidelity")
    in_subspace_fidelity = _optional_float(record, "in_subspace_fidelity")
    return {
        "dimension": record.get("dimension"),
        "n_physical": record.get("n_physical"),
        "fill_ratio": record.get("fill_ratio"),
        "body": record.get("body", record.get("simulation_lane", record.get("backend_name"))),
        "body_strength": record.get("body_strength"),
        "delay_dt": record.get("delay_dt"),
        "delta_process": _delta_from_fidelity(process_fidelity),
        "delta_avg_gate": _delta_from_fidelity(average_gate_fidelity),
        "leakage": _optional_float(record, "leakage"),
        "delta_subspace": _delta_from_fidelity(in_subspace_fidelity),
        "nonunitality": _optional_float(record, "nonunitality"),
        "anisotropy": _optional_float(record, "anisotropy"),
        "state_spread": _optional_float(record, "state_spread"),
        "blp": _optional_float(record, "blp_score"),
    }


__all__ = [
    "ChannelDeformationRecord",
    "nonunitality_from_superoperator",
    "state_fidelity_spread",
    "compute_channel_deformation_vector",
]
