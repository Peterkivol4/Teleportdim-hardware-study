from __future__ import annotations

from .encoding import embed_logical_state
from .metrics import (
    average_gate_fidelity_from_process_fidelity,
    counts_to_probabilities,
    in_subspace_fidelity,
    leakage_probability,
    pure_state_density,
    pure_state_fidelity,
    renormalized_logical_subspace_density,
)
from .process import process_fidelity_to_identity, reconstruct_superoperator
from .tomography import reconstruct_density_matrix

from collections.abc import Sequence

import numpy as np


def resample_counts_multinomial(
    counts: dict[str, int],
    *,
    rng: np.random.Generator,
) -> dict[str, int]:
    """Resample a count dictionary with multinomial shot noise."""
    if not counts:
        raise ValueError("counts cannot be empty")
    labels = sorted(counts)
    probabilities = counts_to_probabilities(counts)
    shots = int(sum(counts.values()))
    sampled = rng.multinomial(shots, [probabilities[label] for label in labels])
    return {
        label: int(value)
        for label, value in zip(labels, sampled)
        if int(value) > 0
    }


def _confidence_interval_bounds(values: Sequence[float], confidence_level: float) -> tuple[float, float]:
    """Return a percentile bootstrap confidence interval."""
    if not 0.0 < confidence_level < 1.0:
        raise ValueError("confidence_level must be between 0 and 1")
    array = np.asarray(values, dtype=float)
    if array.size == 0:
        raise ValueError("values cannot be empty")
    tail = 0.5 * (1.0 - confidence_level)
    low, high = np.quantile(array, [tail, 1.0 - tail])
    return float(low), float(high)


def bootstrap_confidence_interval_from_samples(
    samples: Sequence[float],
    *,
    confidence_level: float = 0.95,
) -> tuple[float, float]:
    """Return a percentile interval for unitless scalar bootstrap samples.

    ``samples`` contains bootstrap estimates for one unitless observable, such as state
    fidelity, leakage, process fidelity, or average gate fidelity. The returned lower and
    upper bounds are in the same unitless scale as the samples.
    """
    return _confidence_interval_bounds(samples, confidence_level)


def bootstrap_tomography_metrics(
    logical_target: np.ndarray,
    dimension: int,
    setting_counts: dict[str, dict[str, int]],
    *,
    n_physical: int | None = None,
    bootstrap_samples: int = 200,
    confidence_level: float = 0.95,
    seed: int | None = None,
) -> dict[str, float]:
    """Bootstrap confidence intervals for fidelity, leakage, and in-subspace fidelity."""
    if bootstrap_samples < 1:
        raise ValueError("bootstrap_samples must be >= 1")

    rng = np.random.default_rng(seed)
    fidelity_values: list[float] = []
    leakage_values: list[float] = []
    in_subspace_values: list[float] = []
    embedded_target = embed_logical_state(logical_target, dimension, n_physical)

    for _ in range(bootstrap_samples):
        resampled_setting_counts = {
            basis: resample_counts_multinomial(counts, rng=rng)
            for basis, counts in setting_counts.items()
        }
        rho = reconstruct_density_matrix(resampled_setting_counts)
        fidelity_values.append(pure_state_fidelity(embedded_target, rho))
        leakage_values.append(leakage_probability(rho, dimension, n_physical))
        in_subspace_values.append(in_subspace_fidelity(logical_target, rho, dimension, n_physical))

    fidelity_ci_low, fidelity_ci_high = _confidence_interval_bounds(fidelity_values, confidence_level)
    leakage_ci_low, leakage_ci_high = _confidence_interval_bounds(leakage_values, confidence_level)
    in_subspace_ci_low, in_subspace_ci_high = _confidence_interval_bounds(in_subspace_values, confidence_level)
    return {
        "confidence_level": float(confidence_level),
        "bootstrap_samples": int(bootstrap_samples),
        "fidelity_bootstrap_mean": float(np.mean(fidelity_values)),
        "leakage_bootstrap_mean": float(np.mean(leakage_values)),
        "in_subspace_fidelity_bootstrap_mean": float(np.mean(in_subspace_values)),
        "fidelity_ci_low": fidelity_ci_low,
        "fidelity_ci_high": fidelity_ci_high,
        "leakage_ci_low": leakage_ci_low,
        "leakage_ci_high": leakage_ci_high,
        "in_subspace_fidelity_ci_low": in_subspace_ci_low,
        "in_subspace_fidelity_ci_high": in_subspace_ci_high,
    }


