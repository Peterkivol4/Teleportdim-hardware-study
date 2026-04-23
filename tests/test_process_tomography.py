from __future__ import annotations

import numpy as np

from teleportdim.metrics import pure_state_density
from teleportdim.process import (
    choi_matrix_from_superoperator,
    apply_superoperator,
    process_fidelity_to_identity,
    process_tomography_probe_states,
    reconstruct_superoperator,
)
from teleportdim.statistics import (
    bootstrap_average_tomography_metrics,
    bootstrap_process_tomography_metrics,
    bootstrap_tomography_metrics,
)
from teleportdim import BackendConfig, SweepConfig, build_basic_noise_model
from teleportdim.aer import run_aer_process_tomography


def test_process_tomography_probe_state_count_is_dimension_squared():
    probes = process_tomography_probe_states(3)
    assert len(probes) == 9
    assert all(np.isclose(np.linalg.norm(state), 1.0) for state in probes)


def test_reconstruct_superoperator_identity_has_unit_process_fidelity():
    probes = process_tomography_probe_states(3)
    densities = [pure_state_density(state) for state in probes]
    superoperator = reconstruct_superoperator(densities, densities)
    recovered = apply_superoperator(superoperator, densities[0])
    assert np.allclose(recovered, densities[0])
    assert np.isclose(process_fidelity_to_identity(superoperator, 3), 1.0, atol=1e-8)


def test_choi_matrix_from_superoperator_identity_matches_maximally_entangled_projector():
    superoperator = np.eye(4, dtype=complex)
    choi = choi_matrix_from_superoperator(superoperator, 2)
    maximally_entangled = np.eye(2, dtype=complex).reshape(-1, order="F")
    expected = np.outer(maximally_entangled, maximally_entangled.conj())
    assert np.allclose(choi, expected)
    assert np.isclose(np.trace(choi), 2.0)


def test_reconstruct_superoperator_rejects_incomplete_probe_set():
    pytest = __import__("pytest")
    probes = process_tomography_probe_states(2)[:3]
    densities = [pure_state_density(state) for state in probes]
    with pytest.raises(ValueError, match="informationally complete"):
        reconstruct_superoperator(densities, densities)


def test_bootstrap_tomography_metrics_returns_confidence_interval_fields():
    logical_target = np.array([1.0, 1.0], dtype=complex) / np.sqrt(2.0)
    setting_counts = {
        "X": {"0": 256},
        "Y": {"0": 128, "1": 128},
        "Z": {"0": 128, "1": 128},
    }
    summary = bootstrap_tomography_metrics(
        logical_target,
        2,
        setting_counts,
        bootstrap_samples=32,
        confidence_level=0.95,
        seed=7,
    )
    assert summary["bootstrap_samples"] == 32
    assert summary["confidence_level"] == 0.95
    assert summary["fidelity_ci_low"] <= summary["fidelity_bootstrap_mean"] <= summary["fidelity_ci_high"]
    assert summary["leakage_ci_low"] <= summary["leakage_bootstrap_mean"] <= summary["leakage_ci_high"]
    assert (
        summary["in_subspace_fidelity_ci_low"]
        <= summary["in_subspace_fidelity_bootstrap_mean"]
        <= summary["in_subspace_fidelity_ci_high"]
    )
    assert 0.0 <= summary["fidelity_ci_low"] <= summary["fidelity_ci_high"] <= 1.0
    assert 0.0 <= summary["leakage_ci_low"] <= summary["leakage_ci_high"] <= 1.0
    assert 0.0 <= summary["in_subspace_fidelity_ci_low"] <= summary["in_subspace_fidelity_ci_high"] <= 1.0


def _single_qubit_setting_counts() -> list[dict[str, dict[str, int]]]:
    return [
        {"X": {"0": 64, "1": 64}, "Y": {"0": 64, "1": 64}, "Z": {"0": 128}},
        {"X": {"0": 64, "1": 64}, "Y": {"0": 64, "1": 64}, "Z": {"1": 128}},
        {"X": {"0": 128}, "Y": {"0": 64, "1": 64}, "Z": {"0": 64, "1": 64}},
        {"X": {"0": 64, "1": 64}, "Y": {"0": 128}, "Z": {"0": 64, "1": 64}},
    ]


def test_bootstrap_average_tomography_metrics_returns_confidence_interval_fields():
    logical_targets = process_tomography_probe_states(2)
    summary = bootstrap_average_tomography_metrics(
        logical_targets,
        2,
        _single_qubit_setting_counts(),
        bootstrap_samples=16,
        confidence_level=0.95,
        seed=11,
    )
    assert summary["bootstrap_samples"] == 16
    assert summary["confidence_level"] == 0.95
    assert summary["avg_probe_fidelity_ci_low"] <= summary["avg_probe_fidelity_bootstrap_mean"] <= summary["avg_probe_fidelity_ci_high"]
    assert summary["avg_probe_leakage_ci_low"] <= summary["avg_probe_leakage_bootstrap_mean"] <= summary["avg_probe_leakage_ci_high"]
    assert (
        summary["avg_probe_in_subspace_fidelity_ci_low"]
        <= summary["avg_probe_in_subspace_fidelity_bootstrap_mean"]
        <= summary["avg_probe_in_subspace_fidelity_ci_high"]
    )
    assert 0.0 <= summary["avg_probe_fidelity_ci_low"] <= summary["avg_probe_fidelity_ci_high"] <= 1.0
    assert 0.0 <= summary["avg_probe_leakage_ci_low"] <= summary["avg_probe_leakage_ci_high"] <= 1.0
    assert 0.0 <= summary["avg_probe_in_subspace_fidelity_ci_low"] <= summary["avg_probe_in_subspace_fidelity_ci_high"] <= 1.0


