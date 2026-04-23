from __future__ import annotations

from teleportdim.aer import (
    extract_register_shots_from_memory,
    marginalize_combined_counts_for_register,
    run_aer_delay_sweep,
    split_combined_register_string,
)
from teleportdim.config import BackendConfig, SweepConfig


LAYOUT = [("bell", 2), ("out_X", 1)]


def test_split_combined_register_string_preserves_named_groups():
    assert split_combined_register_string('1 10', LAYOUT) == {'bell': '10', 'out_X': '1'}


def test_marginalize_counts_for_one_register():
    counts = {'1 10': 3, '0 01': 2}
    assert marginalize_combined_counts_for_register(counts, LAYOUT, 'out_X') == {'1': 3, '0': 2}


def test_extract_register_shots_from_memory():
    memory = ['1 10', '0 01', '1 00']
    assert extract_register_shots_from_memory(memory, LAYOUT, 'bell') == ['10', '01', '00']


def test_run_aer_delay_sweep_executes_dynamic_and_deferred_paths():
    pytest = __import__("pytest")
    pytest.importorskip("qiskit")
    pytest.importorskip("qiskit_aer")

    records_by_mode = {}
    for correction_mode in ("dynamic", "deferred"):
        sweep = SweepConfig(dimension=2, delay_dt_values=[0], shots=512, state_family="computational")
        backend = BackendConfig(shots=512, correction_mode=correction_mode)
        records = run_aer_delay_sweep(sweep, backend, method="automatic", seed_simulator=23)

        assert len(records) == 1
        record = records[0]
        records_by_mode[correction_mode] = record
        assert record["correction_mode"] == correction_mode
        assert record["simulation_lane"] == "aer"
        assert record["delay_dt"] == 0
        assert 0.0 <= record["fidelity"] <= 1.0
        assert 0.0 <= record["leakage"] <= 1.0
        assert 0.0 <= record["in_subspace_fidelity"] <= 1.0
        assert record["fidelity"] >= 0.9
        assert record["leakage"] <= 0.1

    assert abs(records_by_mode["dynamic"]["fidelity"] - records_by_mode["deferred"]["fidelity"]) <= 0.1


def test_run_aer_delay_sweep_qutrit_haar_probe_stays_high_fidelity():
    pytest = __import__("pytest")
    pytest.importorskip("qiskit")
    pytest.importorskip("qiskit_aer")

    records_by_mode = {}
    for correction_mode in ("dynamic", "deferred"):
        sweep = SweepConfig(dimension=3, delay_dt_values=[0], shots=1024, state_family="haar", random_seed=7)
        backend = BackendConfig(shots=1024, correction_mode=correction_mode)
        record = run_aer_delay_sweep(sweep, backend, method="automatic", seed_simulator=41)[0]
        records_by_mode[correction_mode] = record

        assert record["fidelity"] >= 0.9
        assert record["leakage"] <= 0.1
        assert record["in_subspace_fidelity"] >= 0.9

    assert abs(records_by_mode["dynamic"]["fidelity"] - records_by_mode["deferred"]["fidelity"]) <= 0.1
