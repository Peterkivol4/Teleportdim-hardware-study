from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, cast

import numpy as np

from .deformation import (
    ChannelDeformationRecord,
    nonunitality_from_superoperator,
    state_fidelity_spread,
)
from .encoding import (
    delay_dt_to_ns,
    embed_logical_state,
    fill_ratio,
    physical_hilbert_dimension_for_logical_dimension,
    resolved_n_physical,
)
from .metrics import (
    average_gate_fidelity_from_process_fidelity,
    in_subspace_fidelity,
    leakage_probability,
    pure_state_density,
    pure_state_fidelity,
    renormalized_logical_subspace_density,
)
from .noise_bodies import NoiseBodyConfig, apply_noise_body_to_density, delay_dt_to_body_steps
from .process import (
    process_fidelity_to_identity,
    process_tomography_probe_states,
    reconstruct_superoperator,
)
from .simulation import (
    blp_non_markovianity,
    blp_random_telegraph_non_markovianity,
    random_telegraph_blp_probe_pair,
)
from .states import computational_basis_state, fourier_state


ProgressCallback = Callable[[str], None]


def _emit_progress(progress: ProgressCallback | None, message: str) -> None:
    """Emit optional progress output for long channel-body sweeps."""
    if progress is not None:
        progress(message)


def _dimension_grid(n_physical_values: Sequence[int], dimensions: Sequence[int] | None) -> list[tuple[int, int]]:
    """Build the valid ``(n_physical, dimension)`` grid for channel-body sweeps."""
    grid: list[tuple[int, int]] = []
    for n_physical in n_physical_values:
        if n_physical < 1:
            raise ValueError("n_physical values must be >= 1")
        maximum_dimension = 2**n_physical
        selected_dimensions = list(range(2, maximum_dimension + 1)) if dimensions is None else list(dimensions)
        for dimension in selected_dimensions:
            if dimension < 2:
                raise ValueError("dimensions must be >= 2")
            if dimension > maximum_dimension:
                raise ValueError(
                    f"dimension={dimension} does not fit in n_physical={n_physical}"
                )
            grid.append((n_physical, dimension))
    return grid


def _body_config(
    *,
    body: str,
    strength: float,
    memory_strength: float,
    correlation: float,
    coherent_angle: float,
    seed: int,
) -> NoiseBodyConfig:
    """Create a validated body configuration from sweep-level knobs."""
    return NoiseBodyConfig(
        body=body,
        strength=float(strength),
        correlation=float(correlation),
        memory_strength=float(memory_strength),
        coherent_angle=float(coherent_angle),
        leakage_rate=float(strength) if body == "leakage_mixing" else 0.0,
        readout_error=float(strength) if body == "readout" else 0.0,
        seed=seed,
    )


def _blp_score_for_body(
    *,
    dimension: int,
    n_physical: int,
    body_config: NoiseBodyConfig,
    delay_dt: int,
    samples: int,
    seed: int,
) -> float | None:
    """Evaluate a BLP score only for bodies with explicit memory dynamics."""
    steps = delay_dt_to_body_steps(delay_dt)
    if body_config.body == "correlated_memory":
        state_a = computational_basis_state(dimension, 0)
        state_b = fourier_state(dimension, 0)
        result = blp_non_markovianity(
            state_a,
            state_b,
            dimension,
            n_physical=n_physical,
            steps=steps,
            base_phase_flip_probability=body_config.strength,
            memory_strength=body_config.memory_strength,
            samples=samples,
            seed=seed,
        )
        return float(cast(float, result["blp_measure"]))
    if body_config.body == "random_telegraph":
        state_a, state_b = random_telegraph_blp_probe_pair(dimension)
        result = blp_random_telegraph_non_markovianity(
            state_a,
            state_b,
            dimension,
            n_physical=n_physical,
            steps=steps,
            coupling_strength=body_config.correlation if body_config.correlation > 0.0 else 0.4,
            switching_probability=body_config.strength,
            samples=samples,
            seed=seed,
        )
        return float(cast(float, result["blp_measure"]))
    return None


