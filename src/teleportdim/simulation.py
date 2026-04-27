from __future__ import annotations

from collections.abc import Sequence
from typing import cast

from .encoding import (
    embed_logical_state,
    physical_hilbert_dimension_for_logical_dimension,
    resolved_n_physical,
)
from .metrics import in_subspace_fidelity, leakage_probability, pure_state_density, pure_state_fidelity
from .states import fourier_state

from itertools import product

import numpy as np


_NumberLike = int | float | str


def _record_float(value: object) -> float:
    """Convert a numeric JSON-record value to float after schema-level filtering."""
    return float(cast(_NumberLike, value))


def _record_int(value: object) -> int:
    """Convert a numeric JSON-record value to int after schema-level filtering."""
    return int(cast(int | str, value))


def _tensor_kraus(single_qubit_ops: list[np.ndarray], n_qubits: int) -> list[np.ndarray]:
    """Build or apply the  tensor kraus used by the effective noise models."""
    ops: list[np.ndarray] = []
    for choices in product(range(len(single_qubit_ops)), repeat=n_qubits):
        op = np.array([[1]], dtype=complex)
        for idx in choices:
            op = np.kron(op, single_qubit_ops[idx])
        ops.append(op)
    return ops


def _apply_kraus(rho: np.ndarray, kraus_ops: list[np.ndarray]) -> np.ndarray:
    """Build or apply the  apply kraus used by the effective noise models."""
    out = np.zeros_like(rho, dtype=complex)
    for op in kraus_ops:
        out += op @ rho @ op.conj().T
    return out


def dephasing_kraus(probability: float) -> list[np.ndarray]:
    """Build or apply the dephasing kraus used by the effective noise models."""
    p = float(np.clip(probability, 0.0, 1.0))
    k0 = np.sqrt(1.0 - p) * np.eye(2, dtype=complex)
    k1 = np.sqrt(p) * np.array([[1, 0], [0, -1]], dtype=complex)
    return [k0, k1]


def amplitude_damping_kraus(gamma: float) -> list[np.ndarray]:
    """Build or apply the amplitude damping kraus used by the effective noise models."""
    g = float(np.clip(gamma, 0.0, 1.0))
    k0 = np.array([[1.0, 0.0], [0.0, np.sqrt(1.0 - g)]], dtype=complex)
    k1 = np.array([[0.0, np.sqrt(g)], [0.0, 0.0]], dtype=complex)
    return [k0, k1]


def depolarizing_kraus(probability: float) -> list[np.ndarray]:
    """Build or apply the depolarizing kraus used by the effective noise models."""
    p = float(np.clip(probability, 0.0, 1.0))
    x = np.array([[0, 1], [1, 0]], dtype=complex)
    y = np.array([[0, -1j], [1j, 0]], dtype=complex)
    z = np.array([[1, 0], [0, -1]], dtype=complex)
    return [
        np.sqrt(1.0 - p) * np.eye(2, dtype=complex),
        np.sqrt(p / 3.0) * x,
        np.sqrt(p / 3.0) * y,
        np.sqrt(p / 3.0) * z,
    ]


def markovian_delay_density(
    logical_state: np.ndarray,
    dimension: int,
    *,
    n_physical: int | None = None,
    delay: float,
    t1: float | None = None,
    t2: float | None = None,
    t_dep: float | None = None,
    depolarizing_probability: float | None = None,
) -> np.ndarray:
    """Phenomenological embedded-state storage model for the output block.

    This is a theory lane only. It is not a full noisy teleportation-circuit simulation.
    Leakage requires a channel that couples the codespace to the unused basis states,
    so this model includes optional depolarizing noise in addition to dephasing and T1 decay.

    Notes
    -----
    ``delay``, ``t1``, ``t2``, and ``t_dep`` must be expressed in the same units. In the
    theory lane they are dimensionless placeholders chosen by the caller. They are **not**
    automatically converted from IBM backend ``dt`` units.
    """
    embedded = embed_logical_state(logical_state, dimension, n_physical)
    rho = pure_state_density(embedded)
    n = resolved_n_physical(dimension, n_physical)

    if t2 is not None and t2 > 0:
        pz = 0.5 * (1.0 - np.exp(-delay / t2))
        rho = _apply_kraus(rho, _tensor_kraus(dephasing_kraus(pz), n))

    if t1 is not None and t1 > 0:
        gamma = 1.0 - np.exp(-delay / t1)
        rho = _apply_kraus(rho, _tensor_kraus(amplitude_damping_kraus(gamma), n))

    if depolarizing_probability is None and t_dep is not None and t_dep > 0:
        depolarizing_probability = 1.0 - np.exp(-delay / t_dep)
    if depolarizing_probability is not None and depolarizing_probability > 0.0:
        rho = _apply_kraus(
            rho,
            _tensor_kraus(depolarizing_kraus(float(depolarizing_probability)), n),
        )

    return rho


