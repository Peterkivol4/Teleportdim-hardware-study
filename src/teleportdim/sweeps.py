from __future__ import annotations

from .aer import (
    _run_aer_tomography_for_state,
    build_basic_noise_model,
    make_aer_simulator,
    run_aer_delay_sweep,
    run_aer_process_tomography,
)
from .circuits import append_output_measurements, build_block_teleportation_circuit
from .config import BackendConfig, CorrectionMode, SweepConfig
from .encoding import (
    delay_dt_to_ns,
    embed_logical_state,
    fill_ratio,
    num_physical_qubits_for_dimension,
    physical_hilbert_dimension_for_logical_dimension,
    resolved_aer_dt_ns_per_dt,
    resolved_n_physical,
)
from .hardware import (
    backend_dt_seconds,
    extract_register_bitstrings,
    extract_register_counts,
    run_sampler_job,
    select_backend,
    transpile_isa,
    validate_backend_for_experiment,
)
from .metrics import (
    average_gate_fidelity_from_process_fidelity,
    in_subspace_fidelity,
    leakage_probability,
    pure_state_density,
    pure_state_fidelity,
    renormalized_logical_subspace_density,
)
from .postprocess import corrected_counts_from_deferred_shots
from .process import process_fidelity_to_identity, process_tomography_probe_states, reconstruct_superoperator
from .simulation import (
    blp_non_markovianity,
    blp_random_telegraph_non_markovianity,
    correlated_memory_observables,
    markovian_delay_observables,
    random_telegraph_blp_probe_pair,
    switching_probability_to_correlation_time,
)
from .states import canonical_probe_states, computational_basis_state, fourier_state, random_haar_state
from .statistics import (
    bootstrap_average_tomography_metrics,
    bootstrap_probe_mean_observables,
    bootstrap_process_tomography_metrics,
)
from .tomography import all_measurement_bases, reconstruct_density_matrix

from collections.abc import Callable, Sequence
from typing import Any, Literal

import numpy as np
import sys


ProgressCallback = Callable[[str], None]
StateFamily = Literal["haar", "computational", "fourier"]


def _emit_progress(progress: ProgressCallback | None, message: str) -> None:
    """Emit optional progress updates for long-running sweep commands."""
    if progress is not None:
        progress(message)


def make_probe_state(config: SweepConfig) -> np.ndarray:
    """Construct make probe state for simulation, tomography, or benchmarking."""
    if config.state_family == "haar":
        return random_haar_state(config.dimension, seed=config.random_seed)
    if config.state_family == "computational":
        return computational_basis_state(config.dimension, 0)
    if config.state_family == "fourier":
        return fourier_state(config.dimension, 0)
    raise ValueError(f"unsupported state_family: {config.state_family}")


def fixed_n_dimensions(n_physical: int) -> list[int]:
    """Generate fixed-physical-qubit experiment plans for fair dimension comparisons."""
    if n_physical < 1:
        raise ValueError("n_physical must be >= 1")
    if n_physical == 1:
        return [2]
    return list(range(2 ** (n_physical - 1), 2**n_physical + 1))


def fixed_n_sweep_configs(
    n_physical_values: Sequence[int],
    *,
    delay_dt_values: Sequence[int],
    state_family: StateFamily = "haar",
    random_seed: int = 7,
) -> list[SweepConfig]:
    """Generate fixed-physical-qubit experiment plans for fair dimension comparisons."""
    configs: list[SweepConfig] = []
    for n_physical in n_physical_values:
        for dimension in fixed_n_dimensions(n_physical):
            configs.append(
                SweepConfig(
                    dimension=dimension,
                    n_physical=n_physical,
                    delay_dt_values=list(delay_dt_values),
                    state_family=state_family,
                    random_seed=random_seed,
                )
            )
    return configs


def _average_markovian_observables(
    dimension: int,
    *,
    n_physical: int | None = None,
    delay: float,
    t1: float | None = None,
    t2: float | None = None,
    t_dep: float | None = None,
    depolarizing_probability: float | None = None,
    bootstrap_samples: int = 0,
    confidence_level: float = 0.95,
    seed: int | None = None,
) -> dict[str, object]:
    """Average probe-state observables into a single fixed-n theory-lane record."""
    states = canonical_probe_states(dimension)
    values = [
        markovian_delay_observables(
            state,
            dimension,
            n_physical=n_physical,
            delay=delay,
            t1=t1,
            t2=t2,
            t_dep=t_dep,
            depolarizing_probability=depolarizing_probability,
        )
        for state in states
    ]
    summary: dict[str, object] = {
        "avg_probe_fidelity": float(np.mean([item["fidelity"] for item in values])),
        "avg_probe_leakage": float(np.mean([item["leakage"] for item in values])),
        "avg_probe_in_subspace_fidelity": float(
            np.mean([item["in_subspace_fidelity"] for item in values])
        ),
        "probe_ensemble_size": float(len(states)),
    }
    if bootstrap_samples > 0:
        summary.update(
            bootstrap_probe_mean_observables(
                values,
                bootstrap_samples=bootstrap_samples,
                confidence_level=confidence_level,
                seed=seed,
            )
        )
    return summary
    return summary


