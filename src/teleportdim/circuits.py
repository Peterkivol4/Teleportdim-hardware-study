from __future__ import annotations

from .config import _VALID_CORRECTION_MODES
from .encoding import embed_logical_state, resolved_n_physical

from dataclasses import dataclass
from typing import Any, Sequence

try:  # pragma: no cover - optional import guard
    from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister
    from qiskit.circuit.library import StatePreparation
except ImportError:  # pragma: no cover
    ClassicalRegister = None
    QuantumCircuit = None
    QuantumRegister = None
    StatePreparation = None



class CircuitBuildError(RuntimeError):
    """Raised when the circuit layer is used without Qiskit installed."""


@dataclass(slots=True)
class TeleportationLayout:
    """Physical register layout for one encoded teleportation block.

    Indices are physical qubit indices inside the generated Qiskit circuit. The
    layout uses three ``n``-qubit registers: source, Alice's half of the Bell
    pairs, and Bob's output block.
    """

    n_physical: int
    source: tuple[int, ...]
    alice: tuple[int, ...]
    bob: tuple[int, ...]
    bell_measure_bits: tuple[int, ...]


@dataclass(slots=True)
class TeleportationProgram:
    """Teleportation circuit plus the qubit layout needed by tomography code."""

    circuit: Any
    layout: TeleportationLayout


def _require_qiskit() -> None:
    """Raise a clear installation error when circuit-building is requested without Qiskit."""
    if QuantumCircuit is None or QuantumRegister is None or ClassicalRegister is None or StatePreparation is None:
        raise CircuitBuildError(
            "Qiskit is not installed. Install teleportdim[aer], teleportdim[ibm], or teleportdim[full] to use the circuit layer."
        )


def _add_bell_pair(qc: Any, a: int, b: int) -> None:
    """Prepare one Bell pair between physical qubits ``a`` and ``b``."""
    qc.h(a)
    qc.cx(a, b)


def theoretical_teleportation_gate_counts(
    dimension: int,
    *,
    n_physical: int | None = None,
    correction_mode: str = "dynamic",
    include_state_preparation: bool = True,
) -> dict[str, int]:
    """Return expected high-level operation counts for one teleportation block.

    The counts are dimensionless operation counts, not durations. For ``n`` physical
    qubits per logical register, the block contains ``n`` Bell-pair Hadamards, ``n``
    Bell-measurement Hadamards, ``2n`` CNOTs, and ``2n`` output Bell measurements.
    Dynamic correction adds ``2n`` conditional Pauli-frame operations. The embedded
    state preparation is counted as one high-level Qiskit instruction because backend
    decomposition depends on the target basis.
    """
    n = resolved_n_physical(dimension, n_physical)
    counts = {
        "h": 2 * n,
        "cx": 2 * n,
        "measure": 2 * n,
    }
    if correction_mode == "dynamic":
        counts["if_else"] = 2 * n
    if include_state_preparation:
        counts["state_preparation"] = 1
    return counts


def theoretical_teleportation_depth(
    dimension: int,
    *,
    n_physical: int | None = None,
    correction_mode: str = "dynamic",
    include_barriers: bool = False,
) -> int:
    """Return the expected high-level Qiskit DAG depth for one teleportation block.

    Depth is a dimensionless layer count. With barriers disabled, this implementation
    has six high-level layers: state preparation, Bell-pair creation, Bell-basis CNOT,
    source Hadamard, Bell readout, and optional dynamic correction. The value is
    independent of ``d`` except through validation of the physical embedding.
    """
    resolved_n_physical(dimension, n_physical)
    if correction_mode not in _VALID_CORRECTION_MODES:
        raise ValueError(f"unsupported correction_mode: {correction_mode}")
    return 8 if include_barriers else 6