def markovian_delay_observables(
    logical_state: np.ndarray,
    dimension: int,
    *,
    n_physical: int | None = None,
    delay: float,
    t1: float | None = None,
    t2: float | None = None,
    t_dep: float | None = None,
    depolarizing_probability: float | None = None,
) -> dict[str, float]:
    """Evaluate the Markovian effective-noise model for a given delay and encoded dimension."""
    embedded = embed_logical_state(logical_state, dimension, n_physical)
    rho = markovian_delay_density(
        logical_state,
        dimension,
        n_physical=n_physical,
        delay=delay,
        t1=t1,
        t2=t2,
        t_dep=t_dep,
        depolarizing_probability=depolarizing_probability,
    )
    return {
        "fidelity": pure_state_fidelity(embedded, rho),
        "leakage": leakage_probability(rho, dimension, n_physical),
        "in_subspace_fidelity": in_subspace_fidelity(logical_state, rho, dimension, n_physical),
    }


def markovian_delay_fidelity(
    logical_state: np.ndarray,
    dimension: int,
    *,
    n_physical: int | None = None,
    delay: float,
    t1: float | None = None,
    t2: float | None = None,
    t_dep: float | None = None,
    depolarizing_probability: float | None = None,
) -> float:
    """Convenience wrapper that returns only the fidelity from the Markovian delay model."""
    return markovian_delay_observables(
        logical_state,
        dimension,
        n_physical=n_physical,
        delay=delay,
        t1=t1,
        t2=t2,
        t_dep=t_dep,
        depolarizing_probability=depolarizing_probability,
    )["fidelity"]


_PAULI_MATRICES = {
    0: np.eye(2, dtype=complex),
    1: np.array([[0, 1], [1, 0]], dtype=complex),
    2: np.array([[0, -1j], [1j, 0]], dtype=complex),
    3: np.array([[1, 0], [0, -1]], dtype=complex),
}


def _apply_local_pauli_to_statevector(state: np.ndarray, qubit: int, n_qubits: int, pauli_idx: int) -> np.ndarray:
    """Apply a single-qubit Pauli to a statevector in O(2**n) time."""
    if pauli_idx == 0:
        return np.asarray(state, dtype=complex).copy()
    if qubit < 0 or qubit >= n_qubits:
        raise ValueError(f"qubit index {qubit} out of range for n_qubits={n_qubits}")
    reshaped = np.asarray(state, dtype=complex).reshape((2,) * n_qubits)
    moved = np.moveaxis(reshaped, qubit, 0)
    transformed = np.empty_like(moved)
    if pauli_idx == 1:  # X
        transformed[0] = moved[1]
        transformed[1] = moved[0]
    elif pauli_idx == 2:  # Y
        transformed[0] = -1j * moved[1]
        transformed[1] = 1j * moved[0]
    elif pauli_idx == 3:  # Z
        transformed[0] = moved[0]
        transformed[1] = -moved[1]
    else:
        raise ValueError(f"unsupported pauli_idx: {pauli_idx}")
    return np.moveaxis(transformed, 0, qubit).reshape(-1)


