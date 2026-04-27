from __future__ import annotations

from typing import Any, cast
import sys

from .aer import AerExecutionError, build_basic_noise_model, run_aer_delay_sweep, run_aer_process_tomography
from .config import (
    BackendConfig,
    CorrectionMode,
    DEFAULT_AER_DT_NS_PER_DT,
    DEFAULT_AER_T1_SECONDS,
    DEFAULT_AER_T2_SECONDS,
    SweepConfig,
)
from .fingerprinting import (
    save_body_fingerprint_markdown_report,
    save_channel_body_markdown_report,
)
from .reports import (
    _normalize_path,
    load_backend_fixed_n_summary_rows,
    load_fixed_n_summary_rows,
    load_json_records,
    plot_blp_vs_memory_strength,
    plot_blp_vs_switching_probability,
    plot_hardware_theory_curves,
    plot_hardware_theory_divergence,
    plot_metric_vs_delay,
    plot_metric_vs_fill_ratio,
    save_backend_fixed_n_markdown_report,
    save_blp_markdown_report,
    save_csv,
    save_fixed_n_markdown_report,
    save_hardware_theory_divergence_markdown_report,
    save_json,
    save_random_telegraph_calibration_markdown_report,
    save_three_lane_fixed_n_markdown_report,
    summarize_backend_fixed_n_table,
    summarize_fixed_n_comparison,
    summarize_hardware_theory_divergence,
    summarize_three_lane_fixed_n_table,
)
from .simulation import (
    blp_non_markovianity,
    calibrate_random_telegraph_from_records,
    correlated_memory_observables,
    markovian_delay_observables,
)
from .states import computational_basis_state, fourier_state, random_haar_state
from .sweeps import (
    fixed_n_sweep_configs,
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
from .body_sweeps import run_channel_body_sweep

import json

import typer


app = typer.Typer(no_args_is_help=True)


def _api(name: str) -> Any:
    """Resolve public API functions through the package root for monkeypatch compatibility."""
    package = sys.modules.get("teleportdim")
    if package is None:
        return globals()[name]
    return getattr(package, name)


def _correction_mode(value: str) -> CorrectionMode:
    """Validate and narrow a CLI correction-mode string."""
    if value not in {"dynamic", "deferred"}:
        raise typer.BadParameter("correction_mode must be 'dynamic' or 'deferred'")
    return cast(CorrectionMode, value)


def _csv_ints(value: str) -> list[int]:
    """Parse a comma-separated integer CLI option."""
    return [int(item.strip()) for item in value.split(",") if item.strip()]


def _csv_floats(value: str) -> list[float]:
    """Parse a comma-separated float CLI option."""
    return [float(item.strip()) for item in value.split(",") if item.strip()]


def _csv_strings(value: str) -> list[str]:
    """Parse a comma-separated string CLI option."""
    return [item.strip() for item in value.split(",") if item.strip()]



def _echo_records_or_paths(records: list[dict[str, Any]], *, output_stem: str | None = None, plot_delay: bool = True) -> None:
    """Utility function used by the TeleportDim experiment toolkit."""
    typer.echo(summarize_results(records), err=True)
    if output_stem is None:
        typer.echo(json.dumps(records, indent=2))
        return
    save_json(records, f"{output_stem}.json")
    save_csv(records, f"{output_stem}.csv")
    if plot_delay:
        plot_metric_vs_delay(records, metric="fidelity", path=f"{output_stem}_fidelity.png")
        plot_metric_vs_delay(records, metric="leakage", path=f"{output_stem}_leakage.png")


@app.command()
def hardware_delay_sweep(
    dimension: int = typer.Option(..., help="Logical Hilbert-space dimension."),
    n_physical: int | None = typer.Option(None, help="Optional explicit physical qubit count for fixed-n hardware comparisons."),
    backend_name: str | None = typer.Option(None, help="IBM backend name."),
    shots: int = typer.Option(2048, help="Number of shots per tomography setting."),
    correction_mode: str = typer.Option("dynamic", help="dynamic or deferred."),
    delays: str = typer.Option("0,64,128", help="Comma-separated delay values in dt units."),
    output_stem: str | None = typer.Option(None, help="Optional file stem for json/csv/plots."),
) -> None:
    """Typer CLI command for the TeleportDim experiment toolkit."""
    sweep = SweepConfig(
        dimension=dimension,
        n_physical=n_physical,
        delay_dt_values=[int(x.strip()) for x in delays.split(",") if x.strip()],
        shots=shots,
    )
    backend = BackendConfig(
        backend_name=backend_name,
        shots=shots,
        correction_mode=_correction_mode(correction_mode),
    )
    records = _api("run_hardware_delay_sweep")(sweep, backend)
    _echo_records_or_paths(records, output_stem=output_stem)


@app.command()
def hardware_fixed_n_sweep(
    n_values: str = typer.Option("2", help="Comma-separated fixed physical-qubit counts."),
    backend_name: str | None = typer.Option(None, help="IBM backend name."),
    shots: int = typer.Option(2048, help="Number of shots per tomography setting."),
    correction_mode: str = typer.Option("dynamic", help="dynamic or deferred."),
    delays: str = typer.Option("0,64,128", help="Comma-separated delay values in dt units."),
    bootstrap_samples: int = typer.Option(0, help="Optional number of bootstrap resamples for tomography confidence intervals."),
    confidence_level: float = typer.Option(0.95, help="Confidence level for bootstrap intervals."),
    output_stem: str | None = typer.Option(None, help="Optional file stem for json/csv/plots."),
) -> None:
    """Run a fixed-``n`` canonical-probe hardware sweep for d=2..2^n on IBM Runtime."""
    configs = fixed_n_sweep_configs(
        [int(x.strip()) for x in n_values.split(",") if x.strip()],
        delay_dt_values=[int(x.strip()) for x in delays.split(",") if x.strip()],
    )
    backend = BackendConfig(
        backend_name=backend_name,
        shots=shots,
        correction_mode=_correction_mode(correction_mode),
    )
    records = _api("run_hardware_fixed_n_sweep")(
        configs,
        backend,
        bootstrap_samples=bootstrap_samples,
        confidence_level=confidence_level,
        progress=lambda message: typer.echo(message, err=True),
    )
    _echo_records_or_paths(records, output_stem=output_stem)


@app.command()
def hardware_multi_backend_fixed_n_sweep(
    n_values: str = typer.Option("2", help="Comma-separated fixed physical-qubit counts."),
    backend_names: str = typer.Option(..., help="Comma-separated IBM backend names."),
    shots: int = typer.Option(2048, help="Number of shots per tomography setting."),
    correction_mode: str = typer.Option("dynamic", help="dynamic or deferred."),
    delays: str = typer.Option("0,64,128", help="Comma-separated delay values in dt units."),
    bootstrap_samples: int = typer.Option(0, help="Optional number of bootstrap resamples for tomography confidence intervals."),
    confidence_level: float = typer.Option(0.95, help="Confidence level for bootstrap intervals."),
    output_stem: str | None = typer.Option(None, help="Optional file stem for json/csv outputs."),
) -> None:
    """Run the fixed-n hardware sweep on multiple IBM backends."""
    configs = fixed_n_sweep_configs(
        [int(x.strip()) for x in n_values.split(",") if x.strip()],
        delay_dt_values=[int(x.strip()) for x in delays.split(",") if x.strip()],
    )
    backend_configs = [
        BackendConfig(
            backend_name=item.strip(),
            shots=shots,
            correction_mode=_correction_mode(correction_mode),
        )
        for item in backend_names.split(",")
        if item.strip()
    ]
    records = _api("run_multi_backend_fixed_n_sweep")(
        configs,
        backend_configs,
        bootstrap_samples=bootstrap_samples,
        confidence_level=confidence_level,
        progress=lambda message: typer.echo(message, err=True),
    )
    _echo_records_or_paths(records, output_stem=output_stem, plot_delay=False)


@app.command()
def hardware_process_tomography(
    dimension: int = typer.Option(..., help="Logical Hilbert-space dimension."),
    n_physical: int | None = typer.Option(None, help="Optional explicit physical qubit count for fixed-n embeddings."),
    backend_name: str | None = typer.Option(None, help="IBM backend name."),
    shots: int = typer.Option(2048, help="Number of shots per tomography setting."),
    correction_mode: str = typer.Option("dynamic", help="dynamic or deferred."),
    delays: str = typer.Option("0,64,128", help="Comma-separated delay values in dt units."),
    bootstrap_samples: int = typer.Option(0, help="Optional number of bootstrap resamples for CIs."),
    confidence_level: float = typer.Option(0.95, help="Confidence level for bootstrap intervals."),
    output_stem: str | None = typer.Option(None, help="Optional file stem for json/csv/plots."),
) -> None:
    """Run logical process tomography on IBM Runtime hardware."""
    sweep = SweepConfig(
        dimension=dimension,
        n_physical=n_physical,
        delay_dt_values=[int(x.strip()) for x in delays.split(",") if x.strip()],
        shots=shots,
    )
    backend = BackendConfig(
        backend_name=backend_name,
        shots=shots,
        correction_mode=_correction_mode(correction_mode),
    )
    records = _api("run_hardware_process_tomography")(
        sweep,
        backend,
        bootstrap_samples=bootstrap_samples,
        confidence_level=confidence_level,
        progress=lambda msg: typer.echo(msg, err=True),
    )
    _echo_records_or_paths(records, output_stem=output_stem)
    if output_stem:
        plot_metric_vs_delay(
            records,
            metric="process_fidelity",
            path=f"{output_stem}_process_fidelity.png",
        )


@app.command()
def hardware_fixed_n_process_tomography(
    n_values: str = typer.Option("2", help="Comma-separated fixed physical-qubit counts."),
    backend_name: str | None = typer.Option(None, help="IBM backend name."),
    shots: int = typer.Option(2048, help="Number of shots per tomography setting."),
    correction_mode: str = typer.Option("dynamic", help="dynamic or deferred."),
    delays: str = typer.Option("0,64,128", help="Comma-separated delay values in dt units."),
    bootstrap_samples: int = typer.Option(0, help="Optional number of bootstrap resamples for CIs."),
    confidence_level: float = typer.Option(0.95, help="Confidence level for bootstrap intervals."),
    output_stem: str | None = typer.Option(None, help="Optional file stem for json/csv/plots."),
) -> None:
    """Run fixed-``n`` logical process tomography on IBM Runtime hardware."""
    configs = fixed_n_sweep_configs(
        [int(x.strip()) for x in n_values.split(",") if x.strip()],
        delay_dt_values=[int(x.strip()) for x in delays.split(",") if x.strip()],
    )
    backend = BackendConfig(
        backend_name=backend_name,
        shots=shots,
        correction_mode=_correction_mode(correction_mode),
    )
    records = _api("run_hardware_fixed_n_process_tomography")(
        configs,
        backend,
        bootstrap_samples=bootstrap_samples,
        confidence_level=confidence_level,
        progress=lambda msg: typer.echo(msg, err=True),
    )
    _echo_records_or_paths(records, output_stem=output_stem)
    if output_stem:
        plot_metric_vs_delay(
            records,
            metric="process_fidelity",
            path=f"{output_stem}_process_fidelity.png",
        )


@app.command()
def hardware_multi_backend_fixed_n_process_tomography(
    n_values: str = typer.Option("2", help="Comma-separated fixed physical-qubit counts."),
    backend_names: str = typer.Option(..., help="Comma-separated IBM backend names."),
    shots: int = typer.Option(2048, help="Number of shots per tomography setting."),
    correction_mode: str = typer.Option("dynamic", help="dynamic or deferred."),
    delays: str = typer.Option("0,64,128", help="Comma-separated delay values in dt units."),
    bootstrap_samples: int = typer.Option(0, help="Optional number of bootstrap resamples for CIs."),
    confidence_level: float = typer.Option(0.95, help="Confidence level for bootstrap intervals."),
    output_stem: str | None = typer.Option(None, help="Optional file stem for json/csv outputs."),
) -> None:
    """Run fixed-n logical process tomography on multiple IBM backends."""
    configs = fixed_n_sweep_configs(
        [int(x.strip()) for x in n_values.split(",") if x.strip()],
        delay_dt_values=[int(x.strip()) for x in delays.split(",") if x.strip()],
    )
    backend_configs = [
        BackendConfig(
            backend_name=item.strip(),
            shots=shots,
            correction_mode=_correction_mode(correction_mode),
        )
        for item in backend_names.split(",")
        if item.strip()
    ]
    records = _api("run_multi_backend_fixed_n_process_tomography")(
        configs,
        backend_configs,
        bootstrap_samples=bootstrap_samples,
        confidence_level=confidence_level,
        progress=lambda msg: typer.echo(msg, err=True),
    )
    _echo_records_or_paths(records, output_stem=output_stem, plot_delay=False)
    if output_stem:
        plot_metric_vs_delay(
            records,
            metric="process_fidelity",
            path=f"{output_stem}_process_fidelity.png",
        )


@app.command()
def aer_delay_sweep(
    dimension: int = typer.Option(..., help="Logical Hilbert-space dimension."),
    shots: int = typer.Option(2048, help="Number of shots per tomography setting."),
    correction_mode: str = typer.Option("dynamic", help="dynamic or deferred."),
    delays: str = typer.Option("0,64,128", help="Comma-separated delay values in dt units."),
    depolarizing_1q: float = typer.Option(0.0),
    depolarizing_2q: float = typer.Option(0.0),
    t1: float | None = typer.Option(DEFAULT_AER_T1_SECONDS),
    t2: float | None = typer.Option(DEFAULT_AER_T2_SECONDS),
    method: str = typer.Option("automatic"),
    bootstrap_samples: int = typer.Option(0, help="Optional number of bootstrap resamples for 95% CIs."),
    confidence_level: float = typer.Option(0.95, help="Confidence level for bootstrap intervals."),
    dt_ns_per_dt: float | None = typer.Option(DEFAULT_AER_DT_NS_PER_DT, help="Nanoseconds per backend dt tick used for delay calibration."),
    output_stem: str | None = typer.Option(None),
) -> None:
    """Aer simulation helper for local noisy validation of encoded teleportation circuits."""
    sweep = SweepConfig(
        dimension=dimension,
        delay_dt_values=[int(x.strip()) for x in delays.split(",") if x.strip()],
        shots=shots,
    )
    backend = BackendConfig(
        shots=shots,
        correction_mode=_correction_mode(correction_mode),
    )
    try:
        noise_model = build_basic_noise_model(
            depolarizing_1q=depolarizing_1q,
            depolarizing_2q=depolarizing_2q,
            t1=t1,
            t2=t2,
        )
        records = _api("run_aer_delay_sweep")(
            sweep,
            backend,
            noise_model=noise_model,
            method=method,
            bootstrap_samples=bootstrap_samples,
            confidence_level=confidence_level,
            dt_ns_per_dt=dt_ns_per_dt,
        )
    except AerExecutionError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1)
    _echo_records_or_paths(records, output_stem=output_stem)