def prepare_embedded_logical_state(
    qc: Any,
    qubits: Sequence[int],
    logical_state: Sequence[complex],
    dimension: int,
    n_physical: int | None = None,
) -> None:
    """Append embedded logical-state preparation to a source register.

    ``logical_state`` is a dimensionless amplitude vector in the logical
    ``dimension``-dimensional Hilbert space. The prepared state occupies the
    first ``dimension`` computational-basis states of the physical ``n``-qubit
    register.
    """
    _require_qiskit()
    embedded = embed_logical_state(logical_state, dimension, n_physical)
    gate = StatePreparation(embedded)
    qc.append(gate, list(qubits))


def build_block_teleportation_circuit(
    logical_state: Sequence[complex],
    dimension: int,
    *,
    n_physical: int | None = None,
    delay_after_entanglement_dt: int = 0,
    correction_mode: str = "dynamic",
    add_barriers: bool = True,
) -> TeleportationProgram:
    """Build the encoded block-teleportation circuit used by Aer and hardware.

    ``delay_after_entanglement_dt`` is measured in backend ``dt`` ticks. The
    returned circuit contains state preparation, Bell-pair generation, optional
    delay on the entangled channel qubits, Bell-basis measurements, and optional
    dynamic Pauli-frame correction.
    """
    _require_qiskit()
    n = resolved_n_physical(dimension, n_physical)
    q = QuantumRegister(3 * n, "q")
    bell_bits = ClassicalRegister(2 * n, "bell")
    qc = QuantumCircuit(q, bell_bits)

    source = tuple(range(0, n))
    alice = tuple(range(n, 2 * n))
    bob = tuple(range(2 * n, 3 * n))

    prepare_embedded_logical_state(qc, source, logical_state, dimension, n)
    if add_barriers:
        qc.barrier()

    for a, b in zip(alice, bob):
        _add_bell_pair(qc, a, b)

    if delay_after_entanglement_dt > 0:
        for qb in (*alice, *bob):
            qc.delay(delay_after_entanglement_dt, qb, unit="dt")

    if add_barriers:
        qc.barrier()

    for i, (s, a, b) in enumerate(zip(source, alice, bob)):
        qc.cx(s, a)
        qc.h(s)
        qc.measure(s, bell_bits[2 * i])
        qc.measure(a, bell_bits[2 * i + 1])
        if correction_mode == "dynamic":
            with qc.if_test((bell_bits[2 * i + 1], 1)):
                qc.x(b)
            with qc.if_test((bell_bits[2 * i], 1)):
                qc.z(b)

    layout = TeleportationLayout(
        n_physical=n,
        source=source,
        alice=alice,
        bob=bob,
        bell_measure_bits=tuple(range(2 * n)),
    )
    return TeleportationProgram(circuit=qc, layout=layout)


def append_output_measurements(
    program: TeleportationProgram,
    basis: str,
) -> Any:
    """Return a copy of the circuit with output-basis rotations and measurements.

    basis should be a string over the alphabet {X, Y, Z} with length equal to the
    number of physical Bob qubits.
    """
    _require_qiskit()
    qc = program.circuit.copy()
    qc.name = f"teleport_tomo_{basis}"
    if len(basis) != program.layout.n_physical:
        raise ValueError("basis length must match number of physical output qubits")

    out = ClassicalRegister(program.layout.n_physical, f"out_{basis}")
    qc.add_register(out)

    for label, qb in zip(basis, program.layout.bob):
        if label == "X":
            qc.h(qb)
        elif label == "Y":
            qc.sdg(qb)
            qc.h(qb)
        elif label == "Z":
            pass
        else:
            raise ValueError(f"unsupported basis label: {label}")

    qc.measure(list(program.layout.bob), list(out))
    return qc


__all__ = [
    "CircuitBuildError",
    "TeleportationLayout",
    "TeleportationProgram",
    "theoretical_teleportation_gate_counts",
    "theoretical_teleportation_depth",
    "prepare_embedded_logical_state",
    "build_block_teleportation_circuit",
    "append_output_measurements",
]