def run_markovian_fixed_n_sweep(
    configs: Sequence[SweepConfig],
    *,
    t1: float | None = None,
    t2: float | None = None,
    t_dep: float | None = None,
    depolarizing_probability: float | None = None,
    bootstrap_samples: int = 0,
    confidence_level: float = 0.95,
    dt_ns_per_dt: float | None = None,
    progress: ProgressCallback | None = None,
) -> list[dict[str, Any]]:
    """Run the phenomenological Markovian fixed-``n`` sweep.

    ``delay_dt_values`` are treated as theory-lane delay coordinates. They only inherit a
    physical meaning if the caller provides ``t1``, ``t2``, and ``t_dep`` in the same units.
    """
    records: list[dict[str, Any]] = []
    total = sum(len(sweep.delay_dt_values) for sweep in configs)
    completed = 0
    for sweep in configs:
        n_physical = resolved_n_physical(sweep.dimension, sweep.n_physical)
        for delay_dt in sweep.delay_dt_values:
            completed += 1
            _emit_progress(progress, f"markovian sweep {completed}/{total}: d={sweep.dimension}, n={n_physical}, delay_dt={delay_dt}")
            avg_observables = _average_markovian_observables(
                sweep.dimension,
                n_physical=n_physical,
                delay=float(delay_dt),
                t1=t1,
                t2=t2,
                t_dep=t_dep,
                depolarizing_probability=depolarizing_probability,
                bootstrap_samples=bootstrap_samples,
                confidence_level=confidence_level,
                seed=sweep.random_seed + completed,
            )
            records.append(
                {
                    "dimension": sweep.dimension,
                    "n_physical": n_physical,
                    "physical_hilbert_dimension": physical_hilbert_dimension_for_logical_dimension(
                        sweep.dimension, n_physical
                    ),
                    "fill_ratio": fill_ratio(sweep.dimension, n_physical),
                    "delay_dt": int(delay_dt),
                    "dt_ns": delay_dt_to_ns(delay_dt, dt_ns_per_dt=dt_ns_per_dt),
                    "shots": sweep.shots,
                    "state_family": "canonical_probe_average",
                    "simulation_lane": "markovian_model",
                    "t1": t1,
                    "t2": t2,
                    "t_dep": t_dep,
                    "depolarizing_probability": depolarizing_probability,
                    "fidelity": avg_observables["avg_probe_fidelity"],
                    "leakage": avg_observables["avg_probe_leakage"],
                    "in_subspace_fidelity": avg_observables["avg_probe_in_subspace_fidelity"],
                    **avg_observables,
                }
            )
    return records


def run_aer_fixed_n_sweep(
    configs: Sequence[SweepConfig],
    *,
    correction_mode: CorrectionMode = "dynamic",
    depolarizing_1q: float = 0.0,
    depolarizing_2q: float = 0.0,
    t1: float | None = None,
    t2: float | None = None,
    method: str = "automatic",
    bootstrap_samples: int = 0,
    confidence_level: float = 0.95,
    dt_ns_per_dt: float | None = None,
    seed_simulator: int = 17,
    progress: ProgressCallback | None = None,
) -> list[dict[str, Any]]:
    """Run fixed-``n`` sweeps through the full Aer teleportation circuit."""
    noise_model = build_basic_noise_model(
        depolarizing_1q=depolarizing_1q,
        depolarizing_2q=depolarizing_2q,
        t1=t1,
        t2=t2,
    )
    backend_config = BackendConfig(shots=max(int(cfg.shots) for cfg in configs), correction_mode=correction_mode)
    simulator = make_aer_simulator(method=method, noise_model=noise_model)
    resolved_dt_ns = resolved_aer_dt_ns_per_dt(dt_ns_per_dt)

    records: list[dict[str, Any]] = []
    total = sum(len(sweep.delay_dt_values) for sweep in configs)
    completed = 0
    for sweep in configs:
        canonical_states = canonical_probe_states(sweep.dimension)
        n_physical = resolved_n_physical(sweep.dimension, sweep.n_physical)
        for delay_dt in sweep.delay_dt_values:
            completed += 1
            _emit_progress(
                progress,
                f"aer circuit sweep {completed}/{total}: d={sweep.dimension}, n={n_physical}, delay_dt={delay_dt}",
            )
            probe_records: list[dict[str, Any]] = []
            probe_setting_counts: list[dict[str, dict[str, int]]] = []
            for probe_index, logical_state in enumerate(canonical_states):
                state_record, setting_counts, _ = _run_aer_tomography_for_state(
                    logical_state,
                    sweep.dimension,
                    n_physical=n_physical,
                    delay_dt=int(delay_dt),
                    backend_config=BackendConfig(
                        shots=sweep.shots,
                        correction_mode=correction_mode,
                        optimization_level=backend_config.optimization_level,
                    ),
                    simulator=simulator,
                    noise_model=noise_model,
                    seed_simulator=seed_simulator + 1000 * completed + probe_index,
                    dt_ns_per_dt=dt_ns_per_dt,
                    state_family="canonical_probe",
                )
                probe_records.append(state_record)
                probe_setting_counts.append(setting_counts)

            record = {
                "dimension": sweep.dimension,
                "n_physical": n_physical,
                "physical_hilbert_dimension": physical_hilbert_dimension_for_logical_dimension(
                    sweep.dimension, n_physical
                ),
                "fill_ratio": fill_ratio(sweep.dimension, n_physical),
                "delay_dt": int(delay_dt),
                "dt_ns": delay_dt_to_ns(delay_dt, dt_ns_per_dt=resolved_dt_ns),
                "shots": sweep.shots,
                "state_family": "canonical_probe_average",
                "simulation_lane": "aer_circuit",
                "backend_name": getattr(simulator, "name", type(simulator).__name__),
                "correction_mode": correction_mode,
                "depolarizing_1q": float(depolarizing_1q),
                "depolarizing_2q": float(depolarizing_2q),
                "t1": t1,
                "t2": t2,
                "fidelity": float(np.mean([item["fidelity"] for item in probe_records])),
                "leakage": float(np.mean([item["leakage"] for item in probe_records])),
                "in_subspace_fidelity": float(np.mean([item["in_subspace_fidelity"] for item in probe_records])),
                "avg_probe_fidelity": float(np.mean([item["fidelity"] for item in probe_records])),
                "avg_probe_leakage": float(np.mean([item["leakage"] for item in probe_records])),
                "avg_probe_in_subspace_fidelity": float(
                    np.mean([item["in_subspace_fidelity"] for item in probe_records])
                ),
                "probe_ensemble_size": float(len(canonical_states)),
            }
            if bootstrap_samples > 0:
                ci_summary = bootstrap_average_tomography_metrics(
                    canonical_states,
                    sweep.dimension,
                    probe_setting_counts,
                    n_physical=n_physical,
                    bootstrap_samples=bootstrap_samples,
                    confidence_level=confidence_level,
                    seed=seed_simulator + 50000 * completed,
                )
                record["observed_fidelity"] = record["fidelity"]
                record["observed_leakage"] = record["leakage"]
                record["observed_in_subspace_fidelity"] = record["in_subspace_fidelity"]
                record["observed_avg_probe_fidelity"] = record["avg_probe_fidelity"]
                record["observed_avg_probe_leakage"] = record["avg_probe_leakage"]
                record["observed_avg_probe_in_subspace_fidelity"] = record["avg_probe_in_subspace_fidelity"]
                record.update(ci_summary)
                record["fidelity"] = ci_summary["avg_probe_fidelity_bootstrap_mean"]
                record["leakage"] = ci_summary["avg_probe_leakage_bootstrap_mean"]
                record["in_subspace_fidelity"] = ci_summary["avg_probe_in_subspace_fidelity_bootstrap_mean"]
                record["avg_probe_fidelity"] = ci_summary["avg_probe_fidelity_bootstrap_mean"]
                record["avg_probe_leakage"] = ci_summary["avg_probe_leakage_bootstrap_mean"]
                record["avg_probe_in_subspace_fidelity"] = ci_summary["avg_probe_in_subspace_fidelity_bootstrap_mean"]
                record["fidelity_ci_low"] = ci_summary["avg_probe_fidelity_ci_low"]
                record["fidelity_ci_high"] = ci_summary["avg_probe_fidelity_ci_high"]
                record["leakage_ci_low"] = ci_summary["avg_probe_leakage_ci_low"]
                record["leakage_ci_high"] = ci_summary["avg_probe_leakage_ci_high"]
                record["in_subspace_fidelity_ci_low"] = ci_summary["avg_probe_in_subspace_fidelity_ci_low"]
                record["in_subspace_fidelity_ci_high"] = ci_summary["avg_probe_in_subspace_fidelity_ci_high"]
            records.append(record)
    return records


