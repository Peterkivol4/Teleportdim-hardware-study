from __future__ import annotations

import numpy as np

from .config import BackendConfig, SweepConfig
from .circuits import append_output_measurements, build_block_teleportation_circuit
from .encoding import (
    delay_dt_to_ns,
    embed_logical_state,
    fill_ratio,
    physical_hilbert_dimension_for_logical_dimension,
    resolved_aer_dt_ns_per_dt,
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
from .postprocess import corrected_counts_from_deferred_shots
from .process import (
    process_fidelity_to_identity,
    process_tomography_probe_states,
    reconstruct_superoperator,
)
from .statistics import (
    bootstrap_average_tomography_metrics,
    bootstrap_process_tomography_metrics,
    bootstrap_tomography_metrics,
)
from .tomography import all_measurement_bases, reconstruct_density_matrix


def make_probe_state(sweep: SweepConfig) -> np.ndarray:
    """Construct the configured probe state without introducing an Aer/sweeps import cycle."""
    from .sweeps import make_probe_state as _make_probe_state

    return _make_probe_state(sweep)

from collections import Counter
from collections.abc import Iterable, Sequence
from typing import Any, cast

try:  # pragma: no cover - optional import guard
    from qiskit import transpile
    from qiskit.circuit import Delay
    from qiskit_aer import AerSimulator
    from qiskit_aer.noise import (
        NoiseModel,
        RelaxationNoisePass,
        depolarizing_error,
        thermal_relaxation_error,
    )
except ImportError:  # pragma: no cover
    transpile = None
    Delay = None
    AerSimulator = None
    NoiseModel = None
    RelaxationNoisePass = None
    depolarizing_error = None
    thermal_relaxation_error = None



class AerExecutionError(RuntimeError):
    """Raised when the optional Aer lane cannot execute."""


def _require_aer_imports() -> None:
    """Aer simulation helper for local noisy validation of encoded teleportation circuits."""
    if (
        transpile is None
        or AerSimulator is None
        or NoiseModel is None
        or depolarizing_error is None
        or thermal_relaxation_error is None
    ):
        raise AerExecutionError(
            "Qiskit Aer dependencies are not installed. Install qiskit and qiskit-aer to use the Aer benchmarking lane."
        )


def counts_register_layout_from_circuit(circuit: Any) -> list[tuple[str, int]]:
    """Return the classical-register layout needed to parse combined Qiskit count strings."""
    return [(reg.name, int(reg.size)) for reg in getattr(circuit, "cregs", [])]


def split_combined_register_string(
    bitstring: str,
    register_layout: Sequence[tuple[str, int]],
) -> dict[str, str]:
    """Split a Qiskit-style combined classical string into named register substrings.

    Qiskit renders grouped classical strings from the highest-addressed register chunk
    to the lowest-addressed one, which is the reverse of ``circuit.cregs`` order.
    """
    cleaned = bitstring.strip()
    if not register_layout:
        return {}
    rendered_layout = list(reversed(register_layout))

    chunks = cleaned.split()
    if len(chunks) == len(rendered_layout):
        return {name: chunk for (name, _), chunk in zip(rendered_layout, chunks)}

    flat = cleaned.replace(" ", "")
    expected_width = sum(width for _, width in rendered_layout)
    if len(flat) != expected_width:
        raise AerExecutionError(
            f"could not split combined bitstring {bitstring!r}; expected width {expected_width}"
        )

    result: dict[str, str] = {}
    offset = 0
    for name, width in rendered_layout:
        result[name] = flat[offset : offset + width]
        offset += width
    return result


def marginalize_combined_counts_for_register(
    counts: dict[str, int],
    register_layout: Sequence[tuple[str, int]],
    register_name: str,
) -> dict[str, int]:
    """Aer simulation helper for local noisy validation of encoded teleportation circuits."""
    target: Counter[str] = Counter()
    for bitstring, shots in counts.items():
        split = split_combined_register_string(bitstring, register_layout)
        if register_name not in split:
            raise AerExecutionError(f"register {register_name!r} not found in combined counts")
        target[split[register_name]] += int(shots)
    return dict(target)


def extract_register_shots_from_memory(
    memory: Iterable[str],
    register_layout: Sequence[tuple[str, int]],
    register_name: str,
) -> list[str]:
    """Extract register shots from memory for encoded logical-state analysis."""
    shots: list[str] = []
    for bitstring in memory:
        split = split_combined_register_string(bitstring, register_layout)
        if register_name not in split:
            raise AerExecutionError(f"register {register_name!r} not found in memory shot")
        shots.append(split[register_name])
    return shots


def build_basic_noise_model(
    *,
    depolarizing_1q: float = 0.0,
    depolarizing_2q: float = 0.0,
    t1: float | None = None,
    t2: float | None = None,
    single_qubit_gate_time: float = 50e-9,
    two_qubit_gate_time: float = 300e-9,
    measure_time: float = 1e-6,
) -> Any:
    """Aer simulation helper for local noisy validation of encoded teleportation circuits."""
    _require_aer_imports()
    noise_model = NoiseModel()

    if depolarizing_1q > 0.0:
        error_1q = depolarizing_error(float(depolarizing_1q), 1)
        noise_model.add_all_qubit_quantum_error(
            error_1q,
            ["id", "rz", "sx", "x", "z", "h", "sdg"],
        )
    if depolarizing_2q > 0.0:
        error_2q = depolarizing_error(float(depolarizing_2q), 2)
        noise_model.add_all_qubit_quantum_error(error_2q, ["cx", "cz", "ecr"])

    if t1 is not None and t2 is not None:
        t1f = float(t1)
        t2f = float(t2)
        relax_1q = thermal_relaxation_error(t1f, t2f, single_qubit_gate_time)
        relax_meas = thermal_relaxation_error(t1f, t2f, measure_time)
        relax_2q = thermal_relaxation_error(t1f, t2f, two_qubit_gate_time).expand(
            thermal_relaxation_error(t1f, t2f, two_qubit_gate_time)
        )
        noise_model.add_all_qubit_quantum_error(
            relax_1q,
            ["id", "rz", "sx", "x", "z", "h", "sdg"],
        )
        noise_model.add_all_qubit_quantum_error(relax_2q, ["cx", "cz", "ecr"])
        noise_model.add_all_qubit_quantum_error(relax_meas, ["measure"])

    # Store calibration metadata so the Aer execution path can add duration-scaled
    # relaxation specifically on Delay instructions.
    noise_model._teleportdim_t1 = None if t1 is None else float(t1)
    noise_model._teleportdim_t2 = None if t2 is None else float(t2)
    return noise_model


def make_aer_simulator(
    *,
    method: str = "automatic",
    backend: Any | None = None,
    noise_model: Any | None = None,
) -> Any:
    """Aer simulation helper for local noisy validation of encoded teleportation circuits."""
    _require_aer_imports()
    if backend is not None:
        return AerSimulator.from_backend(backend)
    if noise_model is not None:
        return AerSimulator(method=method, noise_model=noise_model)
    return AerSimulator(method=method)


def _apply_delay_relaxation_pass(
    circuits: Sequence[Any],
    *,
    noise_model: Any | None,
    dt_ns_per_dt: float | None,
) -> list[Any]:
    """Append delay-duration relaxation channels to circuits when T1/T2 are configured."""
    if noise_model is None or RelaxationNoisePass is None or Delay is None:
        return list(circuits)

    t1 = getattr(noise_model, "_teleportdim_t1", None)
    t2 = getattr(noise_model, "_teleportdim_t2", None)
    if t1 is None or t2 is None or float(t1) <= 0.0 or float(t2) <= 0.0:
        return list(circuits)

    resolved_dt_seconds = resolved_aer_dt_ns_per_dt(dt_ns_per_dt) * 1e-9
    noisy_circuits: list[Any] = []
    for circuit in circuits:
        relaxation_pass = RelaxationNoisePass(
            [float(t1)] * circuit.num_qubits,
            [float(t2)] * circuit.num_qubits,
            dt=resolved_dt_seconds,
            op_types=Delay,
        )
        noisy_circuits.append(relaxation_pass(circuit))
    return noisy_circuits


def _run_aer_tomography_for_state(
    logical_state: np.ndarray,
    dimension: int,
    *,
    n_physical: int | None = None,
    delay_dt: int,
    backend_config: BackendConfig,
    simulator: Any,
    noise_model: Any | None,
    seed_simulator: int,
    bootstrap_samples: int = 0,
    confidence_level: float = 0.95,
    dt_ns_per_dt: float | None = None,
    state_family: str = "custom",
) -> tuple[dict[str, Any], dict[str, dict[str, int]], np.ndarray]:
    """Execute a full tomography bundle for one logical input state on Aer."""
    resolved_n = resolved_n_physical(dimension, n_physical)
    resolved_dt_ns = resolved_aer_dt_ns_per_dt(dt_ns_per_dt)
    embedded_target = embed_logical_state(logical_state, dimension, resolved_n)
    bases = all_measurement_bases(resolved_n)

    program = build_block_teleportation_circuit(
        cast(Sequence[complex], logical_state),
        dimension,
        n_physical=resolved_n,
        delay_after_entanglement_dt=int(delay_dt),
        correction_mode=backend_config.correction_mode,
    )
    tomo_circuits = [append_output_measurements(program, basis) for basis in bases]
    transpiled = transpile(
        tomo_circuits,
        simulator,
        optimization_level=backend_config.optimization_level,
    )
    transpiled = _apply_delay_relaxation_pass(
        transpiled,
        noise_model=noise_model,
        dt_ns_per_dt=resolved_dt_ns,
    )
    job = simulator.run(
        transpiled,
        shots=backend_config.shots,
        memory=(backend_config.correction_mode == "deferred"),
        seed_simulator=seed_simulator,
    )
    result = job.result()

    setting_counts: dict[str, dict[str, int]] = {}
    for index, (basis, circuit) in enumerate(zip(bases, transpiled)):
        combined_counts = result.get_counts(index)
        layout = counts_register_layout_from_circuit(circuit)
        reg_name = f"out_{basis}"
        if backend_config.correction_mode == "dynamic":
            setting_counts[basis] = marginalize_combined_counts_for_register(
                dict(combined_counts),
                layout,
                reg_name,
            )
        else:
            memory = result.get_memory(index)
            output_shots = extract_register_shots_from_memory(memory, layout, reg_name)
            bell_shots = extract_register_shots_from_memory(memory, layout, "bell")
            setting_counts[basis] = corrected_counts_from_deferred_shots(
                output_shots=output_shots,
                bell_shots=bell_shots,
                basis=basis,
            )

    rho = reconstruct_density_matrix(setting_counts)
    record = {
        "dimension": dimension,
        "n_physical": resolved_n,
        "physical_hilbert_dimension": physical_hilbert_dimension_for_logical_dimension(dimension, resolved_n),
        "fill_ratio": fill_ratio(dimension, resolved_n),
        "delay_dt": int(delay_dt),
        "dt_ns": delay_dt_to_ns(delay_dt, dt_ns_per_dt=resolved_dt_ns),
        "backend_name": getattr(simulator, "name", type(simulator).__name__),
        "fidelity": pure_state_fidelity(embedded_target, rho),
        "leakage": leakage_probability(rho, dimension, resolved_n),
        "in_subspace_fidelity": in_subspace_fidelity(logical_state, rho, dimension, resolved_n),
        "shots": backend_config.shots,
        "state_family": state_family,
        "correction_mode": backend_config.correction_mode,
        "simulation_lane": "aer",
        "noise_model": "custom" if noise_model is not None else "ideal",
    }
    if bootstrap_samples > 0:
        ci_summary = bootstrap_tomography_metrics(
            logical_state,
            dimension,
            setting_counts,
            n_physical=resolved_n,
            bootstrap_samples=bootstrap_samples,
            confidence_level=confidence_level,
            seed=seed_simulator,
        )
        record["observed_fidelity"] = record["fidelity"]
        record["observed_leakage"] = record["leakage"]
        record["observed_in_subspace_fidelity"] = record["in_subspace_fidelity"]
        record.update(ci_summary)
        record["fidelity"] = ci_summary["fidelity_bootstrap_mean"]
        record["leakage"] = ci_summary["leakage_bootstrap_mean"]
        record["in_subspace_fidelity"] = ci_summary["in_subspace_fidelity_bootstrap_mean"]
    return record, setting_counts, rho


def run_aer_delay_sweep(
    sweep: SweepConfig,
    backend_config: BackendConfig,
    *,
    simulator: Any | None = None,
    noise_model: Any | None = None,
    method: str = "automatic",
    seed_simulator: int = 17,
    bootstrap_samples: int = 0,
    confidence_level: float = 0.95,
    dt_ns_per_dt: float | None = None,
) -> list[dict[str, Any]]:
    """Aer simulation helper for local noisy validation of encoded teleportation circuits."""
    _require_aer_imports()

    state = make_probe_state(sweep)
    sim = simulator if simulator is not None else make_aer_simulator(method=method, noise_model=noise_model)

    results: list[dict[str, Any]] = []
    for index, delay_dt in enumerate(sweep.delay_dt_values):
        record, _, _ = _run_aer_tomography_for_state(
            state,
            sweep.dimension,
            n_physical=sweep.n_physical,
            delay_dt=int(delay_dt),
            backend_config=backend_config,
            simulator=sim,
            noise_model=noise_model,
            seed_simulator=seed_simulator + index,
            bootstrap_samples=bootstrap_samples,
            confidence_level=confidence_level,
            dt_ns_per_dt=dt_ns_per_dt,
            state_family=sweep.state_family,
        )
        results.append(record)
    return results


def run_aer_process_tomography(
    sweep: SweepConfig,
    backend_config: BackendConfig,
    *,
    simulator: Any | None = None,
    noise_model: Any | None = None,
    method: str = "automatic",
    seed_simulator: int = 17,
    bootstrap_samples: int = 0,
    confidence_level: float = 0.95,
    dt_ns_per_dt: float | None = None,
) -> list[dict[str, Any]]:
    """Run logical process tomography on the Aer teleportation lane."""
    _require_aer_imports()
    sim = simulator if simulator is not None else make_aer_simulator(method=method, noise_model=noise_model)
    resolved_dt_ns = resolved_aer_dt_ns_per_dt(dt_ns_per_dt)

    input_states = process_tomography_probe_states(sweep.dimension)
    input_densities = [pure_state_density(state) for state in input_states]
    n_physical = resolved_n_physical(sweep.dimension, sweep.n_physical)
    records: list[dict[str, Any]] = []
    for delay_index, delay_dt in enumerate(sweep.delay_dt_values):
        probe_records: list[dict[str, Any]] = []
        probe_setting_counts: list[dict[str, dict[str, int]]] = []
        logical_outputs: list[np.ndarray] = []

        for probe_index, logical_state in enumerate(input_states):
            record, setting_counts, rho = _run_aer_tomography_for_state(
                logical_state,
                sweep.dimension,
                n_physical=n_physical,
                delay_dt=int(delay_dt),
                backend_config=backend_config,
                simulator=sim,
                noise_model=noise_model,
                seed_simulator=seed_simulator + 1000 * delay_index + probe_index,
                dt_ns_per_dt=dt_ns_per_dt,
                state_family="process_tomography_probe",
            )
            probe_records.append(record)
            probe_setting_counts.append(setting_counts)
            logical_outputs.append(renormalized_logical_subspace_density(rho, sweep.dimension, n_physical))

        superoperator = reconstruct_superoperator(input_densities, logical_outputs)
        process_fidelity = process_fidelity_to_identity(superoperator, sweep.dimension)
        record = {
            "dimension": sweep.dimension,
            "n_physical": n_physical,
            "physical_hilbert_dimension": physical_hilbert_dimension_for_logical_dimension(sweep.dimension, n_physical),
            "fill_ratio": fill_ratio(sweep.dimension, n_physical),
            "delay_dt": int(delay_dt),
            "dt_ns": delay_dt_to_ns(delay_dt, dt_ns_per_dt=resolved_dt_ns),
            "backend_name": getattr(sim, "name", type(sim).__name__),
            "shots": backend_config.shots,
            "state_family": "process_tomography_probe",
            "correction_mode": backend_config.correction_mode,
            "simulation_lane": "aer_process_tomography",
            "noise_model": "custom" if noise_model is not None else "ideal",
            "probe_ensemble_size": len(input_states),
            "fidelity": float(np.mean([item["fidelity"] for item in probe_records])),
            "leakage": float(np.mean([item["leakage"] for item in probe_records])),
            "in_subspace_fidelity": float(np.mean([item["in_subspace_fidelity"] for item in probe_records])),
            "avg_probe_fidelity": float(np.mean([item["fidelity"] for item in probe_records])),
            "avg_probe_leakage": float(np.mean([item["leakage"] for item in probe_records])),
            "avg_probe_in_subspace_fidelity": float(np.mean([item["in_subspace_fidelity"] for item in probe_records])),
            "process_fidelity": process_fidelity,
            "average_gate_fidelity": average_gate_fidelity_from_process_fidelity(
                process_fidelity, sweep.dimension
            ),
        }
        if bootstrap_samples > 0:
            avg_ci_summary = bootstrap_average_tomography_metrics(
                input_states,
                sweep.dimension,
                probe_setting_counts,
                n_physical=n_physical,
                bootstrap_samples=bootstrap_samples,
                confidence_level=confidence_level,
                seed=seed_simulator + 10000 * (delay_index + 1),
            )
            record["observed_fidelity"] = record["fidelity"]
            record["observed_leakage"] = record["leakage"]
            record["observed_in_subspace_fidelity"] = record["in_subspace_fidelity"]
            record.update(avg_ci_summary)
            record["fidelity"] = avg_ci_summary["avg_probe_fidelity_bootstrap_mean"]
            record["leakage"] = avg_ci_summary["avg_probe_leakage_bootstrap_mean"]
            record["in_subspace_fidelity"] = avg_ci_summary["avg_probe_in_subspace_fidelity_bootstrap_mean"]
            record["avg_probe_fidelity"] = avg_ci_summary["avg_probe_fidelity_bootstrap_mean"]
            record["avg_probe_leakage"] = avg_ci_summary["avg_probe_leakage_bootstrap_mean"]
            record["avg_probe_in_subspace_fidelity"] = avg_ci_summary["avg_probe_in_subspace_fidelity_bootstrap_mean"]
            record["fidelity_ci_low"] = avg_ci_summary["avg_probe_fidelity_ci_low"]
            record["fidelity_ci_high"] = avg_ci_summary["avg_probe_fidelity_ci_high"]
            record["leakage_ci_low"] = avg_ci_summary["avg_probe_leakage_ci_low"]
            record["leakage_ci_high"] = avg_ci_summary["avg_probe_leakage_ci_high"]
            record["in_subspace_fidelity_ci_low"] = avg_ci_summary["avg_probe_in_subspace_fidelity_ci_low"]
            record["in_subspace_fidelity_ci_high"] = avg_ci_summary["avg_probe_in_subspace_fidelity_ci_high"]
            process_ci_summary = bootstrap_process_tomography_metrics(
                sweep.dimension,
                input_states,
                probe_setting_counts,
                n_physical=n_physical,
                bootstrap_samples=bootstrap_samples,
                confidence_level=confidence_level,
                seed=seed_simulator + 20000 * (delay_index + 1),
            )
            record["observed_process_fidelity"] = record["process_fidelity"]
            record["observed_average_gate_fidelity"] = record["average_gate_fidelity"]
            record.update(process_ci_summary)
            record["process_fidelity"] = process_ci_summary["process_fidelity_bootstrap_mean"]
            record["average_gate_fidelity"] = process_ci_summary["average_gate_fidelity_bootstrap_mean"]
        records.append(record)
    return records


__all__ = [
    "AerExecutionError",
    "counts_register_layout_from_circuit",
    "split_combined_register_string",
    "marginalize_combined_counts_for_register",
    "extract_register_shots_from_memory",
    "build_basic_noise_model",
    "make_aer_simulator",
    "run_aer_delay_sweep",
    "run_aer_process_tomography",
]