@app.command()
def fixed_n_plan(
    n_values: str = typer.Option("1,2,3", help="Comma-separated physical-qubit counts."),
    delays: str = typer.Option("0,64,128", help="Comma-separated delay values in dt units."),
) -> None:
    """Generate fixed-physical-qubit experiment plans for fair dimension comparisons."""
    configs = fixed_n_sweep_configs(
        [int(x.strip()) for x in n_values.split(",") if x.strip()],
        delay_dt_values=[int(x.strip()) for x in delays.split(",") if x.strip()],
    )
    typer.echo(
        json.dumps(
            [
                {
                    "dimension": cfg.dimension,
                    "n_physical": cfg.n_physical,
                    "delay_dt_values": list(cfg.delay_dt_values),
                    "state_family": cfg.state_family,
                }
                for cfg in configs
            ],
            indent=2,
        )
    )


@app.command()
def markovian_model(
    dimension: int = typer.Option(...),
    delay: float = typer.Option(...),
    t1: float | None = typer.Option(None),
    t2: float | None = typer.Option(None),
    t_dep: float | None = typer.Option(None),
    depolarizing_probability: float | None = typer.Option(None),
    seed: int = typer.Option(7),
) -> None:
    """Evaluate the Markovian effective-noise model for a given delay and encoded dimension."""
    state = random_haar_state(dimension, seed=seed)
    observables = markovian_delay_observables(
        state,
        dimension,
        delay=delay,
        t1=t1,
        t2=t2,
        t_dep=t_dep,
        depolarizing_probability=depolarizing_probability,
    )
    typer.echo(json.dumps(observables, indent=2))