def run_correlated_memory_fixed_n_sweep(
    configs: Sequence[SweepConfig],
    *,
    steps: int,
    base_phase_flip_probability: float,
    memory_strength: float,
    samples: int = 2048,
    progress: ProgressCallback | None = None,
) -> list[dict[str, Any]]:
    """Run correlated memory fixed n sweep and return structured records for downstream analysis."""
    records: list[dict[str, Any]] = []
    total = len(configs)
    for index, sweep in enumerate(configs, start=1):
        _emit_progress(progress, f"correlated-memory sweep {index}/{total}: d={sweep.dimension}, n={resolved_n_physical(sweep.dimension, sweep.n_physical)}")
        state = make_probe_state(sweep)
        n_physical = resolved_n_physical(sweep.dimension, sweep.n_physical)
        observables = correlated_memory_observables(
            state,
            sweep.dimension,
            n_physical=n_physical,
            steps=steps,
            base_phase_flip_probability=base_phase_flip_probability,
            memory_strength=memory_strength,
            samples=samples,
            seed=sweep.random_seed,
        )
        for item in observables:
            records.append(
                {
                    "dimension": sweep.dimension,
                    "n_physical": n_physical,
                    "physical_hilbert_dimension": physical_hilbert_dimension_for_logical_dimension(
                        sweep.dimension, n_physical
                    ),
                    "fill_ratio": fill_ratio(sweep.dimension, n_physical),
                    "step": int(item["step"]),
                    "shots": sweep.shots,
                    "state_family": sweep.state_family,
                    "simulation_lane": "correlated_memory_model",
                    "memory_strength": float(memory_strength),
                    "base_phase_flip_probability": float(base_phase_flip_probability),
                    "samples": int(samples),
                    **item,
                }
            )
    return records


def run_blp_memory_scan(
    dimensions: Sequence[int],
    memory_strengths: Sequence[float],
    *,
    steps: int,
    base_phase_flip_probability: float,
    samples: int = 2048,
    seed: int = 7,
    progress: ProgressCallback | None = None,
) -> list[dict[str, Any]]:
    """Run blp memory scan and return structured records for downstream analysis."""
    records: list[dict[str, Any]] = []
    total = len(dimensions) * len(memory_strengths)
    completed = 0
    for dimension in dimensions:
        state_a = computational_basis_state(dimension, 0)
        state_b = fourier_state(dimension, 0)
        n_physical = num_physical_qubits_for_dimension(dimension)
        for memory_strength in memory_strengths:
            completed += 1
            _emit_progress(progress, f"blp scan {completed}/{total}: d={dimension}, memory_strength={float(memory_strength):.3f}")
            result = blp_non_markovianity(
                state_a,
                state_b,
                dimension,
                steps=steps,
                base_phase_flip_probability=base_phase_flip_probability,
                memory_strength=float(memory_strength),
                samples=samples,
                seed=seed,
            )
            records.append(
                {
                    "dimension": dimension,
                    "n_physical": n_physical,
                    "fill_ratio": fill_ratio(dimension),
                    "memory_strength": float(memory_strength),
                    "steps": int(steps),
                    "base_phase_flip_probability": float(base_phase_flip_probability),
                    "samples": int(samples),
                    **result,
                }
            )
    return records


