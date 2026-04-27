from __future__ import annotations

from typing import Any
import numpy as np
import pytest
import teleportdim

from teleportdim.sweeps import (
    fixed_n_sweep_configs,
    run_aer_fixed_n_sweep,
    run_blp_memory_scan,
    run_blp_random_telegraph_scan,
    run_correlated_memory_fixed_n_sweep,
    run_hardware_fixed_n_sweep,
    run_hardware_process_tomography,
    run_markovian_fixed_n_sweep,
)


def test_markovian_fixed_n_sweep_includes_fill_ratio_metrics_and_probe_averages() -> None:
    configs = fixed_n_sweep_configs([2], delay_dt_values=[0, 5], state_family='computational')
    records = run_markovian_fixed_n_sweep(configs, t1=20.0, t2=15.0, t_dep=10.0, bootstrap_samples=8, dt_ns_per_dt=0.222)
    assert len(records) == 6
    assert all('fill_ratio' in record for record in records)
    assert all('fidelity' in record for record in records)
    assert all('leakage' in record for record in records)
    assert all('avg_probe_fidelity' in record for record in records)
    assert all(record['state_family'] == 'canonical_probe_average' for record in records)
    assert all('fidelity_ci_low' in record for record in records)
    assert sorted({record['delay_dt'] for record in records}) == [0, 5]
    assert [record['dt_ns'] for record in records if record['delay_dt'] == 0][0] == pytest.approx(0.0)
    assert [record['dt_ns'] for record in records if record['delay_dt'] == 5][0] == pytest.approx(1.11)
    assert any(record['leakage'] > 0.0 for record in records if record['delay_dt'] > 0)


def test_correlated_memory_fixed_n_sweep_tracks_steps() -> None:
    configs = fixed_n_sweep_configs([2], delay_dt_values=[0], state_family='fourier')
    records = run_correlated_memory_fixed_n_sweep(
        configs,
        steps=3,
        base_phase_flip_probability=0.15,
        memory_strength=0.6,
        samples=128,
    )
    assert len(records) == 12
    assert {record['step'] for record in records} == {0, 1, 2, 3}


def test_aer_fixed_n_sweep_runs_full_circuit_average_for_qubit_case() -> None:
    pytest = __import__("pytest")
    pytest.importorskip("qiskit")
    pytest.importorskip("qiskit_aer")

    configs = fixed_n_sweep_configs([1], delay_dt_values=[0], state_family='computational')
    records = run_aer_fixed_n_sweep(
        configs,
        depolarizing_1q=0.0,
        depolarizing_2q=0.0,
        bootstrap_samples=8,
        seed_simulator=23,
    )
    assert len(records) == 1
    record = records[0]
    assert record['simulation_lane'] == 'aer_circuit'
    assert record['probe_ensemble_size'] == 3.0
    assert record['fidelity'] >= 0.9
    assert record['dt_ns'] == pytest.approx(0.0)
    assert 'avg_probe_fidelity_ci_low' in record
    assert 'fidelity_ci_low' in record
    assert record['fidelity_ci_low'] <= record['fidelity'] <= record['fidelity_ci_high']
    assert record['avg_probe_fidelity_ci_low'] <= record['avg_probe_fidelity_ci_high']


def test_aer_fixed_n_sweep_bootstrap_handles_explicit_fixed_n_embedding() -> None:
    pytest = __import__("pytest")
    pytest.importorskip("qiskit")
    pytest.importorskip("qiskit_aer")

    configs = fixed_n_sweep_configs([2], delay_dt_values=[0], state_family='computational')
    for config in configs:
        config.shots = 128

    records = run_aer_fixed_n_sweep(
        configs,
        depolarizing_1q=0.0,
        depolarizing_2q=0.0,
        bootstrap_samples=8,
        seed_simulator=29,
    )

    assert len(records) == 3
    assert all(record['n_physical'] == 2 for record in records)
    assert all(record['dt_ns'] == pytest.approx(0.0) for record in records)
    assert all(record['fidelity_ci_low'] <= record['fidelity'] <= record['fidelity_ci_high'] for record in records)


def test_aer_fixed_n_sweep_tracks_delay_calibration_and_higher_dimension_decay() -> None:
    pytest = __import__("pytest")
    pytest.importorskip("qiskit")
    pytest.importorskip("qiskit_aer")

    configs = fixed_n_sweep_configs([2], delay_dt_values=[0, 64], state_family='computational')
    records = run_aer_fixed_n_sweep(
        configs,
        depolarizing_1q=0.0,
        depolarizing_2q=0.0,
        t1=1e-6,
        t2=1e-6,
        dt_ns_per_dt=100.0,
        seed_simulator=41,
    )
    by_dimension: dict[int, dict[int, dict[str, Any]]] = {}
    for record in records:
        by_dimension.setdefault(record['dimension'], {})[record['delay_dt']] = record

    assert by_dimension[2][64]['dt_ns'] == pytest.approx(6400.0)
    assert by_dimension[3][64]['fidelity'] < by_dimension[3][0]['fidelity']
    assert by_dimension[4][64]['fidelity'] < by_dimension[4][0]['fidelity']