@app.command()
def correlated_memory_model(
    dimension: int = typer.Option(...),
    steps: int = typer.Option(8),
    probability: float = typer.Option(0.02),
    memory_strength: float = typer.Option(0.8),
    samples: int = typer.Option(1024),
    seed: int = typer.Option(7),
) -> None:
    """Evaluate the correlated-memory effective model used as the non-Markovian lane."""
    state = random_haar_state(dimension, seed=seed)
    observables = correlated_memory_observables(
        state,
        dimension,
        steps=steps,
        base_phase_flip_probability=probability,
        memory_strength=memory_strength,
        samples=samples,
        seed=seed,
    )
    typer.echo(json.dumps(observables, indent=2))


@app.command()
def blp_scan(
    dimension: int = typer.Option(...),
    steps: int = typer.Option(8),
    probability: float = typer.Option(0.02),
    memory_strength: float = typer.Option(0.8),
    samples: int = typer.Option(1024),
    seed: int = typer.Option(7),
) -> None:
    """Typer CLI command for the TeleportDim experiment toolkit."""
    state_a = computational_basis_state(dimension, 0)
    state_b = fourier_state(dimension, 0)
    result = blp_non_markovianity(
        state_a,
        state_b,
        dimension,
        steps=steps,
        base_phase_flip_probability=probability,
        memory_strength=memory_strength,
        samples=samples,
        seed=seed,
    )
    typer.echo(json.dumps(result, indent=2))