def run_blp_random_telegraph_scan(
    dimensions: Sequence[int],
    switching_probabilities: Sequence[float],
    *,
    n_physical: int | None = None,
    steps: int,
    coupling_strength: float,
    dt: float = 1.0,
    samples: int = 2048,
    seed: int = 7,
    progress: ProgressCallback | None = None,
) -> list[dict[str, Any]]:
    """Run a calibrated BLP sweep for the random-telegraph dephasing model.

    The scan uses a Fourier-mode probe pair because phase-sensitive superpositions are the
    relevant states for dephasing-induced distinguishability backflow. ``switching_probability``
    is the discrete-time telegraph switching rate; ``dt`` and the derived correlation times
    are expressed in the same arbitrary units used by the theory lane.
    """
    records: list[dict[str, Any]] = []
    total = len(dimensions) * len(switching_probabilities)
    completed = 0
    for dimension in dimensions:
        state_a, state_b = random_telegraph_blp_probe_pair(dimension)
        resolved_n = resolved_n_physical(dimension, n_physical)
        for switching_probability in switching_probabilities:
            completed += 1
            probability = float(switching_probability)
            _emit_progress(
                progress,
                (
                    f"random-telegraph blp scan {completed}/{total}: "
                    f"d={dimension}, n={resolved_n}, p_switch={probability:.4f}"
                ),
            )
            result = blp_random_telegraph_non_markovianity(
                state_a,
                state_b,
                dimension,
                n_physical=resolved_n,
                steps=steps,
                coupling_strength=float(coupling_strength),
                switching_probability=probability,
                dt=dt,
                samples=samples,
                seed=seed,
            )
            correlation_time = switching_probability_to_correlation_time(probability, dt=dt)
            correlation_time_steps = (
                None if correlation_time is None or np.isclose(dt, 0.0) else float(correlation_time / float(dt))
            )
            records.append(
                {
                    "dimension": dimension,
                    "n_physical": resolved_n,
                    "fill_ratio": fill_ratio(dimension, resolved_n),
                    "switching_probability": probability,
                    "correlation_time_dt_units": correlation_time,
                    "correlation_time_steps": correlation_time_steps,
                    "dt_per_step": float(dt),
                    "steps": int(steps),
                    "coupling_strength": float(coupling_strength),
                    "samples": int(samples),
                    "probe_pair": "fourier_k0_vs_k1",
                    **result,
                }
            )
    return records


def _resolve_hardware_execution_dependencies() -> tuple[Any, ...]:
    """Resolve the hardware-execution helpers explicitly and fail fast if they are unavailable."""
    required_names = (
        "select_backend",
        "validate_backend_for_experiment",
        "build_block_teleportation_circuit",
        "append_output_measurements",
        "transpile_isa",
        "run_sampler_job",
        "extract_register_counts",
        "extract_register_bitstrings",
        "corrected_counts_from_deferred_shots",
    )
    resolved: list[Any] = []
    missing: list[str] = []
    # Preserve historical package-root behavior: tests and notebooks often monkeypatch
    # helpers on ``teleportdim`` itself, so resolve through the package root when
    # it exists instead of only using this module's imported bindings.
    package = sys.modules.get("teleportdim")
    global_ns = vars(package) if package is not None else globals()
    for name in required_names:
        value = global_ns.get(name)
        if value is None:
            missing.append(name)
        else:
            resolved.append(value)
    if missing:
        joined = ", ".join(missing)
        raise RuntimeError(
            f"Hardware sweep dependencies are unavailable in the current module surface: {joined}"
        )
    return tuple(resolved)


def _collect_hardware_setting_counts_for_states(
    logical_states: Sequence[np.ndarray],
    dimension: int,
    *,
    n_physical: int,
    delay_dt: int,
    backend_config: BackendConfig,
    backend: Any,
    execution_dependencies: tuple[Any, ...],
) -> list[dict[str, dict[str, int]]]:
    """Acquire full tomography counts for one or more logical input states on hardware."""
    (
        _select_backend_fn,
        _validate_backend_for_experiment_fn,
        build_block_teleportation_circuit_fn,
        append_output_measurements_fn,
        transpile_isa_fn,
        run_sampler_job_fn,
        extract_register_counts_fn,
        extract_register_bitstrings_fn,
        corrected_counts_from_deferred_shots_fn,
    ) = execution_dependencies

    bases = all_measurement_bases(n_physical)
    tomo_circuits: list[Any] = []
    circuit_metadata: list[tuple[int, str]] = []
    for probe_index, logical_state in enumerate(logical_states):
        program = build_block_teleportation_circuit_fn(
            logical_state,
            dimension,
            n_physical=n_physical,
            delay_after_entanglement_dt=int(delay_dt),
            correction_mode=backend_config.correction_mode,
        )
        for basis in bases:
            tomo_circuits.append(append_output_measurements_fn(program, basis))
            circuit_metadata.append((probe_index, basis))

    isa_circuits = transpile_isa_fn(
        tomo_circuits,
        backend=backend,
        optimization_level=backend_config.optimization_level,
    )
    pub_results = run_sampler_job_fn(
        isa_circuits,
        backend=backend,
        shots=backend_config.shots,
        use_session=backend_config.use_session,
    )

    setting_counts_by_probe: list[dict[str, dict[str, int]]] = [
        {} for _ in logical_states
    ]
    for (probe_index, basis), pub_result in zip(circuit_metadata, pub_results):
        reg_name = f"out_{basis}"
        if backend_config.correction_mode == "dynamic":
            setting_counts_by_probe[probe_index][basis] = extract_register_counts_fn(
                pub_result,
                reg_name,
            )
        else:
            output_shots = extract_register_bitstrings_fn(pub_result, reg_name)
            bell_shots = extract_register_bitstrings_fn(pub_result, "bell")
            setting_counts_by_probe[probe_index][basis] = corrected_counts_from_deferred_shots_fn(
                output_shots=output_shots,
                bell_shots=bell_shots,
                basis=basis,
            )
    return setting_counts_by_probe