def test_bootstrap_process_tomography_metrics_returns_confidence_interval_fields():
    logical_targets = process_tomography_probe_states(2)
    summary = bootstrap_process_tomography_metrics(
        2,
        logical_targets,
        _single_qubit_setting_counts(),
        bootstrap_samples=16,
        confidence_level=0.95,
        seed=17,
    )
    assert summary["bootstrap_samples"] == 16
    assert summary["confidence_level"] == 0.95
    assert summary["process_fidelity_ci_low"] <= summary["process_fidelity_bootstrap_mean"] <= summary["process_fidelity_ci_high"]
    assert (
        summary["average_gate_fidelity_ci_low"]
        <= summary["average_gate_fidelity_bootstrap_mean"]
        <= summary["average_gate_fidelity_ci_high"]
    )
    assert 0.0 <= summary["process_fidelity_ci_low"] <= summary["process_fidelity_ci_high"] <= 1.0
    assert 0.0 <= summary["average_gate_fidelity_ci_low"] <= summary["average_gate_fidelity_ci_high"] <= 1.0


def test_run_aer_process_tomography_returns_high_process_fidelity_for_ideal_qubit_channel():
    pytest = __import__("pytest")
    pytest.importorskip("qiskit")
    pytest.importorskip("qiskit_aer")

    sweep = SweepConfig(dimension=2, delay_dt_values=[0], shots=512, state_family="computational")
    backend = BackendConfig(shots=512, correction_mode="dynamic")
    records = run_aer_process_tomography(sweep, backend, method="automatic", seed_simulator=23)

    assert len(records) == 1
    record = records[0]
    assert record["simulation_lane"] == "aer_process_tomography"
    assert record["process_fidelity"] >= 0.9
    assert record["average_gate_fidelity"] >= 0.9


def test_run_aer_process_tomography_respects_explicit_fixed_n_embedding():
    pytest = __import__("pytest")
    pytest.importorskip("qiskit")
    pytest.importorskip("qiskit_aer")

    sweep = SweepConfig(dimension=2, n_physical=2, delay_dt_values=[0], shots=256, state_family="computational")
    backend = BackendConfig(shots=256, correction_mode="dynamic")
    records = run_aer_process_tomography(sweep, backend, method="automatic", seed_simulator=29)

    assert len(records) == 1
    record = records[0]
    assert record["n_physical"] == 2
    assert record["physical_hilbert_dimension"] == 4
    assert record["fill_ratio"] == 0.5


def test_run_aer_process_tomography_bootstrap_points_land_inside_reported_intervals():
    pytest = __import__("pytest")
    pytest.importorskip("qiskit")
    pytest.importorskip("qiskit_aer")

    sweep = SweepConfig(dimension=2, n_physical=2, delay_dt_values=[0], shots=256, state_family="computational")
    backend = BackendConfig(shots=256, correction_mode="dynamic")
    record = run_aer_process_tomography(
        sweep,
        backend,
        method="automatic",
        bootstrap_samples=16,
        seed_simulator=31,
    )[0]

    assert record["dt_ns"] is not None
    assert record["fidelity_ci_low"] <= record["fidelity"] <= record["fidelity_ci_high"]
    assert record["leakage_ci_low"] <= record["leakage"] <= record["leakage_ci_high"]
    assert (
        record["in_subspace_fidelity_ci_low"]
        <= record["in_subspace_fidelity"]
        <= record["in_subspace_fidelity_ci_high"]
    )
    assert record["process_fidelity_ci_low"] <= record["process_fidelity"] <= record["process_fidelity_ci_high"]
    assert (
        record["average_gate_fidelity_ci_low"]
        <= record["average_gate_fidelity"]
        <= record["average_gate_fidelity_ci_high"]
    )


def test_run_aer_process_tomography_process_fidelity_decreases_when_delay_relaxation_is_strong():
    pytest = __import__("pytest")
    pytest.importorskip("qiskit")
    pytest.importorskip("qiskit_aer")

    sweep = SweepConfig(dimension=2, n_physical=2, delay_dt_values=[0, 64], shots=256, state_family="computational")
    backend = BackendConfig(shots=256, correction_mode="dynamic")
    records = run_aer_process_tomography(
        sweep,
        backend,
        method="automatic",
        noise_model=build_basic_noise_model(t1=1e-6, t2=1e-6),
        dt_ns_per_dt=10.0,
        seed_simulator=37,
    )
    by_delay = {record["delay_dt"]: record["process_fidelity"] for record in records}
    assert by_delay[64] < by_delay[0]