@app.command()
def markovian_fixed_n_sweep(
    n_values: str = typer.Option("1,2,3", help="Comma-separated physical-qubit counts."),
    delays: str = typer.Option("0,64,128", help="Comma-separated delay values in dt units."),
    t1: float | None = typer.Option(None),
    t2: float | None = typer.Option(None),
    t_dep: float | None = typer.Option(None),
    depolarizing_probability: float | None = typer.Option(None),
    bootstrap_samples: int = typer.Option(0, help="Optional probe-resampling bootstrap count for confidence intervals."),
    confidence_level: float = typer.Option(0.95, help="Confidence level for bootstrap intervals."),
    dt_ns_per_dt: float | None = typer.Option(DEFAULT_AER_DT_NS_PER_DT, help="Nanoseconds per delay_dt unit used for plotting and export."),
    output_stem: str | None = typer.Option(None, help="Optional file stem for json/csv/plots."),
) -> None:
    """Evaluate the Markovian effective-noise model for a given delay and encoded dimension."""
    configs = fixed_n_sweep_configs(
        [int(x.strip()) for x in n_values.split(",") if x.strip()],
        delay_dt_values=[int(x.strip()) for x in delays.split(",") if x.strip()],
    )
    records = _api("run_markovian_fixed_n_sweep")(
        configs,
        t1=t1,
        t2=t2,
        t_dep=t_dep,
        depolarizing_probability=depolarizing_probability,
        bootstrap_samples=bootstrap_samples,
        confidence_level=confidence_level,
        dt_ns_per_dt=dt_ns_per_dt,
        progress=lambda msg: typer.echo(msg, err=True),
    )
    _echo_records_or_paths(records, output_stem=output_stem)
    if output_stem:
        plot_metric_vs_fill_ratio(records, metric="fidelity", path=f"{output_stem}_phi_fidelity.png")