def _hardware_state_metrics_from_setting_counts(
    logical_state: np.ndarray,
    dimension: int,
    setting_counts: dict[str, dict[str, int]],
    *,
    n_physical: int,
    delay_dt: int,
    dt_seconds: float | None,
    backend_name: str,
    backend_config: BackendConfig,
    state_family: str,
    simulation_lane: str = "ibm_runtime",
) -> tuple[dict[str, Any], np.ndarray]:
    """Reconstruct a hardware output state and compute the headline state metrics."""
    rho = reconstruct_density_matrix(setting_counts)
    embedded_target = embed_logical_state(logical_state, dimension, n_physical)
    record = {
        "dimension": dimension,
        "n_physical": n_physical,
        "physical_hilbert_dimension": physical_hilbert_dimension_for_logical_dimension(
            dimension, n_physical
        ),
        "fill_ratio": fill_ratio(dimension, n_physical),
        "delay_dt": int(delay_dt),
        "dt_ns": delay_dt_to_ns(delay_dt, dt_seconds=dt_seconds),
        "backend_name": backend_name,
        "fidelity": pure_state_fidelity(embedded_target, rho),
        "leakage": leakage_probability(rho, dimension, n_physical),
        "in_subspace_fidelity": in_subspace_fidelity(logical_state, rho, dimension, n_physical),
        "shots": backend_config.shots,
        "state_family": state_family,
        "correction_mode": backend_config.correction_mode,
        "simulation_lane": simulation_lane,
    }
    return record, rho


def run_hardware_delay_sweep(
    sweep: SweepConfig,
    backend_config: BackendConfig,
) -> list[dict[str, Any]]:
    """Run hardware delay sweep and return structured records for downstream analysis."""
    state = make_probe_state(sweep)
    n_physical = resolved_n_physical(sweep.dimension, sweep.n_physical)

    execution_dependencies = _resolve_hardware_execution_dependencies()
    (
        select_backend_fn,
        validate_backend_for_experiment_fn,
        *_rest,
    ) = execution_dependencies

    backend = select_backend_fn(backend_config)
    dt_seconds = backend_dt_seconds(backend)
    validate_backend_for_experiment_fn(
        backend,
        n_required_qubits=3 * n_physical,
        correction_mode=backend_config.correction_mode,
        require_delay=any(delay_dt > 0 for delay_dt in sweep.delay_dt_values),
    )

    results: list[dict[str, Any]] = []
    for delay_dt in sweep.delay_dt_values:
        setting_counts = _collect_hardware_setting_counts_for_states(
            [state],
            sweep.dimension,
            n_physical=n_physical,
            delay_dt=int(delay_dt),
            backend_config=backend_config,
            backend=backend,
            execution_dependencies=execution_dependencies,
        )[0]
        record, _rho = _hardware_state_metrics_from_setting_counts(
            state,
            sweep.dimension,
            setting_counts,
            n_physical=n_physical,
            delay_dt=int(delay_dt),
            dt_seconds=dt_seconds,
            backend_name=backend.name,
            backend_config=backend_config,
            state_family=sweep.state_family,
        )
        results.append(record)
    return results


