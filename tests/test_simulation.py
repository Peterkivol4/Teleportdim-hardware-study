import numpy as np
import pytest

from teleportdim.simulation import (
    blp_non_markovianity,
    blp_random_telegraph_non_markovianity,
    calibrate_random_telegraph_from_records,
    correlated_memory_observables,
    estimate_effective_t2_from_records,
    markovian_delay_observables,
    random_telegraph_dephasing_observables,
)
from teleportdim.states import computational_basis_state, fourier_state


def test_markovian_observables_include_leakage_and_subspace_metrics():
    state = computational_basis_state(3, 1)
    obs = markovian_delay_observables(state, 3, delay=20.0, t1=10.0, t2=20.0, t_dep=15.0)
    assert set(obs) == {"fidelity", "leakage", "in_subspace_fidelity"}
    assert 0.0 <= obs["leakage"] <= 1.0
    assert 0.0 <= obs["in_subspace_fidelity"] <= 1.0
    assert obs["leakage"] > 0.0


def test_correlated_memory_observables_can_generate_leakage_under_pauli_memory_model():
    state = computational_basis_state(3, 1)
    obs = correlated_memory_observables(
        state,
        3,
        steps=3,
        base_phase_flip_probability=0.6,
        memory_strength=0.7,
        samples=512,
        seed=11,
    )
    assert len(obs) == 4
    assert any(item["leakage"] > 0.0 for item in obs[1:])


def test_blp_measure_is_small_in_markovian_limit_and_grows_with_memory():
    state_a = computational_basis_state(2, 0)
    state_b = fourier_state(2, 0)
    markov = blp_non_markovianity(
        state_a,
        state_b,
        2,
        steps=6,
        base_phase_flip_probability=0.3,
        memory_strength=0.0,
        samples=4096,
        seed=5,
    )
    memory = blp_non_markovianity(
        state_a,
        state_b,
        2,
        steps=6,
        base_phase_flip_probability=0.3,
        memory_strength=0.85,
        samples=4096,
        seed=5,
    )
    assert markov["blp_measure"] < 0.01
    assert memory["blp_measure"] >= markov["blp_measure"]
    assert len(memory["trace_distances"]) == 7


def test_blp_respects_explicit_n_physical_embedding():
    state_a = computational_basis_state(2, 0)
    state_b = fourier_state(2, 0)
    result = blp_non_markovianity(
        state_a,
        state_b,
        2,
        n_physical=2,
        steps=4,
        base_phase_flip_probability=0.2,
        memory_strength=0.5,
        samples=1024,
        seed=9,
    )
    assert len(result["trace_distances"]) == 5
    assert all(distance >= 0.0 for distance in result["trace_distances"])


def test_random_telegraph_dephasing_is_physical_and_can_show_more_backflow_when_switching_is_slow():
    plus = fourier_state(2, 0)
    minus = fourier_state(2, 1)
    observables = random_telegraph_dephasing_observables(
        plus,
        2,
        steps=6,
        coupling_strength=1.2,
        switching_probability=0.1,
        samples=1024,
        seed=13,
    )
    assert len(observables) == 7
    assert all(0.0 <= item["leakage"] <= 1.0 for item in observables)

    slow = blp_random_telegraph_non_markovianity(
        plus,
        minus,
        2,
        steps=16,
        coupling_strength=1.2,
        switching_probability=0.05,
        samples=2048,
        seed=13,
    )
    fast = blp_random_telegraph_non_markovianity(
        plus,
        minus,
        2,
        steps=16,
        coupling_strength=1.2,
        switching_probability=0.8,
        samples=2048,
        seed=13,
    )
    assert slow["blp_measure"] >= fast["blp_measure"]


def test_random_telegraph_calibration_recovers_effective_t2_and_switch_probability():
    dimension = 2
    n_physical = 1
    floor = 1.0 / (dimension * dimension)
    baseline = 0.9
    true_t2_ns = 100.0
    records = []
    for delay_dt, dt_ns in [(0, 0.0), (1, 50.0), (2, 100.0)]:
        value = floor + (baseline - floor) * np.exp(-dt_ns / true_t2_ns)
        records.append(
            {
                "dimension": dimension,
                "n_physical": n_physical,
                "delay_dt": delay_dt,
                "dt_ns": dt_ns,
                "process_fidelity": float(value),
                "process_fidelity_ci_low": float(max(floor + 1e-6, value - 0.01)),
                "process_fidelity_ci_high": float(min(0.999999, value + 0.01)),
                "backend_name": "synthetic",
                "simulation_lane": "synthetic_decay",
            }
        )

    summary = estimate_effective_t2_from_records(
        records,
        dimension=dimension,
        n_physical=n_physical,
        metric="process_fidelity",
        fit_mode="regression",
    )
    calibration = calibrate_random_telegraph_from_records(
        records,
        dimension=dimension,
        n_physical=n_physical,
        metric="process_fidelity",
        dt_ns_per_step=5.0,
        fit_mode="regression",
    )

    expected_switch_probability = 1.0 - np.exp(-5.0 / true_t2_ns)
    assert summary["effective_t2_ns"] == pytest.approx(true_t2_ns, rel=0.15)
    assert calibration["switching_probability"] == pytest.approx(expected_switch_probability, rel=0.15)
    assert calibration["switching_probability_ci_low"] is not None
    assert calibration["switching_probability_ci_high"] is not None