def _sample_correlated_pauli_histories(
    *,
    n_qubits: int,
    steps: int,
    base_phase_flip_probability: float,
    memory_strength: float,
    samples: int,
    seed: int,
) -> np.ndarray:
    """Sample local Pauli error histories with one-step classical memory.

    The recurrence over time means the process cannot be fully vectorized across the step
    axis, but the expensive sample/qubit draws are batched in NumPy instead of nested
    Python loops.
    """
    rng = np.random.default_rng(seed)
    p = float(np.clip(base_phase_flip_probability, 0.0, 1.0))
    m = float(np.clip(memory_strength, 0.0, 1.0))
    if steps < 1:
        raise ValueError("steps must be >= 1")
    base_probs = np.array([1.0 - p, p / 3.0, p / 3.0, p / 3.0], dtype=float)
    fresh_draws = rng.choice(4, size=(samples, steps, n_qubits), p=base_probs).astype(np.int8)
    histories = np.empty_like(fresh_draws)
    histories[:, 0, :] = fresh_draws[:, 0, :]
    if steps == 1:
        return histories
    reuse_mask = rng.random((samples, steps - 1, n_qubits)) < m
    for step in range(1, steps):
        histories[:, step, :] = np.where(reuse_mask[:, step - 1, :], histories[:, step - 1, :], fresh_draws[:, step, :])
    return histories


def correlated_memory_density_trajectory(
    logical_state: np.ndarray,
    dimension: int,
    *,
    n_physical: int | None = None,
    steps: int,
    base_phase_flip_probability: float,
    memory_strength: float,
    samples: int = 2048,
    seed: int = 7,
    histories: np.ndarray | None = None,
) -> list[np.ndarray]:
    """Monte-Carlo estimate of density matrices under a correlated local Pauli process.

    The hidden process is still phenomenological, but unlike the phase-only model it can
    populate leakage states through X/Y components while preserving a tunable memory knob.
    """
    if steps < 1:
        raise ValueError("steps must be >= 1")
    embedded = embed_logical_state(logical_state, dimension, n_physical)
    n = resolved_n_physical(dimension, n_physical)

    if histories is None:
        histories = _sample_correlated_pauli_histories(
            n_qubits=n,
            steps=steps,
            base_phase_flip_probability=base_phase_flip_probability,
            memory_strength=memory_strength,
            samples=samples,
            seed=seed,
        )
    if histories.shape != (samples, steps, n):
        raise ValueError(
            f"expected histories shape {(samples, steps, n)}, got {histories.shape}"
        )

    accumulators = [np.zeros((2**n, 2**n), dtype=complex) for _ in range(steps + 1)]
    accumulators[0] = pure_state_density(embedded) * samples

    for sample in range(samples):
        state = embedded.copy()
        for step in range(1, steps + 1):
            errors = histories[sample, step - 1, :]
            for q, pauli_idx in enumerate(errors):
                if pauli_idx:
                    state = _apply_local_pauli_to_statevector(state, q, n, int(pauli_idx))
            accumulators[step] += pure_state_density(state)

    return [rho / samples for rho in accumulators]


def correlated_memory_observables(
    logical_state: np.ndarray,
    dimension: int,
    *,
    n_physical: int | None = None,
    steps: int,
    base_phase_flip_probability: float,
    memory_strength: float,
    samples: int = 2048,
    seed: int = 7,
) -> list[dict[str, float]]:
    """Evaluate the correlated-memory effective model used as the non-Markovian lane."""
    embedded = embed_logical_state(logical_state, dimension, n_physical)
    trajectory = correlated_memory_density_trajectory(
        logical_state,
        dimension,
        n_physical=n_physical,
        steps=steps,
        base_phase_flip_probability=base_phase_flip_probability,
        memory_strength=memory_strength,
        samples=samples,
        seed=seed,
    )
    return [
        {
            "step": step,
            "fidelity": pure_state_fidelity(embedded, rho),
            "leakage": leakage_probability(rho, dimension, n_physical),
            "in_subspace_fidelity": in_subspace_fidelity(logical_state, rho, dimension, n_physical),
        }
        for step, rho in enumerate(trajectory)
    ]


def correlated_memory_fidelity(
    logical_state: np.ndarray,
    dimension: int,
    *,
    n_physical: int | None = None,
    steps: int,
    base_phase_flip_probability: float,
    memory_strength: float,
    samples: int = 2048,
    seed: int = 7,
) -> float:
    """Convenience wrapper that returns only the fidelity from the correlated-memory lane."""
    return correlated_memory_observables(
        logical_state,
        dimension,
        n_physical=n_physical,
        steps=steps,
        base_phase_flip_probability=base_phase_flip_probability,
        memory_strength=memory_strength,
        samples=samples,
        seed=seed,
    )[-1]["fidelity"]