def run_hardware_fixed_n_sweep(
    configs: Sequence[SweepConfig],
    backend_config: BackendConfig,
    *,
    bootstrap_samples: int = 0,
    confidence_level: float = 0.95,
    progress: ProgressCallback | None = None,
) -> list[dict[str, Any]]:
    """Run canonical-probe fixed-``n`` hardware sweeps on an IBM Runtime backend.

    For each logical dimension at a fixed physical-qubit count, the hardware lane prepares the
    canonical probe ensemble, performs full output-state tomography for every requested delay,
    and reports the average fidelity, leakage, and in-subspace fidelity across that ensemble.
    Optional multinomial bootstrapping is applied to the observed tomography counts rather than
    to a separate acquisition, so the point estimate and confidence interval are derived from the
    same live dataset.
    """
    if not configs:
        return []

    execution_dependencies = _resolve_hardware_execution_dependencies()
    (
        select_backend_fn,
        validate_backend_for_experiment_fn,
        *_rest,
    ) = execution_dependencies

    backend = select_backend_fn(backend_config)
    dt_seconds = backend_dt_seconds(backend)
    max_required_qubits = max(
        3 * resolved_n_physical(sweep.dimension, sweep.n_physical) for sweep in configs
    )
    validate_backend_for_experiment_fn(
        backend,
        n_required_qubits=max_required_qubits,
        correction_mode=backend_config.correction_mode,
        require_delay=any(delay_dt > 0 for sweep in configs for delay_dt in sweep.delay_dt_values),
    )

    results: list[dict[str, Any]] = []
    total = sum(len(sweep.delay_dt_values) for sweep in configs)
    completed = 0
    for sweep in configs:
        n_physical = resolved_n_physical(sweep.dimension, sweep.n_physical)
        bases = all_measurement_bases(n_physical)
        canonical_states = canonical_probe_states(sweep.dimension)
        for delay_dt in sweep.delay_dt_values:
            completed += 1
            _emit_progress(
                progress,
                (
                    f"hardware fixed-n sweep {completed}/{total}: "
                    f"d={sweep.dimension}, n={n_physical}, delay_dt={int(delay_dt)}"
                ),
            )

            setting_counts_by_probe = _collect_hardware_setting_counts_for_states(
                canonical_states,
                sweep.dimension,
                n_physical=n_physical,
                delay_dt=int(delay_dt),
                backend_config=backend_config,
                backend=backend,
                execution_dependencies=execution_dependencies,
            )

            probe_records: list[dict[str, float]] = []
            for logical_state, setting_counts in zip(canonical_states, setting_counts_by_probe):
                state_record, _rho = _hardware_state_metrics_from_setting_counts(
                    logical_state,
                    sweep.dimension,
                    setting_counts,
                    n_physical=n_physical,
                    delay_dt=int(delay_dt),
                    dt_seconds=dt_seconds,
                    backend_name=backend.name,
                    backend_config=backend_config,
                    state_family="canonical_probe",
                )
                probe_records.append(
                    {
                        "fidelity": float(state_record["fidelity"]),
                        "leakage": float(state_record["leakage"]),
                        "in_subspace_fidelity": float(state_record["in_subspace_fidelity"]),
                    }
                )

            record: dict[str, Any] = {
                "dimension": sweep.dimension,
                "n_physical": n_physical,
                "physical_hilbert_dimension": physical_hilbert_dimension_for_logical_dimension(
                    sweep.dimension, n_physical
                ),
                "fill_ratio": fill_ratio(sweep.dimension, n_physical),
                "delay_dt": int(delay_dt),
                "dt_ns": delay_dt_to_ns(delay_dt, dt_seconds=dt_seconds),
                "backend_name": backend.name,
                "shots": backend_config.shots,
                "state_family": "canonical_probe_average",
                "correction_mode": backend_config.correction_mode,
                "simulation_lane": "ibm_runtime",
                "probe_ensemble_size": float(len(canonical_states)),
                "fidelity": float(np.mean([item["fidelity"] for item in probe_records])),
                "leakage": float(np.mean([item["leakage"] for item in probe_records])),
                "in_subspace_fidelity": float(
                    np.mean([item["in_subspace_fidelity"] for item in probe_records])
                ),
                "avg_probe_fidelity": float(np.mean([item["fidelity"] for item in probe_records])),
                "avg_probe_leakage": float(np.mean([item["leakage"] for item in probe_records])),
                "avg_probe_in_subspace_fidelity": float(
                    np.mean([item["in_subspace_fidelity"] for item in probe_records])
                ),
            }
            if bootstrap_samples > 0:
                ci_summary = bootstrap_average_tomography_metrics(
                    canonical_states,
                    sweep.dimension,
                    setting_counts_by_probe,
                    n_physical=n_physical,
                    bootstrap_samples=bootstrap_samples,
                    confidence_level=confidence_level,
                    seed=sweep.random_seed + completed,
                )
                record["observed_fidelity"] = record["fidelity"]
                record["observed_leakage"] = record["leakage"]
                record["observed_in_subspace_fidelity"] = record["in_subspace_fidelity"]
                record["observed_avg_probe_fidelity"] = record["avg_probe_fidelity"]
                record["observed_avg_probe_leakage"] = record["avg_probe_leakage"]
                record["observed_avg_probe_in_subspace_fidelity"] = record["avg_probe_in_subspace_fidelity"]
                record.update(ci_summary)
                record["fidelity"] = ci_summary["avg_probe_fidelity_bootstrap_mean"]
                record["leakage"] = ci_summary["avg_probe_leakage_bootstrap_mean"]
                record["in_subspace_fidelity"] = ci_summary[
                    "avg_probe_in_subspace_fidelity_bootstrap_mean"
                ]
                record["avg_probe_fidelity"] = ci_summary["avg_probe_fidelity_bootstrap_mean"]
                record["avg_probe_leakage"] = ci_summary["avg_probe_leakage_bootstrap_mean"]
                record["avg_probe_in_subspace_fidelity"] = ci_summary[
                    "avg_probe_in_subspace_fidelity_bootstrap_mean"
                ]
                record["fidelity_ci_low"] = ci_summary["avg_probe_fidelity_ci_low"]
                record["fidelity_ci_high"] = ci_summary["avg_probe_fidelity_ci_high"]
                record["leakage_ci_low"] = ci_summary["avg_probe_leakage_ci_low"]
                record["leakage_ci_high"] = ci_summary["avg_probe_leakage_ci_high"]
                record["in_subspace_fidelity_ci_low"] = ci_summary[
                    "avg_probe_in_subspace_fidelity_ci_low"
                ]
                record["in_subspace_fidelity_ci_high"] = ci_summary[
                    "avg_probe_in_subspace_fidelity_ci_high"
                ]
            results.append(record)
    return results