@app.command()
def aer_fixed_n_sweep(
    n_values: str = typer.Option("1,2,3", help="Comma-separated physical-qubit counts."),
    delays: str = typer.Option("0,64,128", help="Comma-separated delay values in dt units."),
    shots: int = typer.Option(2048, help="Number of shots per tomography setting."),
    correction_mode: str = typer.Option("dynamic", help="dynamic or deferred."),
    depolarizing_1q: float = typer.Option(0.0),
    depolarizing_2q: float = typer.Option(0.0),
    t1: float | None = typer.Option(DEFAULT_AER_T1_SECONDS),
    t2: float | None = typer.Option(DEFAULT_AER_T2_SECONDS),
    method: str = typer.Option("automatic"),
    bootstrap_samples: int = typer.Option(0, help="Optional number of bootstrap resamples for CIs."),
    confidence_level: float = typer.Option(0.95, help="Confidence level for bootstrap intervals."),
    dt_ns_per_dt: float | None = typer.Option(DEFAULT_AER_DT_NS_PER_DT, help="Nanoseconds per backend dt tick used for delay calibration."),
    output_stem: str | None = typer.Option(None, help="Optional file stem for json/csv/plots."),
) -> None:
    """Run the full Aer teleportation circuit for fixed-n sweeps."""
    configs = fixed_n_sweep_configs(
        [int(x.strip()) for x in n_values.split(",") if x.strip()],
        delay_dt_values=[int(x.strip()) for x in delays.split(",") if x.strip()],
    )
    for config in configs:
        config.shots = shots
    records = _api("run_aer_fixed_n_sweep")(
        configs,
        correction_mode=_correction_mode(correction_mode),
        depolarizing_1q=depolarizing_1q,
        depolarizing_2q=depolarizing_2q,
        t1=t1,
        t2=t2,
        method=method,
        bootstrap_samples=bootstrap_samples,
        confidence_level=confidence_level,
        dt_ns_per_dt=dt_ns_per_dt,
        progress=lambda msg: typer.echo(msg, err=True),
    )
    _echo_records_or_paths(records, output_stem=output_stem)
    if output_stem:
        plot_metric_vs_fill_ratio(records, metric="fidelity", path=f"{output_stem}_phi_fidelity.png")


@app.command()
def correlated_memory_fixed_n_sweep(
    n_values: str = typer.Option("1,2,3", help="Comma-separated physical-qubit counts."),
    steps: int = typer.Option(8),
    probability: float = typer.Option(0.02),
    memory_strength: float = typer.Option(0.8),
    samples: int = typer.Option(1024),
    output_stem: str | None = typer.Option(None),
) -> None:
    """Evaluate the correlated-memory effective model used as the non-Markovian lane."""
    configs = fixed_n_sweep_configs(
        [int(x.strip()) for x in n_values.split(",") if x.strip()],
        delay_dt_values=[0],
    )
    records = _api("run_correlated_memory_fixed_n_sweep")(
        configs,
        steps=steps,
        base_phase_flip_probability=probability,
        memory_strength=memory_strength,
        samples=samples,
        progress=lambda msg: typer.echo(msg, err=True),
    )
    _echo_records_or_paths(records, output_stem=output_stem)


@app.command()
def blp_memory_scan(
    dimensions: str = typer.Option("2,3,4", help="Comma-separated logical dimensions."),
    memory_strengths: str = typer.Option("0.0,0.2,0.4,0.6,0.8,1.0"),
    steps: int = typer.Option(8),
    probability: float = typer.Option(0.02),
    samples: int = typer.Option(1024),
    output_stem: str | None = typer.Option(None),
) -> None:
    """Typer CLI command for the TeleportDim experiment toolkit."""
    records = _api("run_blp_memory_scan")(
        [int(x.strip()) for x in dimensions.split(",") if x.strip()],
        [float(x.strip()) for x in memory_strengths.split(",") if x.strip()],
        steps=steps,
        base_phase_flip_probability=probability,
        samples=samples,
        progress=lambda msg: typer.echo(msg, err=True),
    )
    if output_stem:
        save_json(records, f"{output_stem}.json")
        save_csv(records, f"{output_stem}.csv")
        plot_blp_vs_memory_strength(records, path=f"{output_stem}_blp.png")
    typer.echo(json.dumps(records, indent=2))


@app.command()
def blp_random_telegraph_scan(
    dimensions: str = typer.Option("2,3,4", help="Comma-separated logical dimensions."),
    n_physical: int | None = typer.Option(None, help="Optional fixed physical qubit count for fair fill-ratio comparisons."),
    switching_probabilities: str = typer.Option("0.005,0.0125,0.025,0.05,0.1,0.2"),
    coupling_strength: float = typer.Option(0.4),
    steps: int = typer.Option(16),
    dt: float = typer.Option(1.0, help="Theory-lane time step used in the telegraph update rule."),
    samples: int = typer.Option(2048),
    output_stem: str | None = typer.Option(None),
) -> None:
    """Run a calibrated BLP sweep for the random-telegraph dephasing model."""
    records = _api("run_blp_random_telegraph_scan")(
        [int(x.strip()) for x in dimensions.split(",") if x.strip()],
        [float(x.strip()) for x in switching_probabilities.split(",") if x.strip()],
        n_physical=n_physical,
        steps=steps,
        coupling_strength=coupling_strength,
        dt=dt,
        samples=samples,
        progress=lambda msg: typer.echo(msg, err=True),
    )
    if output_stem:
        save_json(records, f"{output_stem}.json")
        save_csv(records, f"{output_stem}.csv")
        save_blp_markdown_report(records, path=f"{output_stem}.md", title="Random-telegraph BLP scan")
        plot_blp_vs_switching_probability(records, path=f"{output_stem}_blp.png")
    typer.echo(json.dumps(records, indent=2))


