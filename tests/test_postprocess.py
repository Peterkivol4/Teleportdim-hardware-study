from teleportdim.postprocess import (
    correct_output_bitstring_for_deferred_frame,
    corrected_counts_from_deferred_shots,
    pauli_frame_flip_for_basis_label,
)


def test_pauli_frame_flip_rules_single_qubit():
    assert pauli_frame_flip_for_basis_label(basis_label="X", z_bit=0, x_bit=0) == 0
    assert pauli_frame_flip_for_basis_label(basis_label="X", z_bit=1, x_bit=0) == 1
    assert pauli_frame_flip_for_basis_label(basis_label="Z", z_bit=0, x_bit=1) == 1
    assert pauli_frame_flip_for_basis_label(basis_label="Y", z_bit=1, x_bit=0) == 1
    assert pauli_frame_flip_for_basis_label(basis_label="Y", z_bit=1, x_bit=1) == 0


def test_correct_output_bitstring_for_deferred_frame_single_qubit():
    # Register strings are written high-to-low by Qiskit; low-to-high bell order is [z0, x0].
    assert correct_output_bitstring_for_deferred_frame("0", "01", "X") == "1"  # z0 = 1
    assert correct_output_bitstring_for_deferred_frame("0", "10", "Z") == "1"  # x0 = 1
    assert correct_output_bitstring_for_deferred_frame("0", "01", "Z") == "0"  # z0 alone does not flip Z
    assert correct_output_bitstring_for_deferred_frame("1", "11", "Y") == "1"  # XZ commutes with Y


def test_corrected_counts_from_deferred_shots_two_qubit_mixed_basis():
    # basis="XZ" means qubit 0 is measured in X and qubit 1 in Z (low-to-high order).
    output_shots = ["00", "00", "00", "00"]
    bell_shots = ["0000", "0001", "1000", "1001"]
    counts = corrected_counts_from_deferred_shots(output_shots, bell_shots, basis="XZ")
    assert sum(counts.values()) == 4
    assert counts == {"00": 1, "01": 1, "10": 1, "11": 1}