def _apply_local_z_rotation(state: np.ndarray, qubit: int, n_qubits: int, angle: float) -> np.ndarray:
    """Apply a single-qubit Z rotation to a statevector in O(2**n) time."""
    if qubit < 0 or qubit >= n_qubits:
        raise ValueError(f"qubit index {qubit} out of range for n_qubits={n_qubits}")
    phase_zero = np.exp(-0.5j * angle)
    phase_one = np.exp(0.5j * angle)
    reshaped = np.asarray(state, dtype=complex).reshape((2,) * n_qubits)
    moved = np.moveaxis(reshaped, qubit, 0).copy()
    moved[0] *= phase_zero
    moved[1] *= phase_one
    return np.moveaxis(moved, 0, qubit).reshape(-1)


def _sample_random_telegraph_histories(
    *,
    n_qubits: int,
    steps: int,
    switching_probability: float,
    samples: int,
    seed: int,
) -> np.ndarray:
    """Sample local random-telegraph noise histories for physically motivated dephasing."""
    if steps < 1:
        raise ValueError("steps must be >= 1")
    rng = np.random.default_rng(seed)
    switch_probability = float(np.clip(switching_probability, 0.0, 1.0))
    histories = np.empty((samples, steps, n_qubits), dtype=np.int8)
    histories[:, 0, :] = rng.choice([-1, 1], size=(samples, n_qubits))
    if steps == 1:
        return histories
    switches = rng.random((samples, steps - 1, n_qubits)) < switch_probability
    for step in range(1, steps):
        histories[:, step, :] = histories[:, step - 1, :]
        histories[:, step, :][switches[:, step - 1, :]] *= -1
    return histories


def switching_probability_to_correlation_time(
    switching_probability: float,
    *,
    dt: float = 1.0,
) -> float | None:
    """Map a telegraph switching probability to an exponential correlation time.

    The exact discrete-time relation is ``p_switch = 1 - exp(-dt / tau_corr)``. For
    small probabilities this reduces to the rule-of-thumb used in the README:
    ``p_switch ≈ dt / tau_corr``.
    """
    probability = float(switching_probability)
    if probability <= 0.0:
        return None
    if probability >= 1.0:
        return 0.0
    return float(-float(dt) / np.log(1.0 - probability))


def correlation_time_to_switching_probability(
    correlation_time: float,
    *,
    dt: float = 1.0,
) -> float:
    """Map a telegraph correlation time to the per-step switching probability."""
    tau_corr = float(correlation_time)
    if tau_corr <= 0.0:
        raise ValueError("correlation_time must be > 0")
    return float(1.0 - np.exp(-float(dt) / tau_corr))


def _random_telegraph_calibration_floor(
    metric: str,
    *,
    dimension: int,
    n_physical: int | None = None,
) -> float:
    """Return the asymptotic floor used when normalizing decay-based calibration metrics."""
    if metric == "process_fidelity":
        return float(1.0 / (dimension * dimension))
    if metric == "average_gate_fidelity":
        return float(1.0 / dimension)
    if metric == "in_subspace_fidelity":
        return float(1.0 / dimension)
    if metric == "fidelity":
        return float(1.0 / physical_hilbert_dimension_for_logical_dimension(dimension, n_physical))
    raise ValueError(
        "unsupported calibration metric; expected one of "
        "{'process_fidelity', 'average_gate_fidelity', 'in_subspace_fidelity', 'fidelity'}"
    )


def _calibration_metric_ci_bounds(
    record: dict[str, object],
    metric: str,
) -> tuple[float, float] | None:
    """Extract confidence-interval bounds for a specific calibration metric."""
    low_key = f"{metric}_ci_low"
    high_key = f"{metric}_ci_high"
    if low_key in record and high_key in record:
        return _record_float(record[low_key]), _record_float(record[high_key])
    return None