def test_blp_memory_scan_returns_dimension_tagged_records() -> None:
    records = run_blp_memory_scan([2, 3], [0.0, 0.8], steps=4, base_phase_flip_probability=0.1, samples=2048)
    assert len(records) == 4
    assert {record['dimension'] for record in records} == {2, 3}
    by_strength = {record['memory_strength']: record['blp_measure'] for record in records if record['dimension'] == 2}
    assert by_strength[0.0] <= 1e-9
    assert by_strength[0.8] >= by_strength[0.0]


def test_blp_random_telegraph_scan_returns_calibrated_fixed_n_records() -> None:
    records = run_blp_random_telegraph_scan(
        [2, 3],
        [0.0125, 0.05],
        n_physical=2,
        steps=8,
        coupling_strength=0.4,
        samples=256,
    )
    assert len(records) == 4
    assert {record['n_physical'] for record in records} == {2}
    assert {record['dimension'] for record in records} == {2, 3}
    calibrated = [record for record in records if record['switching_probability'] == pytest.approx(0.0125)]
    assert calibrated
    assert all(record['probe_pair'] == 'fourier_k0_vs_k1' for record in records)
    assert all(record['correlation_time_steps'] is None or record['correlation_time_steps'] > 0 for record in records)
    assert all(record['blp_measure'] >= 0.0 for record in records)


def test_hardware_fixed_n_sweep_averages_canonical_probe_records(monkeypatch: Any) -> None:
    class FakeTarget:
        dt = 4e-9
        operation_names = {"if_else", "delay"}

    class FakeBackend:
        name = "fake_backend"
        num_qubits = 16
        target = FakeTarget()

    backend = FakeBackend()
    zero = np.array([1.0, 0.0], dtype=complex)
    one = np.array([0.0, 1.0], dtype=complex)
    plus = np.array([1.0, 1.0], dtype=complex) / np.sqrt(2.0)

    def fake_select_backend(_config: Any) -> Any:
        return backend

    def fake_validate_backend_for_experiment(_backend: Any, **_kwargs: Any) -> Any:
        return None

    def fake_build_block_teleportation_circuit(
        logical_state: Any,
        dimension: Any,
        *,
        n_physical: Any,
        delay_after_entanglement_dt: Any,
        correction_mode: Any,
    ) -> Any:
        return {
            "state": np.asarray(logical_state, dtype=complex),
            "dimension": dimension,
            "n_physical": n_physical,
            "delay_dt": delay_after_entanglement_dt,
            "correction_mode": correction_mode,
        }

    def fake_append_output_measurements(program: Any, basis: Any) -> Any:
        return {"state": program["state"], "basis": basis}

    def fake_transpile_isa(circuits: Any, backend: Any, optimization_level: Any) -> Any:
        assert backend is not None
        assert optimization_level == 1
        return list(circuits)

    def fake_run_sampler_job(circuits: Any, backend: Any, shots: Any, use_session: Any) -> Any:
        assert backend is not None
        assert shots == 64
        assert use_session is False
        return list(circuits)

    def fake_extract_register_counts(pub_result: Any, register_name: Any) -> Any:
        assert register_name.startswith("out_")
        state = pub_result["state"]
        basis = pub_result["basis"]
        if np.allclose(state, zero):
            probs = {"X": {"0": 0.5, "1": 0.5}, "Y": {"0": 0.5, "1": 0.5}, "Z": {"0": 1.0}}
        elif np.allclose(state, one):
            probs = {"X": {"0": 0.5, "1": 0.5}, "Y": {"0": 0.5, "1": 0.5}, "Z": {"1": 1.0}}
        else:
            assert np.allclose(state, plus)
            probs = {"X": {"0": 1.0}, "Y": {"0": 0.5, "1": 0.5}, "Z": {"0": 0.5, "1": 0.5}}
        return {bitstring: int(round(probability * 64)) for bitstring, probability in probs[basis].items()}

    monkeypatch.setattr(teleportdim, "select_backend", fake_select_backend)
    monkeypatch.setattr(teleportdim, "validate_backend_for_experiment", fake_validate_backend_for_experiment)
    monkeypatch.setattr(teleportdim, "build_block_teleportation_circuit", fake_build_block_teleportation_circuit)
    monkeypatch.setattr(teleportdim, "append_output_measurements", fake_append_output_measurements)
    monkeypatch.setattr(teleportdim, "transpile_isa", fake_transpile_isa)
    monkeypatch.setattr(teleportdim, "run_sampler_job", fake_run_sampler_job)
    monkeypatch.setattr(teleportdim, "extract_register_counts", fake_extract_register_counts)

    configs = fixed_n_sweep_configs([1], delay_dt_values=[0], state_family="computational")
    records = run_hardware_fixed_n_sweep(
        configs,
        teleportdim.BackendConfig(backend_name="fake_backend", shots=64),
        bootstrap_samples=8,
    )

    assert len(records) == 1
    record = records[0]
    assert record["simulation_lane"] == "ibm_runtime"
    assert record["state_family"] == "canonical_probe_average"
    assert record["probe_ensemble_size"] == 3.0
    assert record["dt_ns"] == pytest.approx(0.0)
    assert record["fidelity"] > 0.9
    assert record["fidelity_ci_low"] <= record["fidelity"] <= record["fidelity_ci_high"]


