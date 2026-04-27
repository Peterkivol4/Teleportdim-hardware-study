import numpy as np

from teleportdim.encoding import embed_logical_state, fill_ratio, logical_subspace_projector
from teleportdim.metrics import (
    average_gate_fidelity_from_process_fidelity,
    in_subspace_fidelity,
    leakage_probability,
    pure_state_density,
)


def test_fill_ratio_distinguishes_d3_and_d4_on_same_two_qubits() -> None:
    assert np.isclose(fill_ratio(3), 0.75)
    assert np.isclose(fill_ratio(4), 1.0)


def test_leakage_probability_detects_population_outside_codespace() -> None:
    rho = np.zeros((4, 4), dtype=complex)
    rho[3, 3] = 1.0  # |11> leakage state for d=3
    assert np.isclose(leakage_probability(rho, 3), 1.0)
    assert np.isclose(leakage_probability(rho, 4), 0.0)


def test_in_subspace_fidelity_conditions_on_codespace_population() -> None:
    logical = np.array([1.0, 0.0, 0.0], dtype=complex)
    embedded = embed_logical_state(logical, 3)
    rho = 0.5 * pure_state_density(embedded)
    rho[3, 3] += 0.5
    assert np.isclose(in_subspace_fidelity(logical, rho, 3), 1.0)
    assert np.isclose(leakage_probability(rho, 3), 0.5)


def test_average_gate_fidelity_formula() -> None:
    assert np.isclose(average_gate_fidelity_from_process_fidelity(1.0, 3), 1.0)
    assert np.isclose(average_gate_fidelity_from_process_fidelity(0.5, 2), 2 / 3)