def _effective_t2_from_decay_ratios(
    delays_ns: Sequence[float],
    ratios: Sequence[float],
) -> float:
    """Estimate an effective exponential decay constant from normalized decay ratios."""
    if len(delays_ns) != len(ratios):
        raise ValueError("delays_ns and ratios must have the same length")
    if not delays_ns:
        raise ValueError("at least one delay point is required")

    xs: list[float] = []
    ys: list[float] = []
    for delay_ns, ratio in zip(delays_ns, ratios):
        delay_value = float(delay_ns)
        ratio_value = float(ratio)
        if delay_value <= 0.0:
            continue
        if ratio_value <= 0.0 or ratio_value >= 1.0:
            continue
        xs.append(delay_value)
        ys.append(np.log(ratio_value))
    if not xs:
        raise ValueError("no valid decay ratios were available for T2 estimation")

    numerator = float(np.dot(xs, ys))
    denominator = float(np.dot(xs, xs))
    if np.isclose(denominator, 0.0):
        raise ValueError("cannot fit a decay constant from zero-delay data only")
    slope = numerator / denominator
    if slope >= 0.0 or np.isclose(slope, 0.0):
        raise ValueError("decay fit did not produce a negative exponential slope")
    return float(-1.0 / slope)


def estimate_effective_t2_from_records(
    records: Sequence[dict[str, object]],
    *,
    dimension: int,
    n_physical: int | None = None,
    metric: str = "process_fidelity",
    fit_mode: str = "first_nonzero",
) -> dict[str, object]:
    """Estimate an effective coherence-decay time from live or simulated delay records.

    The metric is normalized above a physically motivated asymptotic floor before fitting
    an exponential decay constant. This does not claim the observable is a literal Ramsey
    coherence curve; it provides a backend-anchored effective timescale that can be reused
    to calibrate the random-telegraph switching rate.
    """
    if fit_mode not in {"first_nonzero", "regression"}:
        raise ValueError("fit_mode must be 'first_nonzero' or 'regression'")

    resolved_n = resolved_n_physical(dimension, n_physical)
    filtered = [
        record
        for record in records
        if _record_int(record.get("dimension", -1)) == dimension
        and _record_int(record.get("n_physical", -1)) == resolved_n
        and metric in record
    ]
    if not filtered:
        raise ValueError(
            f"no records found for dimension={dimension}, n_physical={resolved_n}, metric={metric}"
        )

    ordered = sorted(
        filtered,
        key=lambda record: (
            _record_float(record.get("dt_ns", _record_float(record.get("delay_dt", 0)))),
            _record_int(record.get("delay_dt", 0)),
        ),
    )
    baseline = ordered[0]
    baseline_dt_ns = baseline.get("dt_ns")
    if baseline_dt_ns is None:
        raise ValueError("records must include dt_ns to estimate an effective T2")
    baseline_time_ns = _record_float(baseline_dt_ns)
    baseline_value = _record_float(baseline[metric])
    floor = _random_telegraph_calibration_floor(metric, dimension=dimension, n_physical=resolved_n)
    if baseline_value <= floor:
        raise ValueError(
            f"baseline {metric}={baseline_value:.6f} does not sit above the calibration floor {floor:.6f}"
        )

    baseline_bounds = _calibration_metric_ci_bounds(baseline, metric)
    candidate_points: list[dict[str, object]] = []
    for record in ordered[1:]:
        dt_ns = record.get("dt_ns")
        if dt_ns is None:
            continue
        delay_ns = _record_float(dt_ns) - baseline_time_ns
        if delay_ns <= 0.0:
            continue
        value = _record_float(record[metric])
        ratio = float((value - floor) / (baseline_value - floor))
        if ratio <= 0.0 or ratio >= 1.0:
            continue

        point: dict[str, object] = {
            "delay_dt": _record_int(record.get("delay_dt", 0)),
            "delay_ns": delay_ns,
            "metric_value": value,
            "normalized_decay_ratio": ratio,
        }
        point_bounds = _calibration_metric_ci_bounds(record, metric)
        if baseline_bounds is not None and point_bounds is not None:
            denominator_low = baseline_bounds[0] - floor
            denominator_high = baseline_bounds[1] - floor
            numerator_low = point_bounds[0] - floor
            numerator_high = point_bounds[1] - floor
            if denominator_low > 0.0 and denominator_high > 0.0:
                ratio_low = numerator_low / denominator_high
                ratio_high = numerator_high / denominator_low
                if 0.0 < ratio_low < 1.0 and 0.0 < ratio_high < 1.0 and ratio_low <= ratio_high:
                    point["normalized_decay_ratio_ci_low"] = float(ratio_low)
                    point["normalized_decay_ratio_ci_high"] = float(ratio_high)
        candidate_points.append(point)

    if not candidate_points:
        raise ValueError("no positive-delay records produced a usable decay ratio")

    selected_points = (
        [candidate_points[0]] if fit_mode == "first_nonzero" else list(candidate_points)
    )
    delays_ns = [_record_float(point["delay_ns"]) for point in selected_points]
    ratios = [_record_float(point["normalized_decay_ratio"]) for point in selected_points]
    effective_t2_ns = _effective_t2_from_decay_ratios(delays_ns, ratios)

    t2_ci_low = None
    t2_ci_high = None
    if all(
        "normalized_decay_ratio_ci_low" in point and "normalized_decay_ratio_ci_high" in point
        for point in selected_points
    ):
        ratio_lows = [_record_float(point["normalized_decay_ratio_ci_low"]) for point in selected_points]
        ratio_highs = [_record_float(point["normalized_decay_ratio_ci_high"]) for point in selected_points]
        t2_ci_low = _effective_t2_from_decay_ratios(delays_ns, ratio_lows)
        t2_ci_high = _effective_t2_from_decay_ratios(delays_ns, ratio_highs)

    return {
        "dimension": dimension,
        "n_physical": resolved_n,
        "metric": metric,
        "fit_mode": fit_mode,
        "source_backend_name": baseline.get("backend_name"),
        "source_simulation_lane": baseline.get("simulation_lane"),
        "baseline_metric_value": baseline_value,
        "calibration_floor": floor,
        "baseline_dt_ns": baseline_time_ns,
        "effective_t2_ns": effective_t2_ns,
        "effective_t2_ns_ci_low": t2_ci_low,
        "effective_t2_ns_ci_high": t2_ci_high,
        "selected_points": selected_points,
    }