def run_hardware_fixed_n_process_tomography(
    configs: Sequence[SweepConfig],
    backend_config: BackendConfig,
    *,
    bootstrap_samples: int = 0,
    confidence_level: float = 0.95,
    progress: ProgressCallback | None = None,
) -> list[dict[str, Any]]:
    """Run fixed-``n`` logical process tomography on IBM Runtime hardware."""
    if not configs:
        return []

    execution_dependencies = _resolve_hardware_execution_dependencies()
    (
        select_backend_fn,
        validate_backend_for_experiment_fn,
        *_rest,
    ) = execution_dependencies

    backend = select_backend_fn(backend_config)
    dt_seconds = backend_dt_seconds(backend)
    max_required_qubits = max(
        3 * resolved_n_physical(sweep.dimension, sweep.n_physical) for sweep in configs
    )
    validate_backend_for_experiment_fn(
        backend,
        n_required_qubits=max_required_qubits,
        correction_mode=backend_config.correction_mode,
        require_delay=any(delay_dt > 0 for sweep in configs for delay_dt in sweep.delay_dt_values),
    )

    results: list[dict[str, Any]] = []
    total = sum(len(sweep.delay_dt_values) for sweep in configs)
    completed = 0
    for sweep in configs:
        n_physical = resolved_n_physical(sweep.dimension, sweep.n_physical)
        input_states = process_tomography_probe_states(sweep.dimension)
        input_densities = [pure_state_density(state) for state in input_states]
        for delay_dt in sweep.delay_dt_values:
            completed += 1
            _emit_progress(
                progress,
                (
                    f"hardware process tomography {completed}/{total}: "
                    f"d={sweep.dimension}, n={n_physical}, delay_dt={int(delay_dt)}"
                ),
            )
            setting_counts_by_probe = _collect_hardware_setting_counts_for_states(
                input_states,
                sweep.dimension,
                n_physical=n_physical,
                delay_dt=int(delay_dt),
                backend_config=backend_config,
                backend=backend,
                execution_dependencies=execution_dependencies,
            )

            probe_records: list[dict[str, Any]] = []
            logical_outputs: list[np.ndarray] = []
            for logical_state, setting_counts in zip(input_states, setting_counts_by_probe):
                state_record, rho = _hardware_state_metrics_from_setting_counts(
                    logical_state,
                    sweep.dimension,
                    setting_counts,
                    n_physical=n_physical,
                    delay_dt=int(delay_dt),
                    dt_seconds=dt_seconds,
                    backend_name=backend.name,
                    backend_config=backend_config,
                    state_family="process_tomography_probe",
                    simulation_lane="ibm_runtime_process_tomography",
                )
                probe_records.append(state_record)
                logical_outputs.append(
                    renormalized_logical_subspace_density(rho, sweep.dimension, n_physical)
                )

            superoperator = reconstruct_superoperator(input_densities, logical_outputs)
            process_fidelity = process_fidelity_to_identity(superoperator, sweep.dimension)
            record: dict[str, Any] = {
                "dimension": sweep.dimension,
                "n_physical": n_physical,
                "physical_hilbert_dimension": physical_hilbert_dimension_for_logical_dimension(
                    sweep.dimension, n_physical
                ),
                "fill_ratio": fill_ratio(sweep.dimension, n_physical),
                "delay_dt": int(delay_dt),
                "dt_ns": delay_dt_to_ns(delay_dt, dt_seconds=dt_seconds),
                "backend_name": backend.name,
                "shots": backend_config.shots,
                "state_family": "process_tomography_probe",
                "correction_mode": backend_config.correction_mode,
                "simulation_lane": "ibm_runtime_process_tomography",
                "probe_ensemble_size": float(len(input_states)),
                "fidelity": float(np.mean([item["fidelity"] for item in probe_records])),
                "leakage": float(np.mean([item["leakage"] for item in probe_records])),
                "in_subspace_fidelity": float(
                    np.mean([item["in_subspace_fidelity"] for item in probe_records])
                ),
                "avg_probe_fidelity": float(np.mean([item["fidelity"] for item in probe_records])),
                "avg_probe_leakage": float(np.mean([item["leakage"] for item in probe_records])),
                "avg_probe_in_subspace_fidelity": float(
                    np.mean([item["in_subspace_fidelity"] for item in probe_records])
                ),
                "process_fidelity": process_fidelity,
                "average_gate_fidelity": average_gate_fidelity_from_process_fidelity(
                    process_fidelity, sweep.dimension
                ),
            }
            if bootstrap_samples > 0:
                avg_ci_summary = bootstrap_average_tomography_metrics(
                    input_states,
                    sweep.dimension,
                    setting_counts_by_probe,
                    n_physical=n_physical,
                    bootstrap_samples=bootstrap_samples,
                    confidence_level=confidence_level,
                    seed=sweep.random_seed + 10000 * completed,
                )
                record["observed_fidelity"] = record["fidelity"]
                record["observed_leakage"] = record["leakage"]
                record["observed_in_subspace_fidelity"] = record["in_subspace_fidelity"]
                record["observed_avg_probe_fidelity"] = record["avg_probe_fidelity"]
                record["observed_avg_probe_leakage"] = record["avg_probe_leakage"]
                record["observed_avg_probe_in_subspace_fidelity"] = record[
                    "avg_probe_in_subspace_fidelity"
                ]
                record.update(avg_ci_summary)
                record["fidelity"] = avg_ci_summary["avg_probe_fidelity_bootstrap_mean"]
                record["leakage"] = avg_ci_summary["avg_probe_leakage_bootstrap_mean"]
                record["in_subspace_fidelity"] = avg_ci_summary[
                    "avg_probe_in_subspace_fidelity_bootstrap_mean"
                ]
                record["avg_probe_fidelity"] = avg_ci_summary["avg_probe_fidelity_bootstrap_mean"]
                record["avg_probe_leakage"] = avg_ci_summary["avg_probe_leakage_bootstrap_mean"]
                record["avg_probe_in_subspace_fidelity"] = avg_ci_summary[
                    "avg_probe_in_subspace_fidelity_bootstrap_mean"
                ]
                record["fidelity_ci_low"] = avg_ci_summary["avg_probe_fidelity_ci_low"]
                record["fidelity_ci_high"] = avg_ci_summary["avg_probe_fidelity_ci_high"]
                record["leakage_ci_low"] = avg_ci_summary["avg_probe_leakage_ci_low"]
                record["leakage_ci_high"] = avg_ci_summary["avg_probe_leakage_ci_high"]
                record["in_subspace_fidelity_ci_low"] = avg_ci_summary[
                    "avg_probe_in_subspace_fidelity_ci_low"
                ]
                record["in_subspace_fidelity_ci_high"] = avg_ci_summary[
                    "avg_probe_in_subspace_fidelity_ci_high"
                ]
                process_ci_summary = bootstrap_process_tomography_metrics(
                    sweep.dimension,
                    input_states,
                    setting_counts_by_probe,
                    n_physical=n_physical,
                    bootstrap_samples=bootstrap_samples,
                    confidence_level=confidence_level,
                    seed=sweep.random_seed + 20000 * completed,
                )
                record["observed_process_fidelity"] = record["process_fidelity"]
                record["observed_average_gate_fidelity"] = record["average_gate_fidelity"]
                record.update(process_ci_summary)
                record["process_fidelity"] = process_ci_summary["process_fidelity_bootstrap_mean"]
                record["average_gate_fidelity"] = process_ci_summary[
                    "average_gate_fidelity_bootstrap_mean"
                ]
            results.append(record)
    return results