@app.command()
def calibrate_random_telegraph(
    input_json: str = typer.Option(..., help="JSON record file with dt_ns-calibrated delay records."),
    dimension: int = typer.Option(..., help="Logical dimension to calibrate against."),
    n_physical: int | None = typer.Option(None, help="Optional physical qubit count filter."),
    metric: str = typer.Option("process_fidelity", help="Calibration metric: process_fidelity, average_gate_fidelity, in_subspace_fidelity, or fidelity."),
    dt_ns_per_step: float = typer.Option(..., help="Nanoseconds represented by one telegraph update step / backend delay tick."),
    fit_mode: str = typer.Option("first_nonzero", help="first_nonzero or regression."),
    output_stem: str | None = typer.Option(None, help="Optional file stem for json/markdown outputs."),
) -> None:
    """Calibrate a random-telegraph switching rate from backend or Aer delay data."""
    records = load_json_records(input_json)
    calibration = calibrate_random_telegraph_from_records(
        records,
        dimension=dimension,
        n_physical=n_physical,
        metric=metric,
        dt_ns_per_step=dt_ns_per_step,
        fit_mode=fit_mode,
    )
    if output_stem:
        json_path = _normalize_path(f"{output_stem}.json")
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(calibration, indent=2) + "\n")
        save_random_telegraph_calibration_markdown_report(
            calibration,
            path=f"{output_stem}.md",
        )
    typer.echo(json.dumps(calibration, indent=2))


@app.command()
def aer_process_tomography(
    dimension: int = typer.Option(..., help="Logical Hilbert-space dimension."),
    n_physical: int | None = typer.Option(None, help="Optional explicit physical qubit count for fixed-n embeddings."),
    shots: int = typer.Option(2048, help="Number of shots per tomography setting."),
    correction_mode: str = typer.Option("dynamic", help="dynamic or deferred."),
    delays: str = typer.Option("0,64,128", help="Comma-separated delay values in dt units."),
    depolarizing_1q: float = typer.Option(0.0),
    depolarizing_2q: float = typer.Option(0.0),
    t1: float | None = typer.Option(DEFAULT_AER_T1_SECONDS),
    t2: float | None = typer.Option(DEFAULT_AER_T2_SECONDS),
    method: str = typer.Option("automatic"),
    bootstrap_samples: int = typer.Option(0, help="Optional number of bootstrap resamples for CIs."),
    confidence_level: float = typer.Option(0.95, help="Confidence level for bootstrap intervals."),
    dt_ns_per_dt: float | None = typer.Option(DEFAULT_AER_DT_NS_PER_DT, help="Nanoseconds per backend dt tick used for delay calibration."),
    output_stem: str | None = typer.Option(None),
) -> None:
    """Run logical process tomography on the Aer teleportation circuit."""
    sweep = SweepConfig(
        dimension=dimension,
        n_physical=n_physical,
        delay_dt_values=[int(x.strip()) for x in delays.split(",") if x.strip()],
        shots=shots,
    )
    backend = BackendConfig(
        shots=shots,
        correction_mode=_correction_mode(correction_mode),
    )
    try:
        noise_model = build_basic_noise_model(
            depolarizing_1q=depolarizing_1q,
            depolarizing_2q=depolarizing_2q,
            t1=t1,
            t2=t2,
        )
        records = _api("run_aer_process_tomography")(
            sweep,
            backend,
            noise_model=noise_model,
            method=method,
            bootstrap_samples=bootstrap_samples,
            confidence_level=confidence_level,
            dt_ns_per_dt=dt_ns_per_dt,
        )
    except AerExecutionError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1)
    typer.echo(summarize_results(records), err=True)
    if output_stem:
        save_json(records, f"{output_stem}.json")
        save_csv(records, f"{output_stem}.csv")
        plot_metric_vs_delay(records, metric="process_fidelity", path=f"{output_stem}_process_fidelity.png")
        plot_metric_vs_delay(
            records,
            metric="average_gate_fidelity",
            path=f"{output_stem}_average_gate_fidelity.png",
        )
    typer.echo(json.dumps(records, indent=2))


