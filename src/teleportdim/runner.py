"""High-level execution helpers for reproducible TeleportDim runs.

This module owns small orchestration logic that is shared by scripts, notebooks,
and the CLI: delay-grid parsing, fixed-``n`` sweep construction, artifact writing,
and common theory/Aer run wrappers. Hardware shots are raw shot counts. Delay
values are backend ``dt`` ticks unless a record also carries a ``dt_ns`` field.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from .aer import run_aer_delay_sweep, run_aer_process_tomography
from .cli import app, main
from .config import BackendConfig, SweepConfig
from .reports import (
    plot_metric_vs_delay,
    plot_metric_vs_fill_ratio,
    save_csv,
    save_json,
)
from .sweeps import (
    fixed_n_dimensions,
    fixed_n_sweep_configs,
    make_probe_state,
    run_aer_fixed_n_sweep,
    run_blp_memory_scan,
    run_blp_random_telegraph_scan,
    run_correlated_memory_fixed_n_sweep,
    run_hardware_delay_sweep,
    run_hardware_fixed_n_process_tomography,
    run_hardware_fixed_n_sweep,
    run_hardware_process_tomography,
    run_markovian_fixed_n_sweep,
    run_multi_backend_fixed_n_process_tomography,
    run_multi_backend_fixed_n_sweep,
    summarize_results,
)

StateFamily = Literal["haar", "computational", "fourier"]


@dataclass(slots=True)
class RunArtifacts:
    """Filesystem paths produced by a runner invocation.

    Paths are local filesystem locations. JSON/CSV artifacts contain dimensionless
    fidelity-like metrics and raw shot-count metadata; plot paths usually point to
    PNG files whose x-axis is nanoseconds when records include ``dt_ns``.
    """

    json_path: Path | None = None
    csv_path: Path | None = None
    plots: dict[str, Path] = field(default_factory=dict)


def parse_delay_grid(delays: str | Sequence[int]) -> list[int]:
    """Parse a delay grid expressed in backend ``dt`` ticks.

    ``delays`` may be a comma-separated CLI string such as ``"0,64,128"`` or a
    sequence of integer tick counts. The returned values are non-negative integer
    backend ``dt`` units, not nanoseconds.
    """

    if isinstance(delays, str):
        parsed = [int(item.strip()) for item in delays.split(",") if item.strip()]
    else:
        parsed = [int(item) for item in delays]
    if not parsed:
        raise ValueError("delay grid cannot be empty")
    if any(delay < 0 for delay in parsed):
        raise ValueError("delay grid values must be non-negative dt ticks")
    return parsed


def build_fixed_n_runner_configs(
    n_values: Sequence[int],
    *,
    delay_dt_values: str | Sequence[int],
    shots: int | None = None,
    state_family: StateFamily = "haar",
    random_seed: int = 7,
) -> list[SweepConfig]:
    """Build fixed-physical-qubit sweep configs for runner entrypoints.

    ``n_values`` are physical qubit counts. ``delay_dt_values`` are backend ``dt``
    tick counts. ``shots``, when provided, is a raw shot count copied into each
    returned sweep configuration.
    """

    configs = fixed_n_sweep_configs(
        [int(value) for value in n_values],
        delay_dt_values=parse_delay_grid(delay_dt_values),
        state_family=state_family,
        random_seed=random_seed,
    )
    if shots is not None:
        if shots < 1:
            raise ValueError("shots must be >= 1")
        for config in configs:
            config.shots = int(shots)
    return configs


def write_run_artifacts(
    records: Sequence[dict[str, Any]],
    output_stem: str | Path | None,
    *,
    delay_metrics: Sequence[str] = ("fidelity", "leakage"),
    fill_ratio_metrics: Sequence[str] = (),
) -> RunArtifacts:
    """Write JSON, CSV, and optional plots for a run.

    Metrics are unitless. Plot generation is skipped for metrics absent from the
    first record so callers can use the same helper for state, process, and BLP
    runs without special casing every output schema.
    """

    if output_stem is None:
        return RunArtifacts()

    stem = Path(output_stem)
    artifacts = RunArtifacts(
        json_path=save_json(records, stem.with_suffix(".json")),
        csv_path=save_csv(records, stem.with_suffix(".csv")),
    )
    if not records:
        return artifacts

    first = records[0]
    for metric in delay_metrics:
        if metric in first:
            artifacts.plots[f"{metric}_delay"] = plot_metric_vs_delay(
                records,
                metric=metric,
                path=stem.parent / f"{stem.name}_{metric}.png",
            )
    for metric in fill_ratio_metrics:
        if metric in first:
            artifacts.plots[f"{metric}_fill_ratio"] = plot_metric_vs_fill_ratio(
                records,
                metric=metric,
                path=stem.parent / f"{stem.name}_phi_{metric}.png",
            )
    return artifacts


def run_markovian_fixed_n_with_artifacts(
    n_values: Sequence[int],
    *,
    delay_dt_values: str | Sequence[int],
    output_stem: str | Path | None = None,
    **kwargs: Any,
) -> tuple[list[dict[str, Any]], RunArtifacts]:
    """Run the theory-lane fixed-``n`` sweep and write optional artifacts.

    Delay values are backend-style ``dt`` ticks for consistency with Aer/hardware
    records, although the Markovian model interprets them as caller-chosen model
    units unless ``dt_ns_per_dt`` is supplied.
    """

    configs = build_fixed_n_runner_configs(n_values, delay_dt_values=delay_dt_values)
    records = run_markovian_fixed_n_sweep(configs, **kwargs)
    artifacts = write_run_artifacts(
        records,
        output_stem,
        delay_metrics=("fidelity", "leakage", "in_subspace_fidelity"),
        fill_ratio_metrics=("fidelity",),
    )
    return records, artifacts


def run_aer_fixed_n_with_artifacts(
    n_values: Sequence[int],
    *,
    delay_dt_values: str | Sequence[int],
    shots: int,
    output_stem: str | Path | None = None,
    **kwargs: Any,
) -> tuple[list[dict[str, Any]], RunArtifacts]:
    """Run the circuit-level Aer fixed-``n`` sweep and write optional artifacts.

    ``shots`` is the raw simulator shot count per tomography setting. Delay values
    are backend ``dt`` ticks and are converted to nanoseconds in output records when
    ``dt_ns_per_dt`` is supplied.
    """

    configs = build_fixed_n_runner_configs(
        n_values,
        delay_dt_values=delay_dt_values,
        shots=shots,
    )
    records = run_aer_fixed_n_sweep(configs, **kwargs)
    artifacts = write_run_artifacts(
        records,
        output_stem,
        delay_metrics=("fidelity", "leakage", "in_subspace_fidelity"),
        fill_ratio_metrics=("fidelity",),
    )
    return records, artifacts


__all__ = [
    "BackendConfig",
    "RunArtifacts",
    "SweepConfig",
    "app",
    "build_fixed_n_runner_configs",
    "fixed_n_dimensions",
    "fixed_n_sweep_configs",
    "main",
    "make_probe_state",
    "parse_delay_grid",
    "run_aer_delay_sweep",
    "run_aer_fixed_n_sweep",
    "run_aer_fixed_n_with_artifacts",
    "run_aer_process_tomography",
    "run_blp_memory_scan",
    "run_blp_random_telegraph_scan",
    "run_correlated_memory_fixed_n_sweep",
    "run_hardware_delay_sweep",
    "run_hardware_fixed_n_process_tomography",
    "run_hardware_fixed_n_sweep",
    "run_hardware_process_tomography",
    "run_markovian_fixed_n_sweep",
    "run_markovian_fixed_n_with_artifacts",
    "run_multi_backend_fixed_n_process_tomography",
    "run_multi_backend_fixed_n_sweep",
    "summarize_results",
    "write_run_artifacts",
]