def calibrate_random_telegraph_from_records(
    records: Sequence[dict[str, object]],
    *,
    dimension: int,
    n_physical: int | None = None,
    metric: str = "process_fidelity",
    dt_ns_per_step: float,
    fit_mode: str = "first_nonzero",
) -> dict[str, object]:
    """Calibrate a random-telegraph switching probability from backend delay data.

    The calibration uses an effective decay constant inferred from measured delay-dependent
    observables, then sets ``tau_corr := T2_eff`` as a phenomenological matching rule. This
    is intentionally modest: it anchors the telegraph switching rate to a measured timescale
    instead of a hand-picked value without claiming a microscopic fluctuator fit.
    """
    summary = estimate_effective_t2_from_records(
        records,
        dimension=dimension,
        n_physical=n_physical,
        metric=metric,
        fit_mode=fit_mode,
    )
    dt_step = float(dt_ns_per_step)
    if dt_step <= 0.0:
        raise ValueError("dt_ns_per_step must be > 0")

    effective_t2_ns = _record_float(summary["effective_t2_ns"])
    switching_probability = correlation_time_to_switching_probability(
        effective_t2_ns,
        dt=dt_step,
    )

    switching_probability_ci_low = None
    switching_probability_ci_high = None
    t2_ci_low = summary.get("effective_t2_ns_ci_low")
    t2_ci_high = summary.get("effective_t2_ns_ci_high")
    if t2_ci_low is not None and t2_ci_high is not None:
        switching_probability_ci_low = correlation_time_to_switching_probability(
            _record_float(t2_ci_high),
            dt=dt_step,
        )
        switching_probability_ci_high = correlation_time_to_switching_probability(
            _record_float(t2_ci_low),
            dt=dt_step,
        )

    return {
        **summary,
        "dt_ns_per_step": dt_step,
        "correlation_time_ns": effective_t2_ns,
        "correlation_time_ns_ci_low": t2_ci_low,
        "correlation_time_ns_ci_high": t2_ci_high,
        "switching_probability": switching_probability,
        "switching_probability_ci_low": switching_probability_ci_low,
        "switching_probability_ci_high": switching_probability_ci_high,
        "calibration_assumption": "tau_corr := fitted effective T2 from delay data",
        "calibration_formula": "p_switch = 1 - exp(-dt_step / tau_corr)",
    }


