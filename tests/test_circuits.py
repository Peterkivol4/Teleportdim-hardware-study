pytest = __import__("pytest")
pytest.importorskip("qiskit")

import numpy as np

from teleportdim.circuits import (
    append_output_measurements,
    build_block_teleportation_circuit,
    theoretical_teleportation_depth,
    theoretical_teleportation_gate_counts,
)


def test_block_teleportation_layout_for_qutrit() -> None:
    state = np.array([1, 0, 0], dtype=complex)
    program = build_block_teleportation_circuit(state.tolist(), 3, correction_mode="dynamic")
    assert program.layout.n_physical == 2
    assert len(program.layout.source) == 2
    assert len(program.layout.alice) == 2
    assert len(program.layout.bob) == 2


def test_append_output_measurements_register_added() -> None:
    state = np.array([1, 0], dtype=complex)
    program = build_block_teleportation_circuit(state.tolist(), 2, correction_mode="dynamic")
    qc = append_output_measurements(program, "X")
    assert any(reg.name == "out_X" for reg in qc.cregs)


def test_block_teleportation_depth_and_gate_counts_match_theory_for_each_dimension() -> None:
    for dimension in (2, 3, 4, 5):
        state = np.zeros(dimension, dtype=complex)
        state[0] = 1.0
        program = build_block_teleportation_circuit(
            state.tolist(),
            dimension,
            correction_mode="dynamic",
            add_barriers=False,
        )
        assert program.circuit.depth() == theoretical_teleportation_depth(
            dimension,
            correction_mode="dynamic",
            include_barriers=False,
        )
        expected_counts = theoretical_teleportation_gate_counts(
            dimension,
            correction_mode="dynamic",
        )
        observed_counts = dict(program.circuit.count_ops())
        for gate_name, expected in expected_counts.items():
            assert observed_counts[gate_name] == expected