@app.command()
def channel_body_sweep(
    n_values: str = typer.Option("2", help="Comma-separated fixed physical-qubit counts."),
    dimensions: str | None = typer.Option("2,3,4", help="Comma-separated dimensions, or omit for all dimensions per n."),
    bodies: str = typer.Option(
        "ideal,dephasing,amplitude_damping,leakage_mixing,random_telegraph,coherent_z_drift",
        help="Comma-separated channel-deformation bodies.",
    ),
    strengths: str = typer.Option("0,0.001,0.005,0.01", help="Comma-separated unitless body strengths."),
    delays: str = typer.Option("0,64,128", help="Comma-separated delay values in dt units."),
    shots: int = typer.Option(4096, help="Shot count recorded for comparability with hardware/Aer artifacts."),
    samples: int = typer.Option(1024, help="Monte-Carlo samples for memory-body theory models."),
    memory_strength: float = typer.Option(0.8, help="Correlated-memory reuse probability in [0, 1]."),
    correlation: float = typer.Option(0.4, help="Random-telegraph coupling / correlation scale."),
    coherent_angle: float = typer.Option(0.0, help="Optional fixed coherent rotation angle in radians."),
    dt_ns_per_dt: float | None = typer.Option(DEFAULT_AER_DT_NS_PER_DT, help="Nanoseconds per delay_dt unit."),
    output_stem: str | None = typer.Option(None, help="Optional file stem for json/csv/markdown outputs."),
) -> None:
    """Run the controlled channel-body deformation sweep."""
    dimension_values = None if dimensions is None else _csv_ints(dimensions)
    records = _api("run_channel_body_sweep")(
        _csv_ints(n_values),
        dimensions=dimension_values,
        bodies=_csv_strings(bodies),
        strengths=_csv_floats(strengths),
        delays=_csv_ints(delays),
        shots=shots,
        samples=samples,
        memory_strength=memory_strength,
        correlation=correlation,
        coherent_angle=coherent_angle,
        dt_ns_per_dt=dt_ns_per_dt,
        progress=lambda msg: typer.echo(msg, err=True),
    )
    if output_stem:
        save_json(records, f"{output_stem}.json")
        save_csv(records, f"{output_stem}.csv")
        save_channel_body_markdown_report(records, f"{output_stem}.md")
    typer.echo(json.dumps(records, indent=2))


@app.command("compare-body-fingerprints")
def compare_body_fingerprints_command(
    input_json: str = typer.Option(..., help="Channel-body sweep JSON artifact."),
    hardware_json: str = typer.Option(..., help="Hardware raw or fixed-n comparison JSON artifact."),
    metrics: str = typer.Option(
        "process_fidelity,average_gate_fidelity,leakage,in_subspace_fidelity,anisotropy,nonunitality",
        help="Comma-separated metrics used for fingerprint distance.",
    ),
    output_stem: str | None = typer.Option(None, help="Optional file stem for json/csv/markdown outputs."),
) -> None:
    """Rank simulated deformation bodies against hardware channel fingerprints."""
    body_records = load_json_records(input_json)
    hardware_records = load_json_records(hardware_json)
    comparisons = _api("compare_body_fingerprints")(
        body_records,
        hardware_records,
        metrics=_csv_strings(metrics),
    )
    if output_stem:
        save_json(comparisons, f"{output_stem}.json")
        save_csv(comparisons, f"{output_stem}.csv")
        save_body_fingerprint_markdown_report(comparisons, f"{output_stem}.md")
    typer.echo(json.dumps(comparisons, indent=2))


@app.command()
def compare_fixed_n(
    input_json: str = typer.Option(..., help="Path to one JSON records file, or a comma-separated list of JSON files."),
    n_physical: int = typer.Option(..., help="Physical qubit count to compare."),
    dt_ns_per_dt: float | None = typer.Option(None, help="Optional nanoseconds per delay_dt step when records do not already include dt_ns."),
    output_stem: str | None = typer.Option(None),
) -> None:
    """Typer CLI command for the TeleportDim experiment toolkit."""
    input_paths = [item.strip() for item in input_json.split(",") if item.strip()]
    records: list[dict[str, Any]] = []
    for path in input_paths:
        records.extend(load_json_records(path))
    summary = summarize_fixed_n_comparison(records, n_physical=n_physical, dt_ns_per_dt=dt_ns_per_dt)
    if output_stem:
        save_json(summary, f"{output_stem}.json")
        save_csv(summary, f"{output_stem}.csv")
        save_fixed_n_markdown_report(summary, path=f"{output_stem}.md")
    typer.echo(json.dumps(summary, indent=2))


@app.command()
def compare_hardware_backends(
    input_json: str = typer.Option(..., help="Path to one hardware JSON file, or a comma-separated list of raw/summary JSON files."),
    n_physical: int = typer.Option(..., help="Physical qubit count to compare."),
    dt_ns_per_dt: float | None = typer.Option(None, help="Optional nanoseconds per delay_dt step when records do not already include dt_ns."),
    title: str = typer.Option("Multi-backend fixed-n comparison", help="Markdown report title."),
    output_stem: str | None = typer.Option(None),
) -> None:
    """Build one report that compares fixed-n hardware results across multiple backends."""
    summary_rows = load_backend_fixed_n_summary_rows(
        [item.strip() for item in input_json.split(",") if item.strip()],
        n_physical=n_physical,
        dt_ns_per_dt=dt_ns_per_dt,
    )
    rows = summarize_backend_fixed_n_table(summary_rows)
    if output_stem:
        save_json(rows, f"{output_stem}.json")
        save_csv(rows, f"{output_stem}.csv")
        save_backend_fixed_n_markdown_report(rows, path=f"{output_stem}.md", title=title)
    typer.echo(json.dumps(rows, indent=2))