def bootstrap_average_tomography_metrics(
    logical_targets: Sequence[np.ndarray],
    dimension: int,
    setting_counts_by_target: Sequence[dict[str, dict[str, int]]],
    *,
    n_physical: int | None = None,
    bootstrap_samples: int = 200,
    confidence_level: float = 0.95,
    seed: int | None = None,
) -> dict[str, float]:
    """Bootstrap confidence intervals for canonical-probe averages."""
    if len(logical_targets) != len(setting_counts_by_target):
        raise ValueError("logical_targets and setting_counts_by_target must have the same length")
    if bootstrap_samples < 1:
        raise ValueError("bootstrap_samples must be >= 1")

    rng = np.random.default_rng(seed)
    fidelity_values: list[float] = []
    leakage_values: list[float] = []
    in_subspace_values: list[float] = []

    for _ in range(bootstrap_samples):
        per_probe_fidelity: list[float] = []
        per_probe_leakage: list[float] = []
        per_probe_in_subspace: list[float] = []
        for logical_target, setting_counts in zip(logical_targets, setting_counts_by_target):
            resampled_setting_counts = {
                basis: resample_counts_multinomial(counts, rng=rng)
                for basis, counts in setting_counts.items()
            }
            rho = reconstruct_density_matrix(resampled_setting_counts)
            embedded_target = embed_logical_state(logical_target, dimension, n_physical)
            per_probe_fidelity.append(pure_state_fidelity(embedded_target, rho))
            per_probe_leakage.append(leakage_probability(rho, dimension, n_physical))
            per_probe_in_subspace.append(in_subspace_fidelity(logical_target, rho, dimension, n_physical))
        fidelity_values.append(float(np.mean(per_probe_fidelity)))
        leakage_values.append(float(np.mean(per_probe_leakage)))
        in_subspace_values.append(float(np.mean(per_probe_in_subspace)))

    fidelity_ci_low, fidelity_ci_high = _confidence_interval_bounds(fidelity_values, confidence_level)
    leakage_ci_low, leakage_ci_high = _confidence_interval_bounds(leakage_values, confidence_level)
    in_subspace_ci_low, in_subspace_ci_high = _confidence_interval_bounds(in_subspace_values, confidence_level)
    return {
        "confidence_level": float(confidence_level),
        "bootstrap_samples": int(bootstrap_samples),
        "avg_probe_fidelity_bootstrap_mean": float(np.mean(fidelity_values)),
        "avg_probe_leakage_bootstrap_mean": float(np.mean(leakage_values)),
        "avg_probe_in_subspace_fidelity_bootstrap_mean": float(np.mean(in_subspace_values)),
        "avg_probe_fidelity_ci_low": fidelity_ci_low,
        "avg_probe_fidelity_ci_high": fidelity_ci_high,
        "avg_probe_leakage_ci_low": leakage_ci_low,
        "avg_probe_leakage_ci_high": leakage_ci_high,
        "avg_probe_in_subspace_fidelity_ci_low": in_subspace_ci_low,
        "avg_probe_in_subspace_fidelity_ci_high": in_subspace_ci_high,
    }


