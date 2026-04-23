pytest = __import__("pytest")
pytest.importorskip("qiskit")

import numpy as np

from teleportdim.circuits import append_output_measurements, build_block_teleportation_circuit


def test_block_teleportation_layout_for_qutrit():
    state = np.array([1, 0, 0], dtype=complex)
    program = build_block_teleportation_circuit(state, 3, correction_mode="dynamic")
    assert program.layout.n_physical == 2
    assert len(program.layout.source) == 2
    assert len(program.layout.alice) == 2
    assert len(program.layout.bob) == 2


def test_append_output_measurements_register_added():
    state = np.array([1, 0], dtype=complex)
    program = build_block_teleportation_circuit(state, 2, correction_mode="dynamic")
    qc = append_output_measurements(program, "X")
    assert any(reg.name == "out_X" for reg in qc.cregs)