@app.command()
def compare_three_lanes(
    theory_json: str = typer.Option(..., help="Path to one theory-lane compare JSON file, or a comma-separated list of theory summary/raw JSON files."),
    aer_json: str = typer.Option(..., help="Path to one Aer-lane compare JSON file, or a comma-separated list of Aer summary/raw JSON files."),
    hardware_json: str = typer.Option(..., help="Path to one hardware-lane compare JSON file, or a comma-separated list of hardware state/process summary JSON files."),
    n_physical: int = typer.Option(..., help="Physical qubit count to compare."),
    title: str = typer.Option("Three-lane fixed-n comparison", help="Markdown report title."),
    output_stem: str | None = typer.Option(None),
) -> None:
    """Build one report that places theory, Aer, and hardware fixed-n results side by side."""
    lane_summaries = {
        "theory": load_fixed_n_summary_rows(
            [item.strip() for item in theory_json.split(",") if item.strip()],
            n_physical=n_physical,
        ),
        "aer": load_fixed_n_summary_rows(
            [item.strip() for item in aer_json.split(",") if item.strip()],
            n_physical=n_physical,
        ),
        "hardware": load_fixed_n_summary_rows(
            [item.strip() for item in hardware_json.split(",") if item.strip()],
            n_physical=n_physical,
        ),
    }
    rows = summarize_three_lane_fixed_n_table(lane_summaries)
    if output_stem:
        save_json(rows, f"{output_stem}.json")
        save_csv(rows, f"{output_stem}.csv")
        save_three_lane_fixed_n_markdown_report(rows, path=f"{output_stem}.md", title=title)
    typer.echo(json.dumps(rows, indent=2))


@app.command()
def compare_hardware_theory(
    theory_json: str = typer.Option(..., help="Path to one theory-lane compare JSON file, or a comma-separated list of theory summary/raw JSON files."),
    hardware_json: str = typer.Option(..., help="Path to one or more hardware raw/summary JSON files."),
    n_physical: int = typer.Option(..., help="Physical qubit count to compare."),
    metrics: str = typer.Option("fidelity,leakage,in_subspace_fidelity", help="Comma-separated shared metrics to compare."),
    dimensions: str = typer.Option("2,3,4", help="Comma-separated logical dimensions to compare."),
    title: str = typer.Option("Hardware versus theory divergence", help="Markdown report title."),
    output_stem: str | None = typer.Option(None),
) -> None:
    """Compare hardware fixed-n summaries against the theory baseline on the shared delay grid."""
    theory_rows = load_fixed_n_summary_rows(
        [item.strip() for item in theory_json.split(",") if item.strip()],
        n_physical=n_physical,
    )
    hardware_rows = load_backend_fixed_n_summary_rows(
        [item.strip() for item in hardware_json.split(",") if item.strip()],
        n_physical=n_physical,
    )
    comparison_rows = summarize_hardware_theory_divergence(
        theory_rows,
        hardware_rows,
        metrics=[item.strip() for item in metrics.split(",") if item.strip()],
        dimensions=[int(item.strip()) for item in dimensions.split(",") if item.strip()],
    )
    if output_stem:
        save_json(comparison_rows, f"{output_stem}.json")
        save_csv(comparison_rows, f"{output_stem}.csv")
        save_hardware_theory_divergence_markdown_report(
            comparison_rows,
            path=f"{output_stem}.md",
            title=title,
        )
        for metric_name in {str(row["metric"]) for row in comparison_rows}:
            for dimension_value in {int(row["dimension"]) for row in comparison_rows if str(row["metric"]) == metric_name}:
                plot_hardware_theory_curves(
                    comparison_rows,
                    metric=metric_name,
                    dimension=dimension_value,
                    path=f"{output_stem}_{metric_name}_d{dimension_value}_curves.png",
                )
                plot_hardware_theory_divergence(
                    comparison_rows,
                    metric=metric_name,
                    dimension=dimension_value,
                    path=f"{output_stem}_{metric_name}_d{dimension_value}_delta.png",
                )
    typer.echo(json.dumps(comparison_rows, indent=2))


@app.command()
def plot_records(
    input_json: str = typer.Option(..., help="Path to JSON records file."),
    metric: str = typer.Option("fidelity"),
    mode: str = typer.Option("delay", help="delay, fill_ratio, or blp"),
    output_path: str = typer.Option(...),
    delay_dt: int | None = typer.Option(None),
) -> None:
    """Generate a matplotlib figure for one of the thesis analysis outputs."""
    records = load_json_records(input_json)
    if mode == "delay":
        path = plot_metric_vs_delay(records, metric=metric, path=output_path)
    elif mode == "fill_ratio":
        path = plot_metric_vs_fill_ratio(records, metric=metric, path=output_path, delay_dt=delay_dt)
    elif mode == "blp":
        if records and "switching_probability" in records[0]:
            path = plot_blp_vs_switching_probability(records, path=output_path)
        else:
            path = plot_blp_vs_memory_strength(records, path=output_path)
    else:
        raise typer.BadParameter("mode must be one of: delay, fill_ratio, blp")
    typer.echo(str(path))


def main() -> None:
    """Entry point used by the console script and python -m execution."""
    app()


__all__ = [
    "app",
    "main",
]