def bootstrap_process_tomography_metrics(
    dimension: int,
    input_states: Sequence[np.ndarray],
    setting_counts_by_target: Sequence[dict[str, dict[str, int]]],
    *,
    n_physical: int | None = None,
    bootstrap_samples: int = 200,
    confidence_level: float = 0.95,
    seed: int | None = None,
) -> dict[str, float]:
    """Bootstrap confidence intervals for process and average gate fidelity."""
    if len(input_states) != len(setting_counts_by_target):
        raise ValueError("input_states and setting_counts_by_target must have the same length")
    if bootstrap_samples < 1:
        raise ValueError("bootstrap_samples must be >= 1")

    rng = np.random.default_rng(seed)
    process_values: list[float] = []
    gate_values: list[float] = []

    input_densities = [pure_state_density(state) for state in input_states]
    for _ in range(bootstrap_samples):
        output_densities: list[np.ndarray] = []
        for setting_counts in setting_counts_by_target:
            resampled_setting_counts = {
                basis: resample_counts_multinomial(counts, rng=rng)
                for basis, counts in setting_counts.items()
            }
            rho = reconstruct_density_matrix(resampled_setting_counts)
            output_densities.append(renormalized_logical_subspace_density(rho, dimension, n_physical))
        superoperator = reconstruct_superoperator(input_densities, output_densities)
        process_fidelity = process_fidelity_to_identity(superoperator, dimension)
        process_values.append(process_fidelity)
        gate_values.append(average_gate_fidelity_from_process_fidelity(process_fidelity, dimension))

    process_ci_low, process_ci_high = _confidence_interval_bounds(process_values, confidence_level)
    gate_ci_low, gate_ci_high = _confidence_interval_bounds(gate_values, confidence_level)
    return {
        "confidence_level": float(confidence_level),
        "bootstrap_samples": int(bootstrap_samples),
        "process_fidelity_bootstrap_mean": float(np.mean(process_values)),
        "average_gate_fidelity_bootstrap_mean": float(np.mean(gate_values)),
        "process_fidelity_ci_low": process_ci_low,
        "process_fidelity_ci_high": process_ci_high,
        "average_gate_fidelity_ci_low": gate_ci_low,
        "average_gate_fidelity_ci_high": gate_ci_high,
    }


def bootstrap_probe_mean_observables(
    probe_observables: Sequence[dict[str, float]],
    *,
    bootstrap_samples: int = 200,
    confidence_level: float = 0.95,
    seed: int | None = None,
) -> dict[str, object]:
    """Bootstrap the mean observables of a finite logical probe ensemble."""
    if not probe_observables:
        raise ValueError("probe_observables cannot be empty")
    if bootstrap_samples < 1:
        raise ValueError("bootstrap_samples must be >= 1")

    metrics = ("fidelity", "leakage", "in_subspace_fidelity")
    rng = np.random.default_rng(seed)
    sample_size = len(probe_observables)
    values: dict[str, list[float]] = {metric: [] for metric in metrics}

    for _ in range(bootstrap_samples):
        indices = rng.integers(0, sample_size, size=sample_size)
        for metric in metrics:
            values[metric].append(float(np.mean([probe_observables[index][metric] for index in indices])))

    summary = {
        "confidence_level": float(confidence_level),
        "bootstrap_samples": int(bootstrap_samples),
        "ci_method": "probe_resampling",
    }
    for metric in metrics:
        low, high = _confidence_interval_bounds(values[metric], confidence_level)
        summary[f"{metric}_ci_low"] = low
        summary[f"{metric}_ci_high"] = high
        summary[f"avg_probe_{metric}_ci_low"] = low
        summary[f"avg_probe_{metric}_ci_high"] = high
    return summary


__all__ = [
    "resample_counts_multinomial",
    "bootstrap_tomography_metrics",
    "bootstrap_average_tomography_metrics",
    "bootstrap_process_tomography_metrics",
    "bootstrap_probe_mean_observables",
    "bootstrap_confidence_interval_from_samples",
]