def random_telegraph_dephasing_density_trajectory(
    logical_state: np.ndarray,
    dimension: int,
    *,
    n_physical: int | None = None,
    steps: int,
    coupling_strength: float,
    switching_probability: float,
    dt: float = 1.0,
    samples: int = 2048,
    seed: int = 7,
    histories: np.ndarray | None = None,
) -> list[np.ndarray]:
    """Monte-Carlo estimate of density matrices under random-telegraph dephasing.

    This model is motivated by slowly switching fluctuators / low-frequency flux noise:
    each qubit sees a stochastic detuning that flips sign with some switching probability,
    and coherent Z rotations accumulate between switches.
    """
    if steps < 1:
        raise ValueError("steps must be >= 1")
    embedded = embed_logical_state(logical_state, dimension, n_physical)
    n = resolved_n_physical(dimension, n_physical)
    if histories is None:
        histories = _sample_random_telegraph_histories(
            n_qubits=n,
            steps=steps,
            switching_probability=switching_probability,
            samples=samples,
            seed=seed,
        )
    if histories.shape != (samples, steps, n):
        raise ValueError(f"expected histories shape {(samples, steps, n)}, got {histories.shape}")

    accumulators = [np.zeros((2**n, 2**n), dtype=complex) for _ in range(steps + 1)]
    accumulators[0] = pure_state_density(embedded) * samples
    angle_scale = float(coupling_strength) * float(dt)
    for sample in range(samples):
        state = embedded.copy()
        for step in range(1, steps + 1):
            for qubit, sign in enumerate(histories[sample, step - 1, :]):
                state = _apply_local_z_rotation(state, qubit, n, angle_scale * float(sign))
            accumulators[step] += pure_state_density(state)
    return [rho / samples for rho in accumulators]


def random_telegraph_dephasing_observables(
    logical_state: np.ndarray,
    dimension: int,
    *,
    n_physical: int | None = None,
    steps: int,
    coupling_strength: float,
    switching_probability: float,
    dt: float = 1.0,
    samples: int = 2048,
    seed: int = 7,
) -> list[dict[str, float]]:
    """Evaluate a physically motivated random-telegraph dephasing trajectory."""
    embedded = embed_logical_state(logical_state, dimension, n_physical)
    trajectory = random_telegraph_dephasing_density_trajectory(
        logical_state,
        dimension,
        n_physical=n_physical,
        steps=steps,
        coupling_strength=coupling_strength,
        switching_probability=switching_probability,
        dt=dt,
        samples=samples,
        seed=seed,
    )
    return [
        {
            "step": step,
            "fidelity": pure_state_fidelity(embedded, rho),
            "leakage": leakage_probability(rho, dimension, n_physical),
            "in_subspace_fidelity": in_subspace_fidelity(logical_state, rho, dimension, n_physical),
        }
        for step, rho in enumerate(trajectory)
    ]


def trace_distance(rho: np.ndarray, sigma: np.ndarray) -> float:
    """Return the trace distance between two density matrices."""
    delta = np.asarray(rho, dtype=complex) - np.asarray(sigma, dtype=complex)
    singular_values = np.linalg.svd(delta, compute_uv=False)
    return 0.5 * float(np.sum(np.abs(singular_values)))


def _blp_from_density_trajectories(traj_a: Sequence[np.ndarray], traj_b: Sequence[np.ndarray]) -> dict[str, object]:
    """Compute the BLP distinguishability-backflow summary from paired trajectories."""
    distances = [trace_distance(rho_a, rho_b) for rho_a, rho_b in zip(traj_a, traj_b)]
    increments = [distances[i + 1] - distances[i] for i in range(len(distances) - 1)]
    positive_flow = [max(delta, 0.0) for delta in increments]
    return {
        "blp_measure": float(sum(positive_flow)),
        "trace_distances": distances,
        "increments": increments,
        "positive_increments": positive_flow,
    }


