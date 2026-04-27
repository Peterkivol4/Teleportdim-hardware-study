from __future__ import annotations


from collections import Counter
from typing import Iterable


class PostprocessError(ValueError):
    """Raised when deferred-frame post-processing inputs are invalid."""


def _register_bits_low_to_high(bitstring: str) -> list[int]:
    """Convert between Qiskit register bit ordering conventions used in post-processing."""
    bits = bitstring.replace(" ", "")
    if any(bit not in {"0", "1"} for bit in bits):
        raise PostprocessError(f"invalid bitstring: {bitstring!r}")
    return [int(bit) for bit in bits[::-1]]


def _register_bits_high_to_low(bits_low_to_high: Iterable[int]) -> str:
    """Convert between Qiskit register bit ordering conventions used in post-processing."""
    bits = list(bits_low_to_high)
    if any(bit not in {0, 1} for bit in bits):
        raise PostprocessError(f"invalid bit list: {bits}")
    return "".join(str(bit) for bit in bits[::-1])


def pauli_frame_flip_for_basis_label(*, basis_label: str, z_bit: int, x_bit: int) -> int:
    """Return whether a measurement bit should be flipped under a deferred Pauli frame.

    Teleportation with Bell-measurement outcomes (z_bit, x_bit) applies the Pauli frame
    X**x_bit Z**z_bit to the output state. A measurement in basis P in {X, Y, Z} can be
    corrected classically by flipping the observed eigenvalue bit whenever the frame anticommutes
    with P.
    """
    if basis_label == "X":
        return int(z_bit)
    if basis_label == "Y":
        return int(x_bit ^ z_bit)
    if basis_label == "Z":
        return int(x_bit)
    raise PostprocessError(f"unsupported basis label: {basis_label}")


def correct_output_bitstring_for_deferred_frame(
    output_bitstring: str,
    bell_bitstring: str,
    basis: str,
) -> str:
    """Apply classical Pauli-frame correction to one output-register bitstring.

    Parameters
    ----------
    output_bitstring:
        Bitstring of the output register in Qiskit's printed register order (high-to-low).
    bell_bitstring:
        Bitstring of the Bell-measurement register in Qiskit's printed register order.
        Low-to-high Bell register indices are arranged as [z0, x0, z1, x1, ...].
    basis:
        Tomography basis label string over {X, Y, Z}, in low-to-high Bob-qubit order.
    """
    out_bits = _register_bits_low_to_high(output_bitstring)
    bell_bits = _register_bits_low_to_high(bell_bitstring)

    if len(out_bits) != len(basis):
        raise PostprocessError(
            "output bitstring length must match number of basis labels; "
            f"got {len(out_bits)} and {len(basis)}"
        )
    if len(bell_bits) != 2 * len(basis):
        raise PostprocessError(
            "bell bitstring length must be twice the output-register size; "
            f"got {len(bell_bits)} and basis length {len(basis)}"
        )

    corrected = out_bits[:]
    for i, label in enumerate(basis):
        z_bit = bell_bits[2 * i]
        x_bit = bell_bits[2 * i + 1]
        corrected[i] ^= pauli_frame_flip_for_basis_label(
            basis_label=label,
            z_bit=z_bit,
            x_bit=x_bit,
        )
    return _register_bits_high_to_low(corrected)


def corrected_counts_from_deferred_shots(
    output_shots: Iterable[str],
    bell_shots: Iterable[str],
    basis: str,
) -> dict[str, int]:
    """Apply deferred Pauli-frame corrections to shot data and return corrected counts."""
    output_list = list(output_shots)
    bell_list = list(bell_shots)
    if len(output_list) != len(bell_list):
        raise PostprocessError(
            "output_shots and bell_shots must have the same number of samples; "
            f"got {len(output_list)} and {len(bell_list)}"
        )

    counts = Counter(
        correct_output_bitstring_for_deferred_frame(out_bits, bell_bits, basis)
        for out_bits, bell_bits in zip(output_list, bell_list)
    )
    return dict(counts)


__all__ = [
    "PostprocessError",
    "pauli_frame_flip_for_basis_label",
    "correct_output_bitstring_for_deferred_frame",
    "corrected_counts_from_deferred_shots",
]