def evaluate_channel_body_record(
    *,
    dimension: int,
    n_physical: int,
    body_config: NoiseBodyConfig,
    delay_dt: int,
    shots: int = 4096,
    samples: int = 2048,
    dt_ns_per_dt: float | None = None,
) -> dict[str, Any]:
    """Evaluate one dimension/body/delay point as a deformation-record dictionary."""
    probes = process_tomography_probe_states(dimension)
    input_densities = [pure_state_density(probe) for probe in probes]
    output_physical_densities = [
        apply_noise_body_to_density(
            probe,
            dimension,
            body_config,
            n_physical=n_physical,
            delay_dt=delay_dt,
            samples=samples,
        )
        for probe in probes
    ]
    output_logical_densities = [
        renormalized_logical_subspace_density(rho, dimension, n_physical)
        for rho in output_physical_densities
    ]
    superoperator = reconstruct_superoperator(input_densities, output_logical_densities)
    process_fidelity = process_fidelity_to_identity(superoperator, dimension)
    average_gate_fidelity = average_gate_fidelity_from_process_fidelity(
        process_fidelity,
        dimension,
    )
    nonunitality = nonunitality_from_superoperator(superoperator, dimension)

    fidelities: list[float] = []
    leakages: list[float] = []
    subspace_fidelities: list[float] = []
    for probe, rho in zip(probes, output_physical_densities):
        embedded = embed_logical_state(probe, dimension, n_physical)
        fidelities.append(pure_state_fidelity(embedded, rho))
        leakages.append(leakage_probability(rho, dimension, n_physical))
        subspace_fidelities.append(in_subspace_fidelity(probe, rho, dimension, n_physical))

    anisotropy, state_spread = state_fidelity_spread(fidelities)
    blp_score = _blp_score_for_body(
        dimension=dimension,
        n_physical=n_physical,
        body_config=body_config,
        delay_dt=delay_dt,
        samples=samples,
        seed=body_config.seed or 7,
    )
    record = ChannelDeformationRecord(
        dimension=dimension,
        n_physical=n_physical,
        fill_ratio=fill_ratio(dimension, n_physical),
        body=body_config.body,
        body_strength=body_config.strength,
        delay_dt=int(delay_dt),
        fidelity=float(np.mean(fidelities)),
        leakage=float(np.mean(leakages)),
        in_subspace_fidelity=float(np.mean(subspace_fidelities)),
        process_fidelity=process_fidelity,
        average_gate_fidelity=average_gate_fidelity,
        blp_score=blp_score,
        nonunitality=nonunitality,
        anisotropy=anisotropy,
        state_spread=state_spread,
    ).to_dict()
    record.update(
        {
            "physical_hilbert_dimension": physical_hilbert_dimension_for_logical_dimension(
                dimension,
                n_physical,
            ),
            "dt_ns": delay_dt_to_ns(delay_dt, dt_ns_per_dt=dt_ns_per_dt),
            "shots": int(shots),
            "samples": int(samples),
            "simulation_lane": "channel_body_model",
            "body_correlation": body_config.correlation,
            "memory_strength": body_config.memory_strength,
            "coherent_angle": body_config.coherent_angle,
            "leakage_rate": body_config.leakage_rate,
            "readout_error": body_config.readout_error,
            "body_steps": delay_dt_to_body_steps(delay_dt),
        }
    )
    return record


def run_channel_body_sweep(
    n_physical_values: Sequence[int],
    *,
    dimensions: Sequence[int] | None,
    bodies: Sequence[str],
    strengths: Sequence[float],
    delays: Sequence[int],
    shots: int = 4096,
    samples: int = 2048,
    memory_strength: float = 0.8,
    correlation: float = 0.4,
    coherent_angle: float = 0.0,
    dt_ns_per_dt: float | None = None,
    seed: int = 7,
    progress: ProgressCallback | None = None,
) -> list[dict[str, Any]]:
    """Run a controlled theory-level sweep over channel-deformation bodies."""
    if not bodies:
        raise ValueError("bodies cannot be empty")
    if not strengths:
        raise ValueError("strengths cannot be empty")
    if not delays:
        raise ValueError("delays cannot be empty")
    grid = _dimension_grid(n_physical_values, dimensions)
    total = len(grid) * len(bodies) * len(strengths) * len(delays)
    records: list[dict[str, Any]] = []
    completed = 0
    for n_physical, dimension in grid:
        resolved_n = resolved_n_physical(dimension, n_physical)
        for body in bodies:
            if body == "hardware":
                raise ValueError("hardware is a record label, not a synthetic channel-body sweep")
            for strength in strengths:
                for delay_dt in delays:
                    completed += 1
                    _emit_progress(
                        progress,
                        (
                            f"channel-body sweep {completed}/{total}: "
                            f"d={dimension}, n={resolved_n}, body={body}, "
                            f"strength={float(strength):.4g}, delay_dt={int(delay_dt)}"
                        ),
                    )
                    body_config = _body_config(
                        body=body,
                        strength=float(strength),
                        memory_strength=memory_strength,
                        correlation=correlation,
                        coherent_angle=coherent_angle,
                        seed=seed + completed,
                    )
                    records.append(
                        evaluate_channel_body_record(
                            dimension=dimension,
                            n_physical=resolved_n,
                            body_config=body_config,
                            delay_dt=int(delay_dt),
                            shots=shots,
                            samples=samples,
                            dt_ns_per_dt=dt_ns_per_dt,
                        )
                    )
    return records


__all__ = [
    "evaluate_channel_body_record",
    "run_channel_body_sweep",
]