def run_multi_backend_fixed_n_sweep(
    configs: Sequence[SweepConfig],
    backend_configs: Sequence[BackendConfig],
    *,
    bootstrap_samples: int = 0,
    confidence_level: float = 0.95,
    progress: ProgressCallback | None = None,
) -> list[dict[str, Any]]:
    """Run the fixed-n hardware sweep separately on multiple IBM backends."""
    if not backend_configs:
        raise ValueError("backend_configs cannot be empty")

    results: list[dict[str, Any]] = []
    total_backends = len(backend_configs)
    for index, backend_config in enumerate(backend_configs, start=1):
        backend_name = backend_config.backend_name or f"backend_{index}"
        _emit_progress(
            progress,
            f"multi-backend hardware fixed-n sweep {index}/{total_backends}: backend={backend_name}",
        )
        results.extend(
            run_hardware_fixed_n_sweep(
                configs,
                backend_config,
                bootstrap_samples=bootstrap_samples,
                confidence_level=confidence_level,
                progress=progress,
            )
        )
    return results


def run_multi_backend_fixed_n_process_tomography(
    configs: Sequence[SweepConfig],
    backend_configs: Sequence[BackendConfig],
    *,
    bootstrap_samples: int = 0,
    confidence_level: float = 0.95,
    progress: ProgressCallback | None = None,
) -> list[dict[str, Any]]:
    """Run fixed-n logical process tomography separately on multiple IBM backends."""
    if not backend_configs:
        raise ValueError("backend_configs cannot be empty")

    results: list[dict[str, Any]] = []
    total_backends = len(backend_configs)
    for index, backend_config in enumerate(backend_configs, start=1):
        backend_name = backend_config.backend_name or f"backend_{index}"
        _emit_progress(
            progress,
            (
                f"multi-backend hardware process tomography {index}/{total_backends}: "
                f"backend={backend_name}"
            ),
        )
        results.extend(
            run_hardware_fixed_n_process_tomography(
                configs,
                backend_config,
                bootstrap_samples=bootstrap_samples,
                confidence_level=confidence_level,
                progress=progress,
            )
        )
    return results


def run_hardware_process_tomography(
    sweep: SweepConfig,
    backend_config: BackendConfig,
    *,
    bootstrap_samples: int = 0,
    confidence_level: float = 0.95,
    progress: ProgressCallback | None = None,
) -> list[dict[str, Any]]:
    """Run logical process tomography on IBM Runtime hardware for one dimension sweep."""
    return run_hardware_fixed_n_process_tomography(
        [sweep],
        backend_config,
        bootstrap_samples=bootstrap_samples,
        confidence_level=confidence_level,
        progress=progress,
    )


def summarize_results(records: list[dict[str, Any]]) -> str:
    """Build or parse structured comparison summaries for fixed-n analysis reports."""
    if not records:
        return "No records."
    lines = []
    for rec in records:
        if "delay_dt" in rec and rec.get("dt_ns") is not None:
            x_label = f"delay_dt={rec['delay_dt']} ({float(rec['dt_ns']):.3f} ns)"
        elif "delay_dt" in rec:
            x_label = f"delay_dt={rec['delay_dt']}"
        else:
            x_label = f"step={rec.get('step', '?')}"
        parts = [
            f"d={rec['dimension']}",
            f"n={rec['n_physical']}",
            f"phi={rec['fill_ratio']:.3f}",
            x_label,
            f"F={rec['fidelity']:.6f}",
            f"L={rec['leakage']:.6f}",
            f"F_sub={rec['in_subspace_fidelity']:.6f}",
        ]
        if "process_fidelity" in rec:
            parts.append(f"F_proc={float(rec['process_fidelity']):.6f}")
        if "average_gate_fidelity" in rec:
            parts.append(f"F_avg={float(rec['average_gate_fidelity']):.6f}")
        parts.append(f"lane={rec.get('simulation_lane', 'unknown')}")
        lines.append(" | ".join(parts))
    return "\n".join(lines)


__all__ = [
    "make_probe_state",
    "fixed_n_dimensions",
    "fixed_n_sweep_configs",
    "run_markovian_fixed_n_sweep",
    "run_aer_fixed_n_sweep",
    "run_correlated_memory_fixed_n_sweep",
    "run_blp_memory_scan",
    "run_blp_random_telegraph_scan",
    "run_hardware_delay_sweep",
    "run_hardware_fixed_n_sweep",
    "run_hardware_process_tomography",
    "run_hardware_fixed_n_process_tomography",
    "run_multi_backend_fixed_n_sweep",
    "run_multi_backend_fixed_n_process_tomography",
    "summarize_results",
]