def test_run_hardware_process_tomography_returns_high_process_fidelity(monkeypatch: Any) -> None:
    class FakeTarget:
        dt = 4e-9
        operation_names = {"if_else", "delay"}

    class FakeBackend:
        name = "fake_backend"
        num_qubits = 16
        target = FakeTarget()

    backend = FakeBackend()
    zero = np.array([1.0, 0.0], dtype=complex)
    one = np.array([0.0, 1.0], dtype=complex)
    plus = np.array([1.0, 1.0], dtype=complex) / np.sqrt(2.0)
    plus_i = np.array([1.0, 1.0j], dtype=complex) / np.sqrt(2.0)

    def fake_select_backend(_config: Any) -> Any:
        return backend

    def fake_validate_backend_for_experiment(_backend: Any, **_kwargs: Any) -> Any:
        return None

    def fake_build_block_teleportation_circuit(
        logical_state: Any,
        dimension: Any,
        *,
        n_physical: Any,
        delay_after_entanglement_dt: Any,
        correction_mode: Any,
    ) -> Any:
        return {
            "state": np.asarray(logical_state, dtype=complex),
            "dimension": dimension,
            "n_physical": n_physical,
            "delay_dt": delay_after_entanglement_dt,
            "correction_mode": correction_mode,
        }

    def fake_append_output_measurements(program: Any, basis: Any) -> Any:
        return {"state": program["state"], "basis": basis}

    def fake_transpile_isa(circuits: Any, backend: Any, optimization_level: Any) -> Any:
        assert backend is not None
        assert optimization_level == 1
        return list(circuits)

    def fake_run_sampler_job(circuits: Any, backend: Any, shots: Any, use_session: Any) -> Any:
        assert backend is not None
        assert shots == 64
        assert use_session is False
        return list(circuits)

    def fake_extract_register_counts(pub_result: Any, register_name: Any) -> Any:
        assert register_name.startswith("out_")
        state = pub_result["state"]
        basis = pub_result["basis"]
        if np.allclose(state, zero):
            probs = {"X": {"0": 0.5, "1": 0.5}, "Y": {"0": 0.5, "1": 0.5}, "Z": {"0": 1.0}}
        elif np.allclose(state, one):
            probs = {"X": {"0": 0.5, "1": 0.5}, "Y": {"0": 0.5, "1": 0.5}, "Z": {"1": 1.0}}
        elif np.allclose(state, plus):
            probs = {"X": {"0": 1.0}, "Y": {"0": 0.5, "1": 0.5}, "Z": {"0": 0.5, "1": 0.5}}
        else:
            assert np.allclose(state, plus_i)
            probs = {"X": {"0": 0.5, "1": 0.5}, "Y": {"0": 1.0}, "Z": {"0": 0.5, "1": 0.5}}
        return {bitstring: int(round(probability * 64)) for bitstring, probability in probs[basis].items()}

    monkeypatch.setattr(teleportdim, "select_backend", fake_select_backend)
    monkeypatch.setattr(teleportdim, "validate_backend_for_experiment", fake_validate_backend_for_experiment)
    monkeypatch.setattr(teleportdim, "build_block_teleportation_circuit", fake_build_block_teleportation_circuit)
    monkeypatch.setattr(teleportdim, "append_output_measurements", fake_append_output_measurements)
    monkeypatch.setattr(teleportdim, "transpile_isa", fake_transpile_isa)
    monkeypatch.setattr(teleportdim, "run_sampler_job", fake_run_sampler_job)
    monkeypatch.setattr(teleportdim, "extract_register_counts", fake_extract_register_counts)

    sweep = teleportdim.SweepConfig(dimension=2, delay_dt_values=[0], shots=64, state_family="computational")
    records = run_hardware_process_tomography(
        sweep,
        teleportdim.BackendConfig(backend_name="fake_backend", shots=64),
        bootstrap_samples=8,
    )

    assert len(records) == 1
    record = records[0]
    assert record["simulation_lane"] == "ibm_runtime_process_tomography"
    assert record["dt_ns"] == pytest.approx(0.0)
    assert record["process_fidelity"] >= 0.9
    assert record["average_gate_fidelity"] >= 0.9
    assert record["fidelity_ci_low"] <= record["fidelity"] <= record["fidelity_ci_high"]
    assert record["process_fidelity_ci_low"] <= record["process_fidelity"] <= record["process_fidelity_ci_high"]