def blp_non_markovianity(
    state_a: np.ndarray,
    state_b: np.ndarray,
    dimension: int,
    *,
    n_physical: int | None = None,
    steps: int,
    base_phase_flip_probability: float,
    memory_strength: float,
    samples: int = 2048,
    seed: int = 7,
) -> dict[str, object]:
    """Estimate the BLP distinguishability-backflow measure from paired noisy trajectories."""
    n = resolved_n_physical(dimension, n_physical)
    histories = _sample_correlated_pauli_histories(
        n_qubits=n,
        steps=steps,
        base_phase_flip_probability=base_phase_flip_probability,
        memory_strength=memory_strength,
        samples=samples,
        seed=seed,
    )
    traj_a = correlated_memory_density_trajectory(
        state_a,
        dimension,
        n_physical=n_physical,
        steps=steps,
        base_phase_flip_probability=base_phase_flip_probability,
        memory_strength=memory_strength,
        samples=samples,
        seed=seed,
        histories=histories,
    )
    traj_b = correlated_memory_density_trajectory(
        state_b,
        dimension,
        n_physical=n_physical,
        steps=steps,
        base_phase_flip_probability=base_phase_flip_probability,
        memory_strength=memory_strength,
        samples=samples,
        seed=seed,
        histories=histories,
    )
    return _blp_from_density_trajectories(traj_a, traj_b)


def blp_random_telegraph_non_markovianity(
    state_a: np.ndarray,
    state_b: np.ndarray,
    dimension: int,
    *,
    n_physical: int | None = None,
    steps: int,
    coupling_strength: float,
    switching_probability: float,
    dt: float = 1.0,
    samples: int = 2048,
    seed: int = 7,
) -> dict[str, object]:
    """Estimate BLP non-Markovianity for random-telegraph dephasing."""
    n = resolved_n_physical(dimension, n_physical)
    histories = _sample_random_telegraph_histories(
        n_qubits=n,
        steps=steps,
        switching_probability=switching_probability,
        samples=samples,
        seed=seed,
    )
    traj_a = random_telegraph_dephasing_density_trajectory(
        state_a,
        dimension,
        n_physical=n_physical,
        steps=steps,
        coupling_strength=coupling_strength,
        switching_probability=switching_probability,
        dt=dt,
        samples=samples,
        seed=seed,
        histories=histories,
    )
    traj_b = random_telegraph_dephasing_density_trajectory(
        state_b,
        dimension,
        n_physical=n_physical,
        steps=steps,
        coupling_strength=coupling_strength,
        switching_probability=switching_probability,
        dt=dt,
        samples=samples,
        seed=seed,
        histories=histories,
    )
    return _blp_from_density_trajectories(traj_a, traj_b)


def random_telegraph_blp_probe_pair(dimension: int) -> tuple[np.ndarray, np.ndarray]:
    """Return a dephasing-sensitive logical probe pair for random-telegraph BLP scans.

    The first two Fourier modes distribute phase information across the occupied logical
    subspace. For ``dimension == 2`` this reduces to the familiar ``|+>`` and ``|->`` pair.
    """
    if dimension < 2:
        raise ValueError("dimension must be >= 2 for a two-state BLP probe pair")
    return fourier_state(dimension, 0), fourier_state(dimension, 1)


__all__ = [
    "markovian_delay_density",
    "markovian_delay_observables",
    "markovian_delay_fidelity",
    "switching_probability_to_correlation_time",
    "correlation_time_to_switching_probability",
    "estimate_effective_t2_from_records",
    "calibrate_random_telegraph_from_records",
    "random_telegraph_dephasing_density_trajectory",
    "random_telegraph_dephasing_observables",
    "correlated_memory_density_trajectory",
    "correlated_memory_observables",
    "correlated_memory_fidelity",
    "trace_distance",
    "blp_non_markovianity",
    "blp_random_telegraph_non_markovianity",
    "random_telegraph_blp_probe_pair",
    "dephasing_kraus",
    "amplitude_damping_kraus",
    "depolarizing_kraus",
]
