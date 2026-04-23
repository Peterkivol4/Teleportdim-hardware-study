"""TeleportDim monolith.

Single-file package for encoded-dimension teleportation experiments on IBM-compatible
qubit hardware, with theory/model, Aer, and hardware orchestration lanes.
"""

import sys
import types
from functools import lru_cache

# === BEGIN config.py ===

from dataclasses import dataclass, field
from typing import Literal, Mapping, Sequence


CorrectionMode = Literal["dynamic", "deferred"]
_VALID_CORRECTION_MODES = {"dynamic", "deferred"}
_VALID_STATE_FAMILIES = {"haar", "computational", "fourier"}
DEFAULT_AER_DT_NS_PER_DT = 0.2222222222222222
DEFAULT_AER_T1_SECONDS = 120e-6
DEFAULT_AER_T2_SECONDS = 80e-6


@dataclass(slots=True)
class BackendConfig:
    """Typed configuration container for backend settings."""
    backend_name: str | None = None
    min_num_qubits: int = 7
    optimization_level: int = 1
    shots: int = 4096
    use_session: bool = False
    enable_dynamic_circuits: bool = True
    correction_mode: CorrectionMode = "dynamic"

    def __post_init__(self) -> None:
        if self.min_num_qubits < 1:
            raise ValueError("min_num_qubits must be >= 1")
        if self.shots < 1:
            raise ValueError("shots must be >= 1")
        if self.correction_mode not in _VALID_CORRECTION_MODES:
            raise ValueError(
                f"unsupported correction_mode: {self.correction_mode}; "
                f"expected one of {sorted(_VALID_CORRECTION_MODES)}"
            )


@dataclass(slots=True)
class SweepConfig:
    """Typed configuration container for sweep settings."""
    dimension: int
    n_physical: int | None = None
    delay_dt_values: Sequence[int] = field(default_factory=lambda: [0, 64, 128, 256])
    shots: int = 4096
    state_family: Literal["haar", "computational", "fourier"] = "haar"
    random_seed: int = 7

    def __post_init__(self) -> None:
        if self.dimension < 2:
            raise ValueError("dimension must be >= 2")
        if self.shots < 1:
            raise ValueError("shots must be >= 1")
        if self.n_physical is not None and self.n_physical < 1:
            raise ValueError("n_physical must be >= 1 when provided")
        if not self.delay_dt_values:
            raise ValueError("delay_dt_values must not be empty")
        if any(int(delay) < 0 for delay in self.delay_dt_values):
            raise ValueError("delay_dt_values must be >= 0")
        if self.state_family not in _VALID_STATE_FAMILIES:
            raise ValueError(
                f"unsupported state_family: {self.state_family}; "
                f"expected one of {sorted(_VALID_STATE_FAMILIES)}"
            )

# === END config.py ===

# === BEGIN encoding.py ===

import math
from typing import Iterable

import numpy as np


class EncodingError(ValueError):
    """Raised when logical-dimension embedding is invalid."""


def num_physical_qubits_for_dimension(dimension: int) -> int:
    """Return the minimum physical qubit count required for a logical dimension."""
    if dimension < 2:
        raise EncodingError("dimension must be at least 2")
    return math.ceil(math.log2(dimension))


def resolved_n_physical(dimension: int, n_physical: int | None = None) -> int:
    """Resolve and validate the physical qubit count used for an encoded logical dimension."""
    minimum = num_physical_qubits_for_dimension(dimension)
    if n_physical is None:
        return minimum
    if n_physical < minimum:
        raise EncodingError(
            f"n_physical={n_physical} is too small for dimension={dimension}; need at least {minimum}"
        )
    return int(n_physical)


def physical_hilbert_dimension_for_logical_dimension(
    dimension: int, n_physical: int | None = None
) -> int:
    """Return the physical Hilbert-space size associated with the chosen embedding."""
    return 2 ** resolved_n_physical(dimension, n_physical)


def fill_ratio(dimension: int, n_physical: int | None = None) -> float:
    """Compute the logical-to-physical Hilbert-space fill ratio for an embedding."""
    return float(dimension / physical_hilbert_dimension_for_logical_dimension(dimension, n_physical))


def dt_seconds_to_ns(dt_seconds: float | None) -> float | None:
    """Convert one backend ``dt`` tick from seconds to nanoseconds."""
    if dt_seconds is None:
        return None
    return float(dt_seconds) * 1e9


def delay_dt_to_ns(
    delay_dt: int | float,
    *,
    dt_seconds: float | None = None,
    dt_ns_per_dt: float | None = None,
) -> float | None:
    """Convert a delay expressed in backend ``dt`` units into nanoseconds when calibrated."""
    scale_ns = float(dt_ns_per_dt) if dt_ns_per_dt is not None else dt_seconds_to_ns(dt_seconds)
    if scale_ns is None:
        return None
    return float(delay_dt) * scale_ns


def resolved_aer_dt_ns_per_dt(dt_ns_per_dt: float | None = None) -> float:
    """Return the Aer-lane ``dt`` calibration used for labels and delay relaxation."""
    if dt_ns_per_dt is None:
        return float(DEFAULT_AER_DT_NS_PER_DT)
    return float(dt_ns_per_dt)


def logical_basis_indices(dimension: int, n_physical: int | None = None) -> np.ndarray:
    """Return the computational-basis indices occupied by the logical codespace.

    The embedding always uses the first ``dimension`` computational basis states.
    ``n_physical`` therefore serves as an explicit embedding-size validation knob rather
    than changing which basis states are selected. Passing an invalid ``n_physical``
    raises immediately instead of silently falling back to the minimal encoding.
    """
    physical_dim = physical_hilbert_dimension_for_logical_dimension(dimension, n_physical)
    indices = np.arange(dimension, dtype=int)
    if indices[-1] >= physical_dim:
        raise EncodingError(
            f"logical basis for dimension={dimension} exceeds physical Hilbert dimension {physical_dim}"
        )
    return indices


def logical_subspace_projector(dimension: int, n_physical: int | None = None) -> np.ndarray:
    """Logical subspace projector for encoded logical-state analysis."""
    physical_dim = physical_hilbert_dimension_for_logical_dimension(dimension, n_physical)
    projector = np.zeros((physical_dim, physical_dim), dtype=complex)
    projector[:dimension, :dimension] = np.eye(dimension, dtype=complex)
    return projector


def normalize_logical_state(state: Iterable[complex], dimension: int) -> np.ndarray:
    """Normalize logical state for encoded logical-state analysis."""
    vec = np.asarray(list(state), dtype=complex)
    if vec.ndim != 1:
        raise EncodingError("state must be a 1D vector")
    if len(vec) != dimension:
        raise EncodingError(f"expected logical state of length {dimension}, got {len(vec)}")
    norm = np.linalg.norm(vec)
    if np.isclose(norm, 0.0):
        raise EncodingError("state must have non-zero norm")
    return vec / norm


def embed_logical_state(
    state: Iterable[complex], dimension: int, n_physical: int | None = None
) -> np.ndarray:
    """Embed a logical state into the first ``dimension`` basis states of a qubit register.

    Parameters
    ----------
    state:
        Logical state amplitudes living in a ``dimension``-dimensional Hilbert space.
    dimension:
        Logical Hilbert-space dimension of the encoded information.
    n_physical:
        Optional explicit physical qubit count. When omitted, the minimal qubit count
        ``ceil(log2(dimension))`` is used. When provided, it must be large enough to host
        the logical space and defines the ambient physical Hilbert space size ``2**n``.
    """
    logical = normalize_logical_state(state, dimension)
    physical_dim = physical_hilbert_dimension_for_logical_dimension(dimension, n_physical)
    embedded = np.zeros(physical_dim, dtype=complex)
    embedded[:dimension] = logical
    return embedded


def extract_logical_density_subspace(
    rho: np.ndarray, dimension: int, n_physical: int | None = None
) -> np.ndarray:
    """Extract logical density subspace for encoded logical-state analysis."""
    rho = np.asarray(rho, dtype=complex)
    expected = physical_hilbert_dimension_for_logical_dimension(dimension, n_physical)
    if rho.shape != (expected, expected):
        raise EncodingError(
            f"expected density matrix shape {(expected, expected)}, got {rho.shape}"
        )
    return rho[:dimension, :dimension]

# === END encoding.py ===

# === BEGIN states.py ===

import numpy as np


def random_haar_state(dimension: int, seed: int | None = None) -> np.ndarray:
    """Construct random haar state for simulation, tomography, or benchmarking."""
    rng = np.random.default_rng(seed)
    real = rng.normal(size=dimension)
    imag = rng.normal(size=dimension)
    vec = real + 1j * imag
    return vec / np.linalg.norm(vec)


def computational_basis_state(dimension: int, index: int) -> np.ndarray:
    """Construct computational basis state for simulation, tomography, or benchmarking."""
    if index < 0 or index >= dimension:
        raise ValueError("basis index out of range")
    vec = np.zeros(dimension, dtype=complex)
    vec[index] = 1.0
    return vec


def fourier_state(dimension: int, k: int = 0) -> np.ndarray:
    """Construct fourier state for simulation, tomography, or benchmarking."""
    n = np.arange(dimension)
    omega = np.exp(2j * np.pi / dimension)
    vec = omega ** (k * n)
    return vec / np.linalg.norm(vec)


def canonical_probe_states(dimension: int) -> list[np.ndarray]:
    """Construct canonical probe states for simulation, tomography, or benchmarking."""
    return [computational_basis_state(dimension, idx) for idx in range(dimension)] + [fourier_state(dimension, 0)]

# === END states.py ===

# === BEGIN metrics.py ===

import numpy as np



def counts_to_probabilities(counts: dict[str, int]) -> dict[str, float]:
    """Normalize raw shot counts into outcome probabilities.

    Parameters
    ----------
    counts:
        Mapping from measured computational-basis bitstrings to shot counts for one
        tomography or readout setting.

    Returns
    -------
    dict[str, float]
        A probability distribution over the same bitstrings, normalized by the total
        number of shots in ``counts``.
    """
    total = sum(counts.values())
    if total <= 0:
        raise ValueError("counts must contain at least one shot")
    return {bitstring: value / total for bitstring, value in counts.items()}


def expectation_from_counts(counts: dict[str, int]) -> float:
    """Estimate a Z-parity expectation value from measured bitstring counts.

    Each bitstring is assigned eigenvalue ``+1`` for even parity and ``-1`` for odd
    parity, which matches the Pauli-string expectation values used by the tomography
    reconstruction helpers in this module.
    """
    total = sum(counts.values())
    if total <= 0:
        raise ValueError("counts must contain at least one shot")
    acc = 0.0
    for bitstring, c in counts.items():
        parity = sum(int(bit) for bit in bitstring) % 2
        acc += (1.0 if parity == 0 else -1.0) * c
    return acc / total


def pure_state_density(psi: np.ndarray) -> np.ndarray:
    """Construct the density matrix ``|psi><psi|`` for a normalized statevector ``psi``."""
    psi = np.asarray(psi, dtype=complex)
    return np.outer(psi, psi.conj())


def pure_state_fidelity(psi: np.ndarray, rho: np.ndarray) -> float:
    """Compute the fidelity between a pure target state and a density matrix.

    Parameters
    ----------
    psi:
        Logical or embedded target statevector.
    rho:
        Density matrix reconstructed from tomography or produced by one of the noise
        models in this package. ``rho`` must act on the same Hilbert space as ``psi``.
    """
    psi = np.asarray(psi, dtype=complex)
    rho = np.asarray(rho, dtype=complex)
    value = np.vdot(psi, rho @ psi)
    return float(np.real_if_close(value))


def leakage_probability(rho: np.ndarray, dimension: int, n_physical: int | None = None) -> float:
    """Return the population that has left the encoded logical subspace.

    Parameters
    ----------
    rho:
        Density matrix on the full ``2**n_physical`` Hilbert space.
    dimension:
        Logical Hilbert-space dimension ``d`` of the encoded subspace.
    n_physical:
        Physical qubit count ``n`` used for the embedding. When omitted, the minimal
        embedding that can represent ``dimension`` is used.

    Returns
    -------
    float
        Probability mass found outside the first ``dimension`` logical basis states of
        the embedding. This is the quantity reported as leakage in the thesis figures.
    """
    rho = np.asarray(rho, dtype=complex)
    projector = logical_subspace_projector(dimension, n_physical)
    if rho.shape != projector.shape:
        expected = projector.shape
        raise ValueError(f"expected density matrix shape {expected}, got {rho.shape}")
    population_in_codespace = np.trace(projector @ rho)
    leakage = 1.0 - float(np.real_if_close(population_in_codespace))
    return float(np.clip(leakage, 0.0, 1.0))


def logical_subspace_population(rho: np.ndarray, dimension: int, n_physical: int | None = None) -> float:
    """Logical subspace population for encoded logical-state analysis."""
    return 1.0 - leakage_probability(rho, dimension, n_physical)


def renormalized_logical_subspace_density(
    rho: np.ndarray, dimension: int, n_physical: int | None = None
) -> np.ndarray:
    """Utility function used by the monolithic teleportation experiment toolkit."""
    subspace = extract_logical_density_subspace(rho, dimension, n_physical)
    trace = np.trace(subspace)
    if np.isclose(trace, 0.0):
        return np.zeros_like(subspace)
    return subspace / trace


def in_subspace_fidelity(
    logical_target: np.ndarray, rho: np.ndarray, dimension: int, n_physical: int | None = None
) -> float:
    """Compute fidelity after renormalizing onto the logical codespace.

    This separates logical damage inside the occupied subspace from population that has
    leaked into unused computational-basis states. ``logical_target`` is expressed in the
    ``dimension``-dimensional logical basis, while ``rho`` lives on the full physical
    Hilbert space.
    """
    logical_target = np.asarray(logical_target, dtype=complex)
    if logical_target.ndim != 1 or logical_target.shape[0] != dimension:
        raise ValueError(
            f"logical_target must be a 1D vector of length {dimension}; "
            f"got shape {logical_target.shape}"
        )
    reduced = renormalized_logical_subspace_density(rho, dimension, n_physical)
    if not np.any(reduced):
        return 0.0
    return pure_state_fidelity(logical_target, reduced)


def physical_and_logical_summary(dimension: int, n_physical: int | None = None) -> dict[str, float | int]:
    """Return the physical Hilbert-space size associated with the chosen embedding."""
    physical_dim = physical_hilbert_dimension_for_logical_dimension(dimension, n_physical)
    return {
        "dimension": dimension,
        "physical_hilbert_dimension": physical_dim,
        "fill_ratio": fill_ratio(dimension, n_physical),
        "leakage_capacity": physical_dim - dimension,
    }


def average_gate_fidelity_from_process_fidelity(process_fidelity: float, dimension: int) -> float:
    """Convert entanglement/process fidelity into average gate fidelity.

    The formula used is ``F_avg = (d * F_process + 1) / (d + 1)`` for a ``d``-dimensional
    logical channel.
    """
    fp = float(process_fidelity)
    d = float(dimension)
    return (d * fp + 1.0) / (d + 1.0)

# === END metrics.py ===

# === BEGIN postprocess.py ===

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

# === END postprocess.py ===

# === BEGIN tomography.py ===

from itertools import product
from typing import Iterable

import numpy as np


_SINGLE_Q_PAULI = {
    "I": np.array([[1, 0], [0, 1]], dtype=complex),
    "X": np.array([[0, 1], [1, 0]], dtype=complex),
    "Y": np.array([[0, -1j], [1j, 0]], dtype=complex),
    "Z": np.array([[1, 0], [0, -1]], dtype=complex),
}


@lru_cache(maxsize=None)
def _all_measurement_bases_cached(n_qubits: int) -> tuple[str, ...]:
    """Return or manipulate  all measurement bases cached used in tomography and simulation."""
    return tuple("".join(labels) for labels in product("XYZ", repeat=n_qubits))


def all_measurement_bases(n_qubits: int) -> list[str]:
    """Return or manipulate all measurement bases used in tomography and simulation."""
    return list(_all_measurement_bases_cached(n_qubits))


@lru_cache(maxsize=None)
def _all_pauli_strings_cached(n_qubits: int) -> tuple[str, ...]:
    """Return or manipulate  all pauli strings cached used in tomography and simulation."""
    return tuple("".join(labels) for labels in product("IXYZ", repeat=n_qubits))


def all_pauli_strings(n_qubits: int) -> list[str]:
    """Return or manipulate all pauli strings used in tomography and simulation."""
    return list(_all_pauli_strings_cached(n_qubits))


@lru_cache(maxsize=None)
def pauli_operator(label: str) -> np.ndarray:
    """Return or manipulate pauli operator used in tomography and simulation."""
    op = np.array([[1]], dtype=complex)
    # Labels are tracked in low-to-high qubit order, while matrix tensor products are
    # conventionally assembled in high-to-low order for the computational basis.
    for char in reversed(label):
        op = np.kron(op, _SINGLE_Q_PAULI[char])
    return op


def _bitstring_expectation(counts: dict[str, int], active_positions: list[int]) -> float:
    """Utility function used by the monolithic teleportation experiment toolkit."""
    total = sum(counts.values())
    if total <= 0:
        raise ValueError("counts must contain at least one shot")
    value = 0.0
    for bitstring, count in counts.items():
        # Qiskit bitstrings print classical bits from high to low index.
        bits = bitstring.replace(" ", "")
        bits = bits[::-1]
        parity = sum(int(bits[pos]) for pos in active_positions) % 2
        value += (1.0 if parity == 0 else -1.0) * count
    return value / total


def compatible_measurement_setting(pauli_label: str) -> str:
    """Return or manipulate compatible measurement setting used in tomography and simulation."""
    return "".join("Z" if char == "I" else char for char in pauli_label)


def project_to_physical_density_matrix(rho: np.ndarray, *, atol: float = 1e-12) -> np.ndarray:
    """Project a reconstructed matrix back onto the physical density-matrix cone."""
    rho = np.asarray(rho, dtype=complex)
    if rho.ndim != 2 or rho.shape[0] != rho.shape[1]:
        raise ValueError("rho must be a square matrix")
    hermitian = 0.5 * (rho + rho.conj().T)
    eigenvalues, eigenvectors = np.linalg.eigh(hermitian)
    clipped = np.clip(np.real_if_close(eigenvalues), 0.0, None)
    total = float(np.sum(clipped))
    if total <= atol:
        return np.eye(rho.shape[0], dtype=complex) / rho.shape[0]
    projected = eigenvectors @ np.diag(clipped / total) @ eigenvectors.conj().T
    projected = 0.5 * (projected + projected.conj().T)
    return projected


def reconstruct_density_matrix(
    setting_counts: dict[str, dict[str, int]], *, project_physical: bool = True
) -> np.ndarray:
    """Reconstruct a density matrix from Pauli-basis tomography counts.

    The reconstruction uses linear inversion over the Pauli basis and, by default, projects
    the estimate back onto the physical density-matrix set (Hermitian, PSD, unit trace).
    This keeps downstream fidelity and leakage calculations meaningful under finite-shot noise.
    """
    if not setting_counts:
        raise ValueError("setting_counts cannot be empty")
    n_qubits = len(next(iter(setting_counts)))
    identity_label = "I" * n_qubits
    expectations: dict[str, float] = {identity_label: 1.0}

    for pauli_label in _all_pauli_strings_cached(n_qubits):
        if pauli_label == identity_label:
            continue
        setting = compatible_measurement_setting(pauli_label)
        counts = setting_counts.get(setting)
        if counts is None:
            raise ValueError(f"missing counts for compatible setting {setting}")
        active_positions = [i for i, char in enumerate(pauli_label) if char != "I"]
        expectations[pauli_label] = _bitstring_expectation(counts, active_positions)

    rho = np.zeros((2**n_qubits, 2**n_qubits), dtype=complex)
    for label, expval in expectations.items():
        rho += expval * pauli_operator(label)
    rho /= 2**n_qubits
    if project_physical:
        rho = project_to_physical_density_matrix(rho)
    return rho

# === END tomography.py ===

# === BEGIN process.py ===

from collections.abc import Sequence

import numpy as np


def process_tomography_probe_states(dimension: int) -> list[np.ndarray]:
    """Return a pure-state probe set that spans the logical density-operator space."""
    if dimension < 2:
        raise ValueError("dimension must be >= 2")

    states = [computational_basis_state(dimension, index) for index in range(dimension)]
    for left in range(dimension):
        for right in range(left + 1, dimension):
            plus = np.zeros(dimension, dtype=complex)
            plus[left] = 1.0
            plus[right] = 1.0
            states.append(normalize_logical_state(plus, dimension))

            plus_i = np.zeros(dimension, dtype=complex)
            plus_i[left] = 1.0
            plus_i[right] = 1.0j
            states.append(normalize_logical_state(plus_i, dimension))
    return states


def vectorize_operator(operator: np.ndarray) -> np.ndarray:
    """Column-stack an operator into Liouville form."""
    op = np.asarray(operator, dtype=complex)
    if op.ndim != 2 or op.shape[0] != op.shape[1]:
        raise ValueError("operator must be a square matrix")
    return op.reshape(-1, order="F")


def apply_superoperator(superoperator: np.ndarray, rho: np.ndarray) -> np.ndarray:
    """Apply a reconstructed superoperator to a density matrix."""
    sop = np.asarray(superoperator, dtype=complex)
    state = np.asarray(rho, dtype=complex)
    if state.ndim != 2 or state.shape[0] != state.shape[1]:
        raise ValueError("rho must be a square matrix")
    d = state.shape[0]
    if sop.shape != (d * d, d * d):
        raise ValueError(f"expected superoperator shape {(d * d, d * d)}, got {sop.shape}")
    return (sop @ vectorize_operator(state)).reshape((d, d), order="F")


def reconstruct_superoperator(
    input_densities: Sequence[np.ndarray],
    output_densities: Sequence[np.ndarray],
) -> np.ndarray:
    """Reconstruct a logical superoperator from input/output density-matrix pairs."""
    if len(input_densities) != len(output_densities):
        raise ValueError("input_densities and output_densities must have the same length")
    if not input_densities:
        raise ValueError("input_densities cannot be empty")

    inputs = [np.asarray(rho, dtype=complex) for rho in input_densities]
    outputs = [np.asarray(rho, dtype=complex) for rho in output_densities]
    dimension = inputs[0].shape[0]
    expected = (dimension, dimension)
    for rho in inputs + outputs:
        if rho.shape != expected:
            raise ValueError(f"all density matrices must have shape {expected}")

    basis_matrix = np.column_stack([vectorize_operator(rho) for rho in inputs])
    if np.linalg.matrix_rank(basis_matrix) < dimension * dimension:
        raise ValueError("input probe states are not informationally complete for process tomography")
    outputs_matrix = np.column_stack([vectorize_operator(rho) for rho in outputs])
    return outputs_matrix @ np.linalg.pinv(basis_matrix)


def choi_matrix_from_superoperator(superoperator: np.ndarray, dimension: int) -> np.ndarray:
    """Convert a Liouville superoperator into its Choi matrix."""
    sop = np.asarray(superoperator, dtype=complex)
    expected = (dimension * dimension, dimension * dimension)
    if sop.shape != expected:
        raise ValueError(f"expected superoperator shape {expected}, got {sop.shape}")

    choi = np.zeros(expected, dtype=complex)
    for row in range(dimension):
        for col in range(dimension):
            basis = np.zeros((dimension, dimension), dtype=complex)
            basis[row, col] = 1.0
            evolved = apply_superoperator(sop, basis)
            choi += np.kron(evolved, basis)
    return choi


def process_fidelity_to_identity(
    superoperator: np.ndarray,
    dimension: int,
    *,
    project_physical: bool = True,
) -> float:
    """Compute the process fidelity of a reconstructed channel against the identity."""
    choi = choi_matrix_from_superoperator(superoperator, dimension) / float(dimension)
    if project_physical:
        choi = project_to_physical_density_matrix(choi)
    maximally_entangled = np.eye(dimension, dtype=complex).reshape(-1, order="F") / np.sqrt(dimension)
    return pure_state_fidelity(maximally_entangled, choi)

# === END process.py ===

# === BEGIN statistics.py ===

from collections.abc import Sequence

import numpy as np


def resample_counts_multinomial(
    counts: dict[str, int],
    *,
    rng: np.random.Generator,
) -> dict[str, int]:
    """Resample a count dictionary with multinomial shot noise."""
    if not counts:
        raise ValueError("counts cannot be empty")
    labels = sorted(counts)
    probabilities = counts_to_probabilities(counts)
    shots = int(sum(counts.values()))
    sampled = rng.multinomial(shots, [probabilities[label] for label in labels])
    return {
        label: int(value)
        for label, value in zip(labels, sampled)
        if int(value) > 0
    }


def _confidence_interval_bounds(values: Sequence[float], confidence_level: float) -> tuple[float, float]:
    """Return a percentile bootstrap confidence interval."""
    if not 0.0 < confidence_level < 1.0:
        raise ValueError("confidence_level must be between 0 and 1")
    if not values:
        raise ValueError("values cannot be empty")
    tail = 0.5 * (1.0 - confidence_level)
    low, high = np.quantile(np.asarray(values, dtype=float), [tail, 1.0 - tail])
    return float(low), float(high)


def bootstrap_tomography_metrics(
    logical_target: np.ndarray,
    dimension: int,
    setting_counts: dict[str, dict[str, int]],
    *,
    n_physical: int | None = None,
    bootstrap_samples: int = 200,
    confidence_level: float = 0.95,
    seed: int | None = None,
) -> dict[str, float]:
    """Bootstrap confidence intervals for fidelity, leakage, and in-subspace fidelity."""
    if bootstrap_samples < 1:
        raise ValueError("bootstrap_samples must be >= 1")

    rng = np.random.default_rng(seed)
    fidelity_values: list[float] = []
    leakage_values: list[float] = []
    in_subspace_values: list[float] = []
    embedded_target = embed_logical_state(logical_target, dimension, n_physical)

    for _ in range(bootstrap_samples):
        resampled_setting_counts = {
            basis: resample_counts_multinomial(counts, rng=rng)
            for basis, counts in setting_counts.items()
        }
        rho = reconstruct_density_matrix(resampled_setting_counts)
        fidelity_values.append(pure_state_fidelity(embedded_target, rho))
        leakage_values.append(leakage_probability(rho, dimension, n_physical))
        in_subspace_values.append(in_subspace_fidelity(logical_target, rho, dimension, n_physical))

    fidelity_ci_low, fidelity_ci_high = _confidence_interval_bounds(fidelity_values, confidence_level)
    leakage_ci_low, leakage_ci_high = _confidence_interval_bounds(leakage_values, confidence_level)
    in_subspace_ci_low, in_subspace_ci_high = _confidence_interval_bounds(in_subspace_values, confidence_level)
    return {
        "confidence_level": float(confidence_level),
        "bootstrap_samples": int(bootstrap_samples),
        "fidelity_bootstrap_mean": float(np.mean(fidelity_values)),
        "leakage_bootstrap_mean": float(np.mean(leakage_values)),
        "in_subspace_fidelity_bootstrap_mean": float(np.mean(in_subspace_values)),
        "fidelity_ci_low": fidelity_ci_low,
        "fidelity_ci_high": fidelity_ci_high,
        "leakage_ci_low": leakage_ci_low,
        "leakage_ci_high": leakage_ci_high,
        "in_subspace_fidelity_ci_low": in_subspace_ci_low,
        "in_subspace_fidelity_ci_high": in_subspace_ci_high,
    }


def bootstrap_average_tomography_metrics(
    logical_targets: Sequence[np.ndarray],
    dimension: int,
    setting_counts_by_target: Sequence[dict[str, dict[str, int]]],
    *,
    n_physical: int | None = None,
    bootstrap_samples: int = 200,
    confidence_level: float = 0.95,
    seed: int | None = None,
) -> dict[str, float]:
    """Bootstrap confidence intervals for canonical-probe averages."""
    if len(logical_targets) != len(setting_counts_by_target):
        raise ValueError("logical_targets and setting_counts_by_target must have the same length")
    if bootstrap_samples < 1:
        raise ValueError("bootstrap_samples must be >= 1")

    rng = np.random.default_rng(seed)
    fidelity_values: list[float] = []
    leakage_values: list[float] = []
    in_subspace_values: list[float] = []

    for _ in range(bootstrap_samples):
        per_probe_fidelity: list[float] = []
        per_probe_leakage: list[float] = []
        per_probe_in_subspace: list[float] = []
        for logical_target, setting_counts in zip(logical_targets, setting_counts_by_target):
            resampled_setting_counts = {
                basis: resample_counts_multinomial(counts, rng=rng)
                for basis, counts in setting_counts.items()
            }
            rho = reconstruct_density_matrix(resampled_setting_counts)
            embedded_target = embed_logical_state(logical_target, dimension, n_physical)
            per_probe_fidelity.append(pure_state_fidelity(embedded_target, rho))
            per_probe_leakage.append(leakage_probability(rho, dimension, n_physical))
            per_probe_in_subspace.append(in_subspace_fidelity(logical_target, rho, dimension, n_physical))
        fidelity_values.append(float(np.mean(per_probe_fidelity)))
        leakage_values.append(float(np.mean(per_probe_leakage)))
        in_subspace_values.append(float(np.mean(per_probe_in_subspace)))

    fidelity_ci_low, fidelity_ci_high = _confidence_interval_bounds(fidelity_values, confidence_level)
    leakage_ci_low, leakage_ci_high = _confidence_interval_bounds(leakage_values, confidence_level)
    in_subspace_ci_low, in_subspace_ci_high = _confidence_interval_bounds(in_subspace_values, confidence_level)
    return {
        "confidence_level": float(confidence_level),
        "bootstrap_samples": int(bootstrap_samples),
        "avg_probe_fidelity_bootstrap_mean": float(np.mean(fidelity_values)),
        "avg_probe_leakage_bootstrap_mean": float(np.mean(leakage_values)),
        "avg_probe_in_subspace_fidelity_bootstrap_mean": float(np.mean(in_subspace_values)),
        "avg_probe_fidelity_ci_low": fidelity_ci_low,
        "avg_probe_fidelity_ci_high": fidelity_ci_high,
        "avg_probe_leakage_ci_low": leakage_ci_low,
        "avg_probe_leakage_ci_high": leakage_ci_high,
        "avg_probe_in_subspace_fidelity_ci_low": in_subspace_ci_low,
        "avg_probe_in_subspace_fidelity_ci_high": in_subspace_ci_high,
    }


def bootstrap_process_tomography_metrics(
    dimension: int,
    input_states: Sequence[np.ndarray],
    setting_counts_by_target: Sequence[dict[str, dict[str, int]]],
    *,
    n_physical: int | None = None,
    bootstrap_samples: int = 200,
    confidence_level: float = 0.95,
    seed: int | None = None,
) -> dict[str, float]:
    """Bootstrap confidence intervals for process and average gate fidelity."""
    if len(input_states) != len(setting_counts_by_target):
        raise ValueError("input_states and setting_counts_by_target must have the same length")
    if bootstrap_samples < 1:
        raise ValueError("bootstrap_samples must be >= 1")

    rng = np.random.default_rng(seed)
    process_values: list[float] = []
    gate_values: list[float] = []

    input_densities = [pure_state_density(state) for state in input_states]
    for _ in range(bootstrap_samples):
        output_densities: list[np.ndarray] = []
        for setting_counts in setting_counts_by_target:
            resampled_setting_counts = {
                basis: resample_counts_multinomial(counts, rng=rng)
                for basis, counts in setting_counts.items()
            }
            rho = reconstruct_density_matrix(resampled_setting_counts)
            output_densities.append(renormalized_logical_subspace_density(rho, dimension, n_physical))
        superoperator = reconstruct_superoperator(input_densities, output_densities)
        process_fidelity = process_fidelity_to_identity(superoperator, dimension)
        process_values.append(process_fidelity)
        gate_values.append(average_gate_fidelity_from_process_fidelity(process_fidelity, dimension))

    process_ci_low, process_ci_high = _confidence_interval_bounds(process_values, confidence_level)
    gate_ci_low, gate_ci_high = _confidence_interval_bounds(gate_values, confidence_level)
    return {
        "confidence_level": float(confidence_level),
        "bootstrap_samples": int(bootstrap_samples),
        "process_fidelity_bootstrap_mean": float(np.mean(process_values)),
        "average_gate_fidelity_bootstrap_mean": float(np.mean(gate_values)),
        "process_fidelity_ci_low": process_ci_low,
        "process_fidelity_ci_high": process_ci_high,
        "average_gate_fidelity_ci_low": gate_ci_low,
        "average_gate_fidelity_ci_high": gate_ci_high,
    }


def bootstrap_probe_mean_observables(
    probe_observables: Sequence[dict[str, float]],
    *,
    bootstrap_samples: int = 200,
    confidence_level: float = 0.95,
    seed: int | None = None,
) -> dict[str, float]:
    """Bootstrap the mean observables of a finite logical probe ensemble."""
    if not probe_observables:
        raise ValueError("probe_observables cannot be empty")
    if bootstrap_samples < 1:
        raise ValueError("bootstrap_samples must be >= 1")

    metrics = ("fidelity", "leakage", "in_subspace_fidelity")
    rng = np.random.default_rng(seed)
    sample_size = len(probe_observables)
    values: dict[str, list[float]] = {metric: [] for metric in metrics}

    for _ in range(bootstrap_samples):
        indices = rng.integers(0, sample_size, size=sample_size)
        for metric in metrics:
            values[metric].append(float(np.mean([probe_observables[index][metric] for index in indices])))

    summary = {
        "confidence_level": float(confidence_level),
        "bootstrap_samples": int(bootstrap_samples),
        "ci_method": "probe_resampling",
    }
    for metric in metrics:
        low, high = _confidence_interval_bounds(values[metric], confidence_level)
        summary[f"{metric}_ci_low"] = low
        summary[f"{metric}_ci_high"] = high
        summary[f"avg_probe_{metric}_ci_low"] = low
        summary[f"avg_probe_{metric}_ci_high"] = high
    return summary

# === END statistics.py ===

# === BEGIN simulation.py ===

from itertools import product

import numpy as np


def _tensor_kraus(single_qubit_ops: list[np.ndarray], n_qubits: int) -> list[np.ndarray]:
    """Build or apply the  tensor kraus used by the effective noise models."""
    ops: list[np.ndarray] = []
    for choices in product(range(len(single_qubit_ops)), repeat=n_qubits):
        op = np.array([[1]], dtype=complex)
        for idx in choices:
            op = np.kron(op, single_qubit_ops[idx])
        ops.append(op)
    return ops


def _apply_kraus(rho: np.ndarray, kraus_ops: list[np.ndarray]) -> np.ndarray:
    """Build or apply the  apply kraus used by the effective noise models."""
    out = np.zeros_like(rho, dtype=complex)
    for op in kraus_ops:
        out += op @ rho @ op.conj().T
    return out


def dephasing_kraus(probability: float) -> list[np.ndarray]:
    """Build or apply the dephasing kraus used by the effective noise models."""
    p = float(np.clip(probability, 0.0, 1.0))
    k0 = np.sqrt(1.0 - p) * np.eye(2, dtype=complex)
    k1 = np.sqrt(p) * np.array([[1, 0], [0, -1]], dtype=complex)
    return [k0, k1]


def amplitude_damping_kraus(gamma: float) -> list[np.ndarray]:
    """Build or apply the amplitude damping kraus used by the effective noise models."""
    g = float(np.clip(gamma, 0.0, 1.0))
    k0 = np.array([[1.0, 0.0], [0.0, np.sqrt(1.0 - g)]], dtype=complex)
    k1 = np.array([[0.0, np.sqrt(g)], [0.0, 0.0]], dtype=complex)
    return [k0, k1]


def depolarizing_kraus(probability: float) -> list[np.ndarray]:
    """Build or apply the depolarizing kraus used by the effective noise models."""
    p = float(np.clip(probability, 0.0, 1.0))
    x = np.array([[0, 1], [1, 0]], dtype=complex)
    y = np.array([[0, -1j], [1j, 0]], dtype=complex)
    z = np.array([[1, 0], [0, -1]], dtype=complex)
    return [
        np.sqrt(1.0 - p) * np.eye(2, dtype=complex),
        np.sqrt(p / 3.0) * x,
        np.sqrt(p / 3.0) * y,
        np.sqrt(p / 3.0) * z,
    ]


def markovian_delay_density(
    logical_state: np.ndarray,
    dimension: int,
    *,
    n_physical: int | None = None,
    delay: float,
    t1: float | None = None,
    t2: float | None = None,
    t_dep: float | None = None,
    depolarizing_probability: float | None = None,
) -> np.ndarray:
    """Phenomenological embedded-state storage model for the output block.

    This is a theory lane only. It is not a full noisy teleportation-circuit simulation.
    Leakage requires a channel that couples the codespace to the unused basis states,
    so this model includes optional depolarizing noise in addition to dephasing and T1 decay.

    Notes
    -----
    ``delay``, ``t1``, ``t2``, and ``t_dep`` must be expressed in the same units. In the
    theory lane they are dimensionless placeholders chosen by the caller. They are **not**
    automatically converted from IBM backend ``dt`` units.
    """
    embedded = embed_logical_state(logical_state, dimension, n_physical)
    rho = pure_state_density(embedded)
    n = resolved_n_physical(dimension, n_physical)

    if t2 is not None and t2 > 0:
        pz = 0.5 * (1.0 - np.exp(-delay / t2))
        rho = _apply_kraus(rho, _tensor_kraus(dephasing_kraus(pz), n))

    if t1 is not None and t1 > 0:
        gamma = 1.0 - np.exp(-delay / t1)
        rho = _apply_kraus(rho, _tensor_kraus(amplitude_damping_kraus(gamma), n))

    if depolarizing_probability is None and t_dep is not None and t_dep > 0:
        depolarizing_probability = 1.0 - np.exp(-delay / t_dep)
    if depolarizing_probability is not None and depolarizing_probability > 0.0:
        rho = _apply_kraus(
            rho,
            _tensor_kraus(depolarizing_kraus(float(depolarizing_probability)), n),
        )

    return rho


def markovian_delay_observables(
    logical_state: np.ndarray,
    dimension: int,
    *,
    n_physical: int | None = None,
    delay: float,
    t1: float | None = None,
    t2: float | None = None,
    t_dep: float | None = None,
    depolarizing_probability: float | None = None,
) -> dict[str, float]:
    """Evaluate the Markovian effective-noise model for a given delay and encoded dimension."""
    embedded = embed_logical_state(logical_state, dimension, n_physical)
    rho = markovian_delay_density(
        logical_state,
        dimension,
        n_physical=n_physical,
        delay=delay,
        t1=t1,
        t2=t2,
        t_dep=t_dep,
        depolarizing_probability=depolarizing_probability,
    )
    return {
        "fidelity": pure_state_fidelity(embedded, rho),
        "leakage": leakage_probability(rho, dimension, n_physical),
        "in_subspace_fidelity": in_subspace_fidelity(logical_state, rho, dimension, n_physical),
    }


def markovian_delay_fidelity(
    logical_state: np.ndarray,
    dimension: int,
    *,
    n_physical: int | None = None,
    delay: float,
    t1: float | None = None,
    t2: float | None = None,
    t_dep: float | None = None,
    depolarizing_probability: float | None = None,
) -> float:
    """Convenience wrapper that returns only the fidelity from the Markovian delay model."""
    return markovian_delay_observables(
        logical_state,
        dimension,
        n_physical=n_physical,
        delay=delay,
        t1=t1,
        t2=t2,
        t_dep=t_dep,
        depolarizing_probability=depolarizing_probability,
    )["fidelity"]


_PAULI_MATRICES = {
    0: np.eye(2, dtype=complex),
    1: np.array([[0, 1], [1, 0]], dtype=complex),
    2: np.array([[0, -1j], [1j, 0]], dtype=complex),
    3: np.array([[1, 0], [0, -1]], dtype=complex),
}


def _apply_local_pauli_to_statevector(state: np.ndarray, qubit: int, n_qubits: int, pauli_idx: int) -> np.ndarray:
    """Apply a single-qubit Pauli to a statevector in O(2**n) time."""
    if pauli_idx == 0:
        return np.asarray(state, dtype=complex).copy()
    if qubit < 0 or qubit >= n_qubits:
        raise ValueError(f"qubit index {qubit} out of range for n_qubits={n_qubits}")
    reshaped = np.asarray(state, dtype=complex).reshape((2,) * n_qubits)
    moved = np.moveaxis(reshaped, qubit, 0)
    transformed = np.empty_like(moved)
    if pauli_idx == 1:  # X
        transformed[0] = moved[1]
        transformed[1] = moved[0]
    elif pauli_idx == 2:  # Y
        transformed[0] = -1j * moved[1]
        transformed[1] = 1j * moved[0]
    elif pauli_idx == 3:  # Z
        transformed[0] = moved[0]
        transformed[1] = -moved[1]
    else:
        raise ValueError(f"unsupported pauli_idx: {pauli_idx}")
    return np.moveaxis(transformed, 0, qubit).reshape(-1)


def _sample_correlated_pauli_histories(
    *,
    n_qubits: int,
    steps: int,
    base_phase_flip_probability: float,
    memory_strength: float,
    samples: int,
    seed: int,
) -> np.ndarray:
    """Sample local Pauli error histories with one-step classical memory.

    The recurrence over time means the process cannot be fully vectorized across the step
    axis, but the expensive sample/qubit draws are batched in NumPy instead of nested
    Python loops.
    """
    rng = np.random.default_rng(seed)
    p = float(np.clip(base_phase_flip_probability, 0.0, 1.0))
    m = float(np.clip(memory_strength, 0.0, 1.0))
    if steps < 1:
        raise ValueError("steps must be >= 1")
    base_probs = np.array([1.0 - p, p / 3.0, p / 3.0, p / 3.0], dtype=float)
    fresh_draws = rng.choice(4, size=(samples, steps, n_qubits), p=base_probs).astype(np.int8)
    histories = np.empty_like(fresh_draws)
    histories[:, 0, :] = fresh_draws[:, 0, :]
    if steps == 1:
        return histories
    reuse_mask = rng.random((samples, steps - 1, n_qubits)) < m
    for step in range(1, steps):
        histories[:, step, :] = np.where(reuse_mask[:, step - 1, :], histories[:, step - 1, :], fresh_draws[:, step, :])
    return histories


def correlated_memory_density_trajectory(
    logical_state: np.ndarray,
    dimension: int,
    *,
    n_physical: int | None = None,
    steps: int,
    base_phase_flip_probability: float,
    memory_strength: float,
    samples: int = 2048,
    seed: int = 7,
    histories: np.ndarray | None = None,
) -> list[np.ndarray]:
    """Monte-Carlo estimate of density matrices under a correlated local Pauli process.

    The hidden process is still phenomenological, but unlike the phase-only model it can
    populate leakage states through X/Y components while preserving a tunable memory knob.
    """
    if steps < 1:
        raise ValueError("steps must be >= 1")
    embedded = embed_logical_state(logical_state, dimension, n_physical)
    n = resolved_n_physical(dimension, n_physical)

    if histories is None:
        histories = _sample_correlated_pauli_histories(
            n_qubits=n,
            steps=steps,
            base_phase_flip_probability=base_phase_flip_probability,
            memory_strength=memory_strength,
            samples=samples,
            seed=seed,
        )
    if histories.shape != (samples, steps, n):
        raise ValueError(
            f"expected histories shape {(samples, steps, n)}, got {histories.shape}"
        )

    accumulators = [np.zeros((2**n, 2**n), dtype=complex) for _ in range(steps + 1)]
    accumulators[0] = pure_state_density(embedded) * samples

    for sample in range(samples):
        state = embedded.copy()
        for step in range(1, steps + 1):
            errors = histories[sample, step - 1, :]
            for q, pauli_idx in enumerate(errors):
                if pauli_idx:
                    state = _apply_local_pauli_to_statevector(state, q, n, int(pauli_idx))
            accumulators[step] += pure_state_density(state)

    return [rho / samples for rho in accumulators]


def correlated_memory_observables(
    logical_state: np.ndarray,
    dimension: int,
    *,
    n_physical: int | None = None,
    steps: int,
    base_phase_flip_probability: float,
    memory_strength: float,
    samples: int = 2048,
    seed: int = 7,
) -> list[dict[str, float]]:
    """Evaluate the correlated-memory effective model used as the non-Markovian lane."""
    embedded = embed_logical_state(logical_state, dimension, n_physical)
    trajectory = correlated_memory_density_trajectory(
        logical_state,
        dimension,
        n_physical=n_physical,
        steps=steps,
        base_phase_flip_probability=base_phase_flip_probability,
        memory_strength=memory_strength,
        samples=samples,
        seed=seed,
    )
    return [
        {
            "step": step,
            "fidelity": pure_state_fidelity(embedded, rho),
            "leakage": leakage_probability(rho, dimension, n_physical),
            "in_subspace_fidelity": in_subspace_fidelity(logical_state, rho, dimension, n_physical),
        }
        for step, rho in enumerate(trajectory)
    ]


def correlated_memory_fidelity(
    logical_state: np.ndarray,
    dimension: int,
    *,
    n_physical: int | None = None,
    steps: int,
    base_phase_flip_probability: float,
    memory_strength: float,
    samples: int = 2048,
    seed: int = 7,
) -> float:
    """Convenience wrapper that returns only the fidelity from the correlated-memory lane."""
    return correlated_memory_observables(
        logical_state,
        dimension,
        n_physical=n_physical,
        steps=steps,
        base_phase_flip_probability=base_phase_flip_probability,
        memory_strength=memory_strength,
        samples=samples,
        seed=seed,
    )[-1]["fidelity"]


def _apply_local_z_rotation(state: np.ndarray, qubit: int, n_qubits: int, angle: float) -> np.ndarray:
    """Apply a single-qubit Z rotation to a statevector in O(2**n) time."""
    if qubit < 0 or qubit >= n_qubits:
        raise ValueError(f"qubit index {qubit} out of range for n_qubits={n_qubits}")
    phase_zero = np.exp(-0.5j * angle)
    phase_one = np.exp(0.5j * angle)
    reshaped = np.asarray(state, dtype=complex).reshape((2,) * n_qubits)
    moved = np.moveaxis(reshaped, qubit, 0).copy()
    moved[0] *= phase_zero
    moved[1] *= phase_one
    return np.moveaxis(moved, 0, qubit).reshape(-1)


def _sample_random_telegraph_histories(
    *,
    n_qubits: int,
    steps: int,
    switching_probability: float,
    samples: int,
    seed: int,
) -> np.ndarray:
    """Sample local random-telegraph noise histories for physically motivated dephasing."""
    if steps < 1:
        raise ValueError("steps must be >= 1")
    rng = np.random.default_rng(seed)
    switch_probability = float(np.clip(switching_probability, 0.0, 1.0))
    histories = np.empty((samples, steps, n_qubits), dtype=np.int8)
    histories[:, 0, :] = rng.choice([-1, 1], size=(samples, n_qubits))
    if steps == 1:
        return histories
    switches = rng.random((samples, steps - 1, n_qubits)) < switch_probability
    for step in range(1, steps):
        histories[:, step, :] = histories[:, step - 1, :]
        histories[:, step, :][switches[:, step - 1, :]] *= -1
    return histories


def switching_probability_to_correlation_time(
    switching_probability: float,
    *,
    dt: float = 1.0,
) -> float | None:
    """Map a telegraph switching probability to an exponential correlation time.

    The exact discrete-time relation is ``p_switch = 1 - exp(-dt / tau_corr)``. For
    small probabilities this reduces to the rule-of-thumb used in the README:
    ``p_switch ≈ dt / tau_corr``.
    """
    probability = float(switching_probability)
    if probability <= 0.0:
        return None
    if probability >= 1.0:
        return 0.0
    return float(-float(dt) / np.log(1.0 - probability))


def correlation_time_to_switching_probability(
    correlation_time: float,
    *,
    dt: float = 1.0,
) -> float:
    """Map a telegraph correlation time to the per-step switching probability."""
    tau_corr = float(correlation_time)
    if tau_corr <= 0.0:
        raise ValueError("correlation_time must be > 0")
    return float(1.0 - np.exp(-float(dt) / tau_corr))


def _random_telegraph_calibration_floor(
    metric: str,
    *,
    dimension: int,
    n_physical: int | None = None,
) -> float:
    """Return the asymptotic floor used when normalizing decay-based calibration metrics."""
    if metric == "process_fidelity":
        return float(1.0 / (dimension * dimension))
    if metric == "average_gate_fidelity":
        return float(1.0 / dimension)
    if metric == "in_subspace_fidelity":
        return float(1.0 / dimension)
    if metric == "fidelity":
        return float(1.0 / physical_hilbert_dimension_for_logical_dimension(dimension, n_physical))
    raise ValueError(
        "unsupported calibration metric; expected one of "
        "{'process_fidelity', 'average_gate_fidelity', 'in_subspace_fidelity', 'fidelity'}"
    )


def _calibration_metric_ci_bounds(
    record: dict[str, object],
    metric: str,
) -> tuple[float, float] | None:
    """Extract confidence-interval bounds for a specific calibration metric."""
    low_key = f"{metric}_ci_low"
    high_key = f"{metric}_ci_high"
    if low_key in record and high_key in record:
        return float(record[low_key]), float(record[high_key])
    return None


def _effective_t2_from_decay_ratios(
    delays_ns: Sequence[float],
    ratios: Sequence[float],
) -> float:
    """Estimate an effective exponential decay constant from normalized decay ratios."""
    if len(delays_ns) != len(ratios):
        raise ValueError("delays_ns and ratios must have the same length")
    if not delays_ns:
        raise ValueError("at least one delay point is required")

    xs: list[float] = []
    ys: list[float] = []
    for delay_ns, ratio in zip(delays_ns, ratios):
        delay_value = float(delay_ns)
        ratio_value = float(ratio)
        if delay_value <= 0.0:
            continue
        if ratio_value <= 0.0 or ratio_value >= 1.0:
            continue
        xs.append(delay_value)
        ys.append(np.log(ratio_value))
    if not xs:
        raise ValueError("no valid decay ratios were available for T2 estimation")

    numerator = float(np.dot(xs, ys))
    denominator = float(np.dot(xs, xs))
    if np.isclose(denominator, 0.0):
        raise ValueError("cannot fit a decay constant from zero-delay data only")
    slope = numerator / denominator
    if slope >= 0.0 or np.isclose(slope, 0.0):
        raise ValueError("decay fit did not produce a negative exponential slope")
    return float(-1.0 / slope)


def estimate_effective_t2_from_records(
    records: Sequence[dict[str, object]],
    *,
    dimension: int,
    n_physical: int | None = None,
    metric: str = "process_fidelity",
    fit_mode: str = "first_nonzero",
) -> dict[str, object]:
    """Estimate an effective coherence-decay time from live or simulated delay records.

    The metric is normalized above a physically motivated asymptotic floor before fitting
    an exponential decay constant. This does not claim the observable is a literal Ramsey
    coherence curve; it provides a backend-anchored effective timescale that can be reused
    to calibrate the random-telegraph switching rate.
    """
    if fit_mode not in {"first_nonzero", "regression"}:
        raise ValueError("fit_mode must be 'first_nonzero' or 'regression'")

    resolved_n = resolved_n_physical(dimension, n_physical)
    filtered = [
        record
        for record in records
        if int(record.get("dimension", -1)) == dimension
        and int(record.get("n_physical", -1)) == resolved_n
        and metric in record
    ]
    if not filtered:
        raise ValueError(
            f"no records found for dimension={dimension}, n_physical={resolved_n}, metric={metric}"
        )

    ordered = sorted(
        filtered,
        key=lambda record: (
            float(record.get("dt_ns", float(record.get("delay_dt", 0)))),
            int(record.get("delay_dt", 0)),
        ),
    )
    baseline = ordered[0]
    baseline_dt_ns = baseline.get("dt_ns")
    if baseline_dt_ns is None:
        raise ValueError("records must include dt_ns to estimate an effective T2")
    baseline_time_ns = float(baseline_dt_ns)
    baseline_value = float(baseline[metric])
    floor = _random_telegraph_calibration_floor(metric, dimension=dimension, n_physical=resolved_n)
    if baseline_value <= floor:
        raise ValueError(
            f"baseline {metric}={baseline_value:.6f} does not sit above the calibration floor {floor:.6f}"
        )

    baseline_bounds = _calibration_metric_ci_bounds(baseline, metric)
    candidate_points: list[dict[str, object]] = []
    for record in ordered[1:]:
        dt_ns = record.get("dt_ns")
        if dt_ns is None:
            continue
        delay_ns = float(dt_ns) - baseline_time_ns
        if delay_ns <= 0.0:
            continue
        value = float(record[metric])
        ratio = float((value - floor) / (baseline_value - floor))
        if ratio <= 0.0 or ratio >= 1.0:
            continue

        point: dict[str, object] = {
            "delay_dt": int(record.get("delay_dt", 0)),
            "delay_ns": delay_ns,
            "metric_value": value,
            "normalized_decay_ratio": ratio,
        }
        point_bounds = _calibration_metric_ci_bounds(record, metric)
        if baseline_bounds is not None and point_bounds is not None:
            denominator_low = baseline_bounds[0] - floor
            denominator_high = baseline_bounds[1] - floor
            numerator_low = point_bounds[0] - floor
            numerator_high = point_bounds[1] - floor
            if denominator_low > 0.0 and denominator_high > 0.0:
                ratio_low = numerator_low / denominator_high
                ratio_high = numerator_high / denominator_low
                if 0.0 < ratio_low < 1.0 and 0.0 < ratio_high < 1.0 and ratio_low <= ratio_high:
                    point["normalized_decay_ratio_ci_low"] = float(ratio_low)
                    point["normalized_decay_ratio_ci_high"] = float(ratio_high)
        candidate_points.append(point)

    if not candidate_points:
        raise ValueError("no positive-delay records produced a usable decay ratio")

    selected_points = (
        [candidate_points[0]] if fit_mode == "first_nonzero" else list(candidate_points)
    )
    delays_ns = [float(point["delay_ns"]) for point in selected_points]
    ratios = [float(point["normalized_decay_ratio"]) for point in selected_points]
    effective_t2_ns = _effective_t2_from_decay_ratios(delays_ns, ratios)

    t2_ci_low = None
    t2_ci_high = None
    if all(
        "normalized_decay_ratio_ci_low" in point and "normalized_decay_ratio_ci_high" in point
        for point in selected_points
    ):
        ratio_lows = [float(point["normalized_decay_ratio_ci_low"]) for point in selected_points]
        ratio_highs = [float(point["normalized_decay_ratio_ci_high"]) for point in selected_points]
        t2_ci_low = _effective_t2_from_decay_ratios(delays_ns, ratio_lows)
        t2_ci_high = _effective_t2_from_decay_ratios(delays_ns, ratio_highs)

    return {
        "dimension": dimension,
        "n_physical": resolved_n,
        "metric": metric,
        "fit_mode": fit_mode,
        "source_backend_name": baseline.get("backend_name"),
        "source_simulation_lane": baseline.get("simulation_lane"),
        "baseline_metric_value": baseline_value,
        "calibration_floor": floor,
        "baseline_dt_ns": baseline_time_ns,
        "effective_t2_ns": effective_t2_ns,
        "effective_t2_ns_ci_low": t2_ci_low,
        "effective_t2_ns_ci_high": t2_ci_high,
        "selected_points": selected_points,
    }


def calibrate_random_telegraph_from_records(
    records: Sequence[dict[str, object]],
    *,
    dimension: int,
    n_physical: int | None = None,
    metric: str = "process_fidelity",
    dt_ns_per_step: float,
    fit_mode: str = "first_nonzero",
) -> dict[str, object]:
    """Calibrate a random-telegraph switching probability from backend delay data.

    The calibration uses an effective decay constant inferred from measured delay-dependent
    observables, then sets ``tau_corr := T2_eff`` as a phenomenological matching rule. This
    is intentionally modest: it anchors the telegraph switching rate to a measured timescale
    instead of a hand-picked value without claiming a microscopic fluctuator fit.
    """
    summary = estimate_effective_t2_from_records(
        records,
        dimension=dimension,
        n_physical=n_physical,
        metric=metric,
        fit_mode=fit_mode,
    )
    dt_step = float(dt_ns_per_step)
    if dt_step <= 0.0:
        raise ValueError("dt_ns_per_step must be > 0")

    effective_t2_ns = float(summary["effective_t2_ns"])
    switching_probability = correlation_time_to_switching_probability(
        effective_t2_ns,
        dt=dt_step,
    )

    switching_probability_ci_low = None
    switching_probability_ci_high = None
    t2_ci_low = summary.get("effective_t2_ns_ci_low")
    t2_ci_high = summary.get("effective_t2_ns_ci_high")
    if t2_ci_low is not None and t2_ci_high is not None:
        switching_probability_ci_low = correlation_time_to_switching_probability(
            float(t2_ci_high),
            dt=dt_step,
        )
        switching_probability_ci_high = correlation_time_to_switching_probability(
            float(t2_ci_low),
            dt=dt_step,
        )

    return {
        **summary,
        "dt_ns_per_step": dt_step,
        "correlation_time_ns": effective_t2_ns,
        "correlation_time_ns_ci_low": t2_ci_low,
        "correlation_time_ns_ci_high": t2_ci_high,
        "switching_probability": switching_probability,
        "switching_probability_ci_low": switching_probability_ci_low,
        "switching_probability_ci_high": switching_probability_ci_high,
        "calibration_assumption": "tau_corr := fitted effective T2 from delay data",
        "calibration_formula": "p_switch = 1 - exp(-dt_step / tau_corr)",
    }


def random_telegraph_dephasing_density_trajectory(
    logical_state: np.ndarray,
    dimension: int,
    *,
    n_physical: int | None = None,
    steps: int,
    coupling_strength: float,
    switching_probability: float,
    dt: float = 1.0,
    samples: int = 2048,
    seed: int = 7,
    histories: np.ndarray | None = None,
) -> list[np.ndarray]:
    """Monte-Carlo estimate of density matrices under random-telegraph dephasing.

    This model is motivated by slowly switching fluctuators / low-frequency flux noise:
    each qubit sees a stochastic detuning that flips sign with some switching probability,
    and coherent Z rotations accumulate between switches.
    """
    if steps < 1:
        raise ValueError("steps must be >= 1")
    embedded = embed_logical_state(logical_state, dimension, n_physical)
    n = resolved_n_physical(dimension, n_physical)
    if histories is None:
        histories = _sample_random_telegraph_histories(
            n_qubits=n,
            steps=steps,
            switching_probability=switching_probability,
            samples=samples,
            seed=seed,
        )
    if histories.shape != (samples, steps, n):
        raise ValueError(f"expected histories shape {(samples, steps, n)}, got {histories.shape}")

    accumulators = [np.zeros((2**n, 2**n), dtype=complex) for _ in range(steps + 1)]
    accumulators[0] = pure_state_density(embedded) * samples
    angle_scale = float(coupling_strength) * float(dt)
    for sample in range(samples):
        state = embedded.copy()
        for step in range(1, steps + 1):
            for qubit, sign in enumerate(histories[sample, step - 1, :]):
                state = _apply_local_z_rotation(state, qubit, n, angle_scale * float(sign))
            accumulators[step] += pure_state_density(state)
    return [rho / samples for rho in accumulators]


def random_telegraph_dephasing_observables(
    logical_state: np.ndarray,
    dimension: int,
    *,
    n_physical: int | None = None,
    steps: int,
    coupling_strength: float,
    switching_probability: float,
    dt: float = 1.0,
    samples: int = 2048,
    seed: int = 7,
) -> list[dict[str, float]]:
    """Evaluate a physically motivated random-telegraph dephasing trajectory."""
    embedded = embed_logical_state(logical_state, dimension, n_physical)
    trajectory = random_telegraph_dephasing_density_trajectory(
        logical_state,
        dimension,
        n_physical=n_physical,
        steps=steps,
        coupling_strength=coupling_strength,
        switching_probability=switching_probability,
        dt=dt,
        samples=samples,
        seed=seed,
    )
    return [
        {
            "step": step,
            "fidelity": pure_state_fidelity(embedded, rho),
            "leakage": leakage_probability(rho, dimension, n_physical),
            "in_subspace_fidelity": in_subspace_fidelity(logical_state, rho, dimension, n_physical),
        }
        for step, rho in enumerate(trajectory)
    ]


def trace_distance(rho: np.ndarray, sigma: np.ndarray) -> float:
    """Return the trace distance between two density matrices."""
    delta = np.asarray(rho, dtype=complex) - np.asarray(sigma, dtype=complex)
    singular_values = np.linalg.svd(delta, compute_uv=False)
    return 0.5 * float(np.sum(np.abs(singular_values)))


def _blp_from_density_trajectories(traj_a: Sequence[np.ndarray], traj_b: Sequence[np.ndarray]) -> dict[str, object]:
    """Compute the BLP distinguishability-backflow summary from paired trajectories."""
    distances = [trace_distance(rho_a, rho_b) for rho_a, rho_b in zip(traj_a, traj_b)]
    increments = [distances[i + 1] - distances[i] for i in range(len(distances) - 1)]
    positive_flow = [max(delta, 0.0) for delta in increments]
    return {
        "blp_measure": float(sum(positive_flow)),
        "trace_distances": distances,
        "increments": increments,
        "positive_increments": positive_flow,
    }


def blp_non_markovianity(
    state_a: np.ndarray,
    state_b: np.ndarray,
    dimension: int,
    *,
    n_physical: int | None = None,
    steps: int,
    base_phase_flip_probability: float,
    memory_strength: float,
    samples: int = 2048,
    seed: int = 7,
) -> dict[str, object]:
    """Estimate the BLP distinguishability-backflow measure from paired noisy trajectories."""
    n = resolved_n_physical(dimension, n_physical)
    histories = _sample_correlated_pauli_histories(
        n_qubits=n,
        steps=steps,
        base_phase_flip_probability=base_phase_flip_probability,
        memory_strength=memory_strength,
        samples=samples,
        seed=seed,
    )
    traj_a = correlated_memory_density_trajectory(
        state_a,
        dimension,
        n_physical=n_physical,
        steps=steps,
        base_phase_flip_probability=base_phase_flip_probability,
        memory_strength=memory_strength,
        samples=samples,
        seed=seed,
        histories=histories,
    )
    traj_b = correlated_memory_density_trajectory(
        state_b,
        dimension,
        n_physical=n_physical,
        steps=steps,
        base_phase_flip_probability=base_phase_flip_probability,
        memory_strength=memory_strength,
        samples=samples,
        seed=seed,
        histories=histories,
    )
    return _blp_from_density_trajectories(traj_a, traj_b)


def blp_random_telegraph_non_markovianity(
    state_a: np.ndarray,
    state_b: np.ndarray,
    dimension: int,
    *,
    n_physical: int | None = None,
    steps: int,
    coupling_strength: float,
    switching_probability: float,
    dt: float = 1.0,
    samples: int = 2048,
    seed: int = 7,
) -> dict[str, object]:
    """Estimate BLP non-Markovianity for random-telegraph dephasing."""
    n = resolved_n_physical(dimension, n_physical)
    histories = _sample_random_telegraph_histories(
        n_qubits=n,
        steps=steps,
        switching_probability=switching_probability,
        samples=samples,
        seed=seed,
    )
    traj_a = random_telegraph_dephasing_density_trajectory(
        state_a,
        dimension,
        n_physical=n_physical,
        steps=steps,
        coupling_strength=coupling_strength,
        switching_probability=switching_probability,
        dt=dt,
        samples=samples,
        seed=seed,
        histories=histories,
    )
    traj_b = random_telegraph_dephasing_density_trajectory(
        state_b,
        dimension,
        n_physical=n_physical,
        steps=steps,
        coupling_strength=coupling_strength,
        switching_probability=switching_probability,
        dt=dt,
        samples=samples,
        seed=seed,
        histories=histories,
    )
    return _blp_from_density_trajectories(traj_a, traj_b)


def random_telegraph_blp_probe_pair(dimension: int) -> tuple[np.ndarray, np.ndarray]:
    """Return a dephasing-sensitive logical probe pair for random-telegraph BLP scans.

    The first two Fourier modes distribute phase information across the occupied logical
    subspace. For ``dimension == 2`` this reduces to the familiar ``|+>`` and ``|->`` pair.
    """
    if dimension < 2:
        raise ValueError("dimension must be >= 2 for a two-state BLP probe pair")
    return fourier_state(dimension, 0), fourier_state(dimension, 1)

# === END simulation.py ===

# === BEGIN circuits.py ===

from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np

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
    """Dataclass describing the teleportation layoutused by circuit execution."""
    n_physical: int
    source: tuple[int, ...]
    alice: tuple[int, ...]
    bob: tuple[int, ...]
    bell_measure_bits: tuple[int, ...]


@dataclass(slots=True)
class TeleportationProgram:
    """Dataclass describing the teleportation programused by circuit execution."""
    circuit: Any
    layout: TeleportationLayout


def _require_qiskit() -> None:
    """Raise a clear installation error when circuit-building is requested without Qiskit."""
    if QuantumCircuit is None or QuantumRegister is None or ClassicalRegister is None or StatePreparation is None:
        raise CircuitBuildError(
            "Qiskit is not installed. Install teleportdim[aer], teleportdim[ibm], or teleportdim[full] to use the circuit layer."
        )


def _add_bell_pair(qc: Any, a: int, b: int) -> None:
    """Construct the encoded teleportation circuit components used by hardware and Aer runs."""
    qc.h(a)
    qc.cx(a, b)


def prepare_embedded_logical_state(
    qc: Any,
    qubits: Sequence[int],
    logical_state: Sequence[complex],
    dimension: int,
    n_physical: int | None = None,
) -> None:
    """Construct prepare embedded logical state for simulation, tomography, or benchmarking."""
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
    """Construct the encoded teleportation circuit components used by hardware and Aer runs."""
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

# === END circuits.py ===

# === BEGIN hardware.py ===

from collections.abc import Iterable
from typing import Any

try:
    from qiskit.transpiler import generate_preset_pass_manager
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2, Session
except ImportError:  # pragma: no cover - import guard for non-hardware environments
    generate_preset_pass_manager = None
    QiskitRuntimeService = None
    SamplerV2 = None
    Session = None



class HardwareError(RuntimeError):
    """Raised for runtime/backend orchestration errors."""


def _require_runtime_imports() -> None:
    """Load IBM Runtime dependencies lazily and fail with an actionable error if unavailable."""
    if QiskitRuntimeService is None or SamplerV2 is None or generate_preset_pass_manager is None:
        raise HardwareError(
            "Qiskit Runtime dependencies are not installed. Install qiskit, qiskit-aer, and qiskit-ibm-runtime to use the hardware lane."
        )


def get_service() -> QiskitRuntimeService:
    """Load IBM Runtime dependencies lazily and fail with an actionable error if unavailable."""
    _require_runtime_imports()
    return QiskitRuntimeService()


def backend_operation_names(backend: Any) -> set[str]:
    """Backend or Runtime helper used by IBM hardware execution."""
    target = getattr(backend, "target", None)
    names = getattr(target, "operation_names", None)
    return set(names or [])


def backend_supports_dynamic_circuits(backend: Any) -> bool:
    """Backend or Runtime helper used by IBM hardware execution."""
    names = backend_operation_names(backend)
    return "if_else" in names


def backend_supports_delay(backend: Any) -> bool:
    """Backend or Runtime helper used by IBM hardware execution."""
    names = backend_operation_names(backend)
    return "delay" in names or not names


def backend_dt_seconds(backend: Any) -> float | None:
    """Return the backend ``dt`` duration in seconds when the backend exposes it."""
    target = getattr(backend, "target", None)
    dt_value = getattr(target, "dt", None)
    if dt_value is not None:
        return float(dt_value)

    configuration = getattr(backend, "configuration", None)
    if callable(configuration):
        config = configuration()
        dt_value = getattr(config, "dt", None)
        if dt_value is not None:
            return float(dt_value)
    return None


def validate_backend_for_experiment(
    backend: Any,
    *,
    n_required_qubits: int,
    correction_mode: str,
    require_delay: bool,
) -> None:
    """Backend or Runtime helper used by IBM hardware execution."""
    num_qubits = getattr(backend, "num_qubits", None)
    if num_qubits is not None and num_qubits < n_required_qubits:
        raise HardwareError(
            f"backend {getattr(backend, 'name', '<unknown>')} has {num_qubits} qubits; "
            f"experiment requires at least {n_required_qubits}"
        )

    if correction_mode == "dynamic" and not backend_supports_dynamic_circuits(backend):
        raise HardwareError(
            f"backend {getattr(backend, 'name', '<unknown>')} does not advertise if_else support; "
            "choose correction_mode='deferred' or select a backend with dynamic circuits"
        )

    if require_delay and not backend_supports_delay(backend):
        raise HardwareError(
            f"backend {getattr(backend, 'name', '<unknown>')} does not advertise delay support"
        )


def select_backend(config: BackendConfig):
    """Backend or Runtime helper used by IBM hardware execution."""
    service = get_service()
    if config.backend_name:
        backend = service.backend(config.backend_name)
        validate_backend_for_experiment(
            backend,
            n_required_qubits=config.min_num_qubits,
            correction_mode=config.correction_mode,
            require_delay=False,
        )
        return backend

    dynamic_filter = True if config.correction_mode == "dynamic" else None
    return service.least_busy(
        operational=True,
        simulator=False,
        min_num_qubits=config.min_num_qubits,
        dynamic_circuits=dynamic_filter,
    )


def transpile_isa(circuits: Iterable, backend, optimization_level: int = 1):
    """Backend or Runtime helper used by IBM hardware execution."""
    _require_runtime_imports()
    pm = generate_preset_pass_manager(backend=backend, optimization_level=optimization_level)
    return [pm.run(circuit) for circuit in circuits]


def run_sampler_job(circuits: list, backend, shots: int = 4096, use_session: bool = False):
    """Backend or Runtime helper used by IBM hardware execution."""
    _require_runtime_imports()
    if use_session:
        with Session(backend=backend) as session:
            sampler = SamplerV2(mode=session)
            job = sampler.run(circuits, shots=shots)
            return job.result()
    sampler = SamplerV2(mode=backend)
    job = sampler.run(circuits, shots=shots)
    return job.result()


def _get_register_bitarray(pub_result, register_name: str):
    """Read per-register count or shot data from a primitive result object."""
    data_bin = pub_result.data
    if not hasattr(data_bin, register_name):
        available = [name for name in dir(data_bin) if not name.startswith("_")]
        raise HardwareError(
            f"result register {register_name!r} not found; available entries: {available}"
        )
    return getattr(data_bin, register_name)


def extract_register_counts(pub_result, register_name: str) -> dict[str, int]:
    """Extract register counts for encoded logical-state analysis."""
    bitarray = _get_register_bitarray(pub_result, register_name)
    try:
        return bitarray.get_counts()
    except TypeError:
        return bitarray.get_counts(0)


def extract_register_bitstrings(pub_result, register_name: str) -> list[str]:
    """Extract register bitstrings for encoded logical-state analysis."""
    bitarray = _get_register_bitarray(pub_result, register_name)
    try:
        return list(bitarray.get_bitstrings())
    except TypeError:
        return list(bitarray.get_bitstrings(0))

# === END hardware.py ===

# === BEGIN aer.py ===

from collections import Counter
from collections.abc import Iterable, Sequence
from typing import Any

try:  # pragma: no cover - optional import guard
    from qiskit import transpile
    from qiskit.circuit import Delay
    from qiskit_aer import AerSimulator
    from qiskit_aer.noise import (
        NoiseModel,
        RelaxationNoisePass,
        depolarizing_error,
        thermal_relaxation_error,
    )
except ImportError:  # pragma: no cover
    transpile = None
    Delay = None
    AerSimulator = None
    NoiseModel = None
    RelaxationNoisePass = None
    depolarizing_error = None
    thermal_relaxation_error = None



class AerExecutionError(RuntimeError):
    """Raised when the optional Aer lane cannot execute."""


def _require_aer_imports() -> None:
    """Aer simulation helper for local noisy validation of encoded teleportation circuits."""
    if (
        transpile is None
        or AerSimulator is None
        or NoiseModel is None
        or depolarizing_error is None
        or thermal_relaxation_error is None
    ):
        raise AerExecutionError(
            "Qiskit Aer dependencies are not installed. Install qiskit and qiskit-aer to use the Aer benchmarking lane."
        )


def counts_register_layout_from_circuit(circuit: Any) -> list[tuple[str, int]]:
    """Return the classical-register layout needed to parse combined Qiskit count strings."""
    return [(reg.name, int(reg.size)) for reg in getattr(circuit, "cregs", [])]


def split_combined_register_string(
    bitstring: str,
    register_layout: Sequence[tuple[str, int]],
) -> dict[str, str]:
    """Split a Qiskit-style combined classical string into named register substrings.

    Qiskit renders grouped classical strings from the highest-addressed register chunk
    to the lowest-addressed one, which is the reverse of ``circuit.cregs`` order.
    """
    cleaned = bitstring.strip()
    if not register_layout:
        return {}
    rendered_layout = list(reversed(register_layout))

    chunks = cleaned.split()
    if len(chunks) == len(rendered_layout):
        return {name: chunk for (name, _), chunk in zip(rendered_layout, chunks)}

    flat = cleaned.replace(" ", "")
    expected_width = sum(width for _, width in rendered_layout)
    if len(flat) != expected_width:
        raise AerExecutionError(
            f"could not split combined bitstring {bitstring!r}; expected width {expected_width}"
        )

    result: dict[str, str] = {}
    offset = 0
    for name, width in rendered_layout:
        result[name] = flat[offset : offset + width]
        offset += width
    return result


def marginalize_combined_counts_for_register(
    counts: dict[str, int],
    register_layout: Sequence[tuple[str, int]],
    register_name: str,
) -> dict[str, int]:
    """Aer simulation helper for local noisy validation of encoded teleportation circuits."""
    target = Counter()
    for bitstring, shots in counts.items():
        split = split_combined_register_string(bitstring, register_layout)
        if register_name not in split:
            raise AerExecutionError(f"register {register_name!r} not found in combined counts")
        target[split[register_name]] += int(shots)
    return dict(target)


def extract_register_shots_from_memory(
    memory: Iterable[str],
    register_layout: Sequence[tuple[str, int]],
    register_name: str,
) -> list[str]:
    """Extract register shots from memory for encoded logical-state analysis."""
    shots: list[str] = []
    for bitstring in memory:
        split = split_combined_register_string(bitstring, register_layout)
        if register_name not in split:
            raise AerExecutionError(f"register {register_name!r} not found in memory shot")
        shots.append(split[register_name])
    return shots


def build_basic_noise_model(
    *,
    depolarizing_1q: float = 0.0,
    depolarizing_2q: float = 0.0,
    t1: float | None = None,
    t2: float | None = None,
    single_qubit_gate_time: float = 50e-9,
    two_qubit_gate_time: float = 300e-9,
    measure_time: float = 1e-6,
) -> Any:
    """Aer simulation helper for local noisy validation of encoded teleportation circuits."""
    _require_aer_imports()
    noise_model = NoiseModel()

    if depolarizing_1q > 0.0:
        error_1q = depolarizing_error(float(depolarizing_1q), 1)
        noise_model.add_all_qubit_quantum_error(
            error_1q,
            ["id", "rz", "sx", "x", "z", "h", "sdg"],
        )
    if depolarizing_2q > 0.0:
        error_2q = depolarizing_error(float(depolarizing_2q), 2)
        noise_model.add_all_qubit_quantum_error(error_2q, ["cx", "cz", "ecr"])

    if t1 is not None and t2 is not None:
        t1f = float(t1)
        t2f = float(t2)
        relax_1q = thermal_relaxation_error(t1f, t2f, single_qubit_gate_time)
        relax_meas = thermal_relaxation_error(t1f, t2f, measure_time)
        relax_2q = thermal_relaxation_error(t1f, t2f, two_qubit_gate_time).expand(
            thermal_relaxation_error(t1f, t2f, two_qubit_gate_time)
        )
        noise_model.add_all_qubit_quantum_error(
            relax_1q,
            ["id", "rz", "sx", "x", "z", "h", "sdg"],
        )
        noise_model.add_all_qubit_quantum_error(relax_2q, ["cx", "cz", "ecr"])
        noise_model.add_all_qubit_quantum_error(relax_meas, ["measure"])

    # Store calibration metadata so the Aer execution path can add duration-scaled
    # relaxation specifically on Delay instructions.
    noise_model._teleportdim_t1 = None if t1 is None else float(t1)  # type: ignore[attr-defined]
    noise_model._teleportdim_t2 = None if t2 is None else float(t2)  # type: ignore[attr-defined]
    return noise_model


def make_aer_simulator(
    *,
    method: str = "automatic",
    backend: Any | None = None,
    noise_model: Any | None = None,
) -> Any:
    """Aer simulation helper for local noisy validation of encoded teleportation circuits."""
    _require_aer_imports()
    if backend is not None:
        return AerSimulator.from_backend(backend)
    if noise_model is not None:
        return AerSimulator(method=method, noise_model=noise_model)
    return AerSimulator(method=method)


def _apply_delay_relaxation_pass(
    circuits: Sequence[Any],
    *,
    noise_model: Any | None,
    dt_ns_per_dt: float | None,
) -> list[Any]:
    """Append delay-duration relaxation channels to circuits when T1/T2 are configured."""
    if noise_model is None or RelaxationNoisePass is None or Delay is None:
        return list(circuits)

    t1 = getattr(noise_model, "_teleportdim_t1", None)
    t2 = getattr(noise_model, "_teleportdim_t2", None)
    if t1 is None or t2 is None or float(t1) <= 0.0 or float(t2) <= 0.0:
        return list(circuits)

    resolved_dt_seconds = resolved_aer_dt_ns_per_dt(dt_ns_per_dt) * 1e-9
    noisy_circuits: list[Any] = []
    for circuit in circuits:
        relaxation_pass = RelaxationNoisePass(
            [float(t1)] * circuit.num_qubits,
            [float(t2)] * circuit.num_qubits,
            dt=resolved_dt_seconds,
            op_types=Delay,
        )
        noisy_circuits.append(relaxation_pass(circuit))
    return noisy_circuits


def _run_aer_tomography_for_state(
    logical_state: np.ndarray,
    dimension: int,
    *,
    n_physical: int | None = None,
    delay_dt: int,
    backend_config: BackendConfig,
    simulator: Any,
    noise_model: Any | None,
    seed_simulator: int,
    bootstrap_samples: int = 0,
    confidence_level: float = 0.95,
    dt_ns_per_dt: float | None = None,
    state_family: str = "custom",
) -> tuple[dict[str, Any], dict[str, dict[str, int]], np.ndarray]:
    """Execute a full tomography bundle for one logical input state on Aer."""
    resolved_n = resolved_n_physical(dimension, n_physical)
    resolved_dt_ns = resolved_aer_dt_ns_per_dt(dt_ns_per_dt)
    embedded_target = embed_logical_state(logical_state, dimension, resolved_n)
    bases = all_measurement_bases(resolved_n)

    program = build_block_teleportation_circuit(
        logical_state,
        dimension,
        n_physical=resolved_n,
        delay_after_entanglement_dt=int(delay_dt),
        correction_mode=backend_config.correction_mode,
    )
    tomo_circuits = [append_output_measurements(program, basis) for basis in bases]
    transpiled = transpile(
        tomo_circuits,
        simulator,
        optimization_level=backend_config.optimization_level,
    )
    transpiled = _apply_delay_relaxation_pass(
        transpiled,
        noise_model=noise_model,
        dt_ns_per_dt=resolved_dt_ns,
    )
    job = simulator.run(
        transpiled,
        shots=backend_config.shots,
        memory=(backend_config.correction_mode == "deferred"),
        seed_simulator=seed_simulator,
    )
    result = job.result()

    setting_counts: dict[str, dict[str, int]] = {}
    for index, (basis, circuit) in enumerate(zip(bases, transpiled)):
        combined_counts = result.get_counts(index)
        layout = counts_register_layout_from_circuit(circuit)
        reg_name = f"out_{basis}"
        if backend_config.correction_mode == "dynamic":
            setting_counts[basis] = marginalize_combined_counts_for_register(
                dict(combined_counts),
                layout,
                reg_name,
            )
        else:
            memory = result.get_memory(index)
            output_shots = extract_register_shots_from_memory(memory, layout, reg_name)
            bell_shots = extract_register_shots_from_memory(memory, layout, "bell")
            setting_counts[basis] = corrected_counts_from_deferred_shots(
                output_shots=output_shots,
                bell_shots=bell_shots,
                basis=basis,
            )

    rho = reconstruct_density_matrix(setting_counts)
    record = {
        "dimension": dimension,
        "n_physical": resolved_n,
        "physical_hilbert_dimension": physical_hilbert_dimension_for_logical_dimension(dimension, resolved_n),
        "fill_ratio": fill_ratio(dimension, resolved_n),
        "delay_dt": int(delay_dt),
        "dt_ns": delay_dt_to_ns(delay_dt, dt_ns_per_dt=resolved_dt_ns),
        "backend_name": getattr(simulator, "name", type(simulator).__name__),
        "fidelity": pure_state_fidelity(embedded_target, rho),
        "leakage": leakage_probability(rho, dimension, resolved_n),
        "in_subspace_fidelity": in_subspace_fidelity(logical_state, rho, dimension, resolved_n),
        "shots": backend_config.shots,
        "state_family": state_family,
        "correction_mode": backend_config.correction_mode,
        "simulation_lane": "aer",
        "noise_model": "custom" if noise_model is not None else "ideal",
    }
    if bootstrap_samples > 0:
        ci_summary = bootstrap_tomography_metrics(
            logical_state,
            dimension,
            setting_counts,
            n_physical=resolved_n,
            bootstrap_samples=bootstrap_samples,
            confidence_level=confidence_level,
            seed=seed_simulator,
        )
        record["observed_fidelity"] = record["fidelity"]
        record["observed_leakage"] = record["leakage"]
        record["observed_in_subspace_fidelity"] = record["in_subspace_fidelity"]
        record.update(ci_summary)
        record["fidelity"] = ci_summary["fidelity_bootstrap_mean"]
        record["leakage"] = ci_summary["leakage_bootstrap_mean"]
        record["in_subspace_fidelity"] = ci_summary["in_subspace_fidelity_bootstrap_mean"]
    return record, setting_counts, rho


def run_aer_delay_sweep(
    sweep: SweepConfig,
    backend_config: BackendConfig,
    *,
    simulator: Any | None = None,
    noise_model: Any | None = None,
    method: str = "automatic",
    seed_simulator: int = 17,
    bootstrap_samples: int = 0,
    confidence_level: float = 0.95,
    dt_ns_per_dt: float | None = None,
) -> list[dict[str, Any]]:
    """Aer simulation helper for local noisy validation of encoded teleportation circuits."""
    _require_aer_imports()

    state = make_probe_state(sweep)
    sim = simulator if simulator is not None else make_aer_simulator(method=method, noise_model=noise_model)

    results: list[dict[str, Any]] = []
    for index, delay_dt in enumerate(sweep.delay_dt_values):
        record, _, _ = _run_aer_tomography_for_state(
            state,
            sweep.dimension,
            n_physical=sweep.n_physical,
            delay_dt=int(delay_dt),
            backend_config=backend_config,
            simulator=sim,
            noise_model=noise_model,
            seed_simulator=seed_simulator + index,
            bootstrap_samples=bootstrap_samples,
            confidence_level=confidence_level,
            dt_ns_per_dt=dt_ns_per_dt,
            state_family=sweep.state_family,
        )
        results.append(record)
    return results


def run_aer_process_tomography(
    sweep: SweepConfig,
    backend_config: BackendConfig,
    *,
    simulator: Any | None = None,
    noise_model: Any | None = None,
    method: str = "automatic",
    seed_simulator: int = 17,
    bootstrap_samples: int = 0,
    confidence_level: float = 0.95,
    dt_ns_per_dt: float | None = None,
) -> list[dict[str, Any]]:
    """Run logical process tomography on the Aer teleportation lane."""
    _require_aer_imports()
    sim = simulator if simulator is not None else make_aer_simulator(method=method, noise_model=noise_model)
    resolved_dt_ns = resolved_aer_dt_ns_per_dt(dt_ns_per_dt)

    input_states = process_tomography_probe_states(sweep.dimension)
    input_densities = [pure_state_density(state) for state in input_states]
    n_physical = resolved_n_physical(sweep.dimension, sweep.n_physical)
    records: list[dict[str, Any]] = []
    for delay_index, delay_dt in enumerate(sweep.delay_dt_values):
        probe_records: list[dict[str, Any]] = []
        probe_setting_counts: list[dict[str, dict[str, int]]] = []
        logical_outputs: list[np.ndarray] = []

        for probe_index, logical_state in enumerate(input_states):
            record, setting_counts, rho = _run_aer_tomography_for_state(
                logical_state,
                sweep.dimension,
                n_physical=n_physical,
                delay_dt=int(delay_dt),
                backend_config=backend_config,
                simulator=sim,
                noise_model=noise_model,
                seed_simulator=seed_simulator + 1000 * delay_index + probe_index,
                dt_ns_per_dt=dt_ns_per_dt,
                state_family="process_tomography_probe",
            )
            probe_records.append(record)
            probe_setting_counts.append(setting_counts)
            logical_outputs.append(renormalized_logical_subspace_density(rho, sweep.dimension, n_physical))

        superoperator = reconstruct_superoperator(input_densities, logical_outputs)
        process_fidelity = process_fidelity_to_identity(superoperator, sweep.dimension)
        record = {
            "dimension": sweep.dimension,
            "n_physical": n_physical,
            "physical_hilbert_dimension": physical_hilbert_dimension_for_logical_dimension(sweep.dimension, n_physical),
            "fill_ratio": fill_ratio(sweep.dimension, n_physical),
            "delay_dt": int(delay_dt),
            "dt_ns": delay_dt_to_ns(delay_dt, dt_ns_per_dt=resolved_dt_ns),
            "backend_name": getattr(sim, "name", type(sim).__name__),
            "shots": backend_config.shots,
            "state_family": "process_tomography_probe",
            "correction_mode": backend_config.correction_mode,
            "simulation_lane": "aer_process_tomography",
            "noise_model": "custom" if noise_model is not None else "ideal",
            "probe_ensemble_size": len(input_states),
            "fidelity": float(np.mean([item["fidelity"] for item in probe_records])),
            "leakage": float(np.mean([item["leakage"] for item in probe_records])),
            "in_subspace_fidelity": float(np.mean([item["in_subspace_fidelity"] for item in probe_records])),
            "avg_probe_fidelity": float(np.mean([item["fidelity"] for item in probe_records])),
            "avg_probe_leakage": float(np.mean([item["leakage"] for item in probe_records])),
            "avg_probe_in_subspace_fidelity": float(np.mean([item["in_subspace_fidelity"] for item in probe_records])),
            "process_fidelity": process_fidelity,
            "average_gate_fidelity": average_gate_fidelity_from_process_fidelity(
                process_fidelity, sweep.dimension
            ),
        }
        if bootstrap_samples > 0:
            avg_ci_summary = bootstrap_average_tomography_metrics(
                input_states,
                sweep.dimension,
                probe_setting_counts,
                n_physical=n_physical,
                bootstrap_samples=bootstrap_samples,
                confidence_level=confidence_level,
                seed=seed_simulator + 10000 * (delay_index + 1),
            )
            record["observed_fidelity"] = record["fidelity"]
            record["observed_leakage"] = record["leakage"]
            record["observed_in_subspace_fidelity"] = record["in_subspace_fidelity"]
            record.update(avg_ci_summary)
            record["fidelity"] = avg_ci_summary["avg_probe_fidelity_bootstrap_mean"]
            record["leakage"] = avg_ci_summary["avg_probe_leakage_bootstrap_mean"]
            record["in_subspace_fidelity"] = avg_ci_summary["avg_probe_in_subspace_fidelity_bootstrap_mean"]
            record["avg_probe_fidelity"] = avg_ci_summary["avg_probe_fidelity_bootstrap_mean"]
            record["avg_probe_leakage"] = avg_ci_summary["avg_probe_leakage_bootstrap_mean"]
            record["avg_probe_in_subspace_fidelity"] = avg_ci_summary["avg_probe_in_subspace_fidelity_bootstrap_mean"]
            record["fidelity_ci_low"] = avg_ci_summary["avg_probe_fidelity_ci_low"]
            record["fidelity_ci_high"] = avg_ci_summary["avg_probe_fidelity_ci_high"]
            record["leakage_ci_low"] = avg_ci_summary["avg_probe_leakage_ci_low"]
            record["leakage_ci_high"] = avg_ci_summary["avg_probe_leakage_ci_high"]
            record["in_subspace_fidelity_ci_low"] = avg_ci_summary["avg_probe_in_subspace_fidelity_ci_low"]
            record["in_subspace_fidelity_ci_high"] = avg_ci_summary["avg_probe_in_subspace_fidelity_ci_high"]
            process_ci_summary = bootstrap_process_tomography_metrics(
                sweep.dimension,
                input_states,
                probe_setting_counts,
                n_physical=n_physical,
                bootstrap_samples=bootstrap_samples,
                confidence_level=confidence_level,
                seed=seed_simulator + 20000 * (delay_index + 1),
            )
            record["observed_process_fidelity"] = record["process_fidelity"]
            record["observed_average_gate_fidelity"] = record["average_gate_fidelity"]
            record.update(process_ci_summary)
            record["process_fidelity"] = process_ci_summary["process_fidelity_bootstrap_mean"]
            record["average_gate_fidelity"] = process_ci_summary["average_gate_fidelity_bootstrap_mean"]
        records.append(record)
    return records

# === END aer.py ===

# === BEGIN reports.py ===

import csv
import json
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt


def _normalize_path(path: str | Path) -> Path:
    """Filesystem or reporting helper used by the analysis and artifact pipeline."""
    return Path(path).expanduser().resolve()


def save_json(records: Sequence[dict[str, Any]], path: str | Path) -> Path:
    """Filesystem or reporting helper used by the analysis and artifact pipeline."""
    output = _normalize_path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(list(records), indent=2))
    return output


def save_csv(records: Sequence[dict[str, Any]], path: str | Path) -> Path:
    """Filesystem or reporting helper used by the analysis and artifact pipeline."""
    output = _normalize_path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for record in records:
        for key in record.keys():
            if key not in fieldnames:
                fieldnames.append(key)
    with output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow(record)
    return output


def load_json_records(path: str | Path) -> list[dict[str, Any]]:
    """Filesystem or reporting helper used by the analysis and artifact pipeline."""
    input_path = _normalize_path(path)
    return list(json.loads(input_path.read_text()))


def _group_label(record: dict[str, Any]) -> str:
    """Filesystem or reporting helper used by the analysis and artifact pipeline."""
    parts = [f"d={record.get('dimension')}", f"n={record.get('n_physical')}"]
    fill_ratio = record.get("fill_ratio")
    if fill_ratio is not None:
        parts.append(f"phi={float(fill_ratio):.3f}")
    return ", ".join(parts)


def plot_metric_vs_delay(
    records: Sequence[dict[str, Any]],
    *,
    metric: str,
    path: str | Path,
    title: str | None = None,
) -> Path:
    """Generate a matplotlib figure for one of the thesis analysis outputs."""
    if not records:
        raise ValueError("records cannot be empty")
    use_dt_ns = all(record.get("dt_ns") is not None for record in records)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[_group_label(record)].append(record)

    fig, ax = plt.subplots(figsize=(8, 5))
    for label, group in grouped.items():
        ordered = sorted(group, key=lambda item: item.get("delay_dt", item.get("step", 0)))
        if use_dt_ns:
            xs = [float(item["dt_ns"]) for item in ordered]
        else:
            xs = [item.get("delay_dt", item.get("step", 0)) for item in ordered]
        ys = [float(item[metric]) for item in ordered]
        ax.plot(xs, ys, marker="o", label=label)
    ax.set_xlabel("delay (ns)" if use_dt_ns else "delay_dt / step")
    ax.set_ylabel(metric)
    ax.set_title(title or f"{metric} vs delay")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    output = _normalize_path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180)
    plt.close(fig)
    return output


def plot_metric_vs_fill_ratio(
    records: Sequence[dict[str, Any]],
    *,
    metric: str,
    path: str | Path,
    delay_dt: int | None = None,
    title: str | None = None,
) -> Path:
    """Generate a matplotlib figure for one of the thesis analysis outputs."""
    if not records:
        raise ValueError("records cannot be empty")
    filtered = [record for record in records if delay_dt is None or int(record.get("delay_dt", -1)) == delay_dt]
    if not filtered:
        raise ValueError("no records remain after delay filter")

    fig, ax = plt.subplots(figsize=(8, 5))
    xs = [float(record["fill_ratio"]) for record in filtered]
    ys = [float(record[metric]) for record in filtered]
    ax.plot(xs, ys, marker="o")
    ax.set_xlabel("fill_ratio")
    ax.set_ylabel(metric)
    if delay_dt is None:
        ax.set_title(title or f"{metric} vs fill ratio")
    else:
        ax.set_title(title or f"{metric} vs fill ratio at delay_dt={delay_dt}")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    output = _normalize_path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180)
    plt.close(fig)
    return output


def plot_blp_vs_memory_strength(
    records: Sequence[dict[str, Any]],
    *,
    path: str | Path,
    title: str | None = None,
) -> Path:
    """Generate a matplotlib figure for one of the thesis analysis outputs."""
    if not records:
        raise ValueError("records cannot be empty")
    ordered = sorted(records, key=lambda item: float(item["memory_strength"]))
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(
        [float(record["memory_strength"]) for record in ordered],
        [float(record["blp_measure"]) for record in ordered],
        marker="o",
    )
    ax.set_xlabel("memory_strength")
    ax.set_ylabel("blp_measure")
    ax.set_title(title or "BLP non-Markovianity vs memory strength")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    output = _normalize_path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180)
    plt.close(fig)
    return output


def plot_blp_vs_switching_probability(
    records: Sequence[dict[str, Any]],
    *,
    path: str | Path,
    title: str | None = None,
) -> Path:
    """Plot BLP non-Markovianity against the random-telegraph switching probability."""
    if not records:
        raise ValueError("records cannot be empty")
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[_group_label(record)].append(record)

    fig, ax = plt.subplots(figsize=(8, 5))
    for label, group in grouped.items():
        ordered = sorted(group, key=lambda item: float(item["switching_probability"]))
        ax.plot(
            [float(record["switching_probability"]) for record in ordered],
            [float(record["blp_measure"]) for record in ordered],
            marker="o",
            label=label,
        )
    ax.set_xlabel("switching_probability")
    ax.set_ylabel("blp_measure")
    ax.set_title(title or "BLP non-Markovianity vs switching probability")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    output = _normalize_path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180)
    plt.close(fig)
    return output


def summarize_fixed_n_comparison(
    records: Sequence[dict[str, Any]],
    *,
    n_physical: int,
    metric_keys: Sequence[str] = (
        "fidelity",
        "leakage",
        "in_subspace_fidelity",
        "process_fidelity",
        "average_gate_fidelity",
    ),
    dt_ns_per_dt: float | None = None,
) -> list[dict[str, Any]]:
    """Build or parse structured comparison summaries for fixed-n analysis reports."""
    filtered = [record for record in records if int(record.get("n_physical", -1)) == n_physical]
    if not filtered:
        raise ValueError(f"no records found for n_physical={n_physical}")

    delays = sorted({int(record.get("delay_dt", 0)) for record in filtered})
    dimensions = sorted({int(record["dimension"]) for record in filtered})
    reference_dimension = max(dimensions)
    summary: list[dict[str, Any]] = []
    for delay in delays:
        row: dict[str, Any] = {
            "n_physical": n_physical,
            "delay_dt": delay,
            "dt_ns": delay_dt_to_ns(delay, dt_ns_per_dt=dt_ns_per_dt),
        }
        delay_records = [
            record for record in filtered if int(record.get("delay_dt", 0)) == delay
        ]
        source_lanes = sorted(
            {
                str(record.get("simulation_lane"))
                for record in delay_records
                if record.get("simulation_lane") is not None
            }
        )
        if source_lanes:
            row["source_simulation_lanes"] = ",".join(source_lanes)
        contains_theory_baseline = any(
            record.get("simulation_lane") == "markovian_model" for record in delay_records
        )
        contains_explicit_theory_mixing = any(
            record.get("simulation_lane") == "markovian_model"
            and (
                (
                    record.get("t_dep") is not None
                    and float(record.get("t_dep", 0.0)) > 0.0
                )
                or (
                    record.get("depolarizing_probability") is not None
                    and float(record.get("depolarizing_probability", 0.0)) > 0.0
                )
            )
            for record in delay_records
        )
        row["contains_theory_baseline"] = contains_theory_baseline
        row["contains_explicit_theory_mixing"] = contains_explicit_theory_mixing
        by_dimension: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for record in filtered:
            if int(record.get("delay_dt", 0)) == delay:
                by_dimension[int(record["dimension"])].append(record)
        for dimension in dimensions:
            matching_records = by_dimension.get(dimension, [])
            if not matching_records:
                continue
            record = _merge_summary_source_records(matching_records)
            row[_summary_fill_ratio_key(dimension)] = float(record["fill_ratio"])
            if row["dt_ns"] is None and record.get("dt_ns") is not None:
                row["dt_ns"] = float(record["dt_ns"])
            for key in metric_keys:
                if key in record:
                    row[_summary_metric_key(dimension, key)] = float(record[key])
                bounds = _metric_confidence_interval_bounds(record, key)
                if bounds is not None:
                    row[_summary_metric_ci_key(dimension, key, "low")] = bounds[0]
                    row[_summary_metric_ci_key(dimension, key, "high")] = bounds[1]
        for dimension in dimensions:
            if dimension == reference_dimension:
                continue
            for key in metric_keys:
                ka = _summary_metric_key(dimension, key)
                kb = _summary_metric_key(reference_dimension, key)
                if ka in row and kb in row:
                    row[_summary_delta_key(reference_dimension, dimension, key)] = row[kb] - row[ka]
                    bounds_a = _summary_metric_ci_bounds_from_row(row, dimension, key)
                    bounds_b = _summary_metric_ci_bounds_from_row(row, reference_dimension, key)
                    if bounds_a is not None and bounds_b is not None:
                        row[_summary_significant_key(reference_dimension, dimension, key)] = _intervals_do_not_overlap(
                            bounds_b,
                            bounds_a,
                        )
        summary.append(row)
    return summary


def _summary_fill_ratio_key(dimension: int) -> str:
    """Build or parse structured comparison summaries for fixed-n analysis reports."""
    return f"d{dimension}|fill_ratio"



def _summary_metric_key(dimension: int, metric: str) -> str:
    """Build or parse structured comparison summaries for fixed-n analysis reports."""
    return f"d{dimension}|metric|{metric}"


def _summary_metric_ci_key(dimension: int, metric: str, bound: str) -> str:
    """Build the structured key used for per-dimension confidence intervals."""
    return f"d{dimension}|metric_ci|{metric}|{bound}"



def _summary_delta_key(reference_dimension: int, dimension: int, metric: str) -> str:
    """Build or parse structured comparison summaries for fixed-n analysis reports."""
    return f"delta|d{reference_dimension}-d{dimension}|metric|{metric}"


def _summary_significant_key(reference_dimension: int, dimension: int, metric: str) -> str:
    """Build the structured key used for report-level significance booleans."""
    return f"significant|d{reference_dimension}-d{dimension}|metric|{metric}"


def _merge_summary_source_records(records: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Merge multiple records for the same dimension/delay into one comparison source."""
    merged: dict[str, Any] = {}
    for record in records:
        for key, value in record.items():
            if value is None:
                continue
            merged[key] = value
    return merged


def _metric_confidence_interval_bounds(record: dict[str, Any], metric: str) -> tuple[float, float] | None:
    """Extract a confidence interval for a headline metric when a record exposes one."""
    for prefix in (metric, f"avg_probe_{metric}"):
        low_key = f"{prefix}_ci_low"
        high_key = f"{prefix}_ci_high"
        if low_key in record and high_key in record:
            return float(record[low_key]), float(record[high_key])
    return None


def _summary_metric_ci_bounds_from_row(
    row: dict[str, Any],
    dimension: int,
    metric: str,
) -> tuple[float, float] | None:
    """Extract a per-dimension confidence interval from a summary row."""
    low_key = _summary_metric_ci_key(dimension, metric, "low")
    high_key = _summary_metric_ci_key(dimension, metric, "high")
    if low_key in row and high_key in row:
        return float(row[low_key]), float(row[high_key])
    return None


def _intervals_do_not_overlap(
    left: tuple[float, float],
    right: tuple[float, float],
) -> bool:
    """Return whether two confidence intervals are separated."""
    return float(left[0]) > float(right[1]) or float(right[0]) > float(left[1])



def _parse_summary_key(key: str) -> tuple[str, int | None, int | None, str | None]:
    """Build or parse structured comparison summaries for fixed-n analysis reports."""
    parts = key.split("|")
    if len(parts) == 2 and parts[0].startswith("d") and parts[0][1:].isdigit() and parts[1] == "fill_ratio":
        return ("fill_ratio", int(parts[0][1:]), None, None)
    if len(parts) == 3 and parts[0].startswith("d") and parts[0][1:].isdigit() and parts[1] == "metric":
        return ("metric", int(parts[0][1:]), None, parts[2])
    if len(parts) == 4 and parts[0].startswith("d") and parts[0][1:].isdigit() and parts[1] == "metric_ci":
        return ("metric_ci", int(parts[0][1:]), None, parts[2])
    if len(parts) == 4 and parts[0] == "delta" and parts[1].startswith("d") and "-d" in parts[1] and parts[2] == "metric":
        ref_part, other_part = parts[1].split("-d", 1)
        if ref_part[1:].isdigit() and other_part.isdigit():
            return ("delta", int(ref_part[1:]), int(other_part), parts[3])
    if len(parts) == 4 and parts[0] == "significant" and parts[1].startswith("d") and "-d" in parts[1] and parts[2] == "metric":
        ref_part, other_part = parts[1].split("-d", 1)
        if ref_part[1:].isdigit() and other_part.isdigit():
            return ("significant", int(ref_part[1:]), int(other_part), parts[3])
    return ("other", None, None, None)


_THREE_LANE_METRIC_ORDER = (
    "fidelity",
    "leakage",
    "in_subspace_fidelity",
    "process_fidelity",
    "average_gate_fidelity",
)

_THREE_LANE_LANE_ORDER = ("theory", "aer", "hardware")

_THREE_LANE_LANE_LABELS = {
    "theory": "Theory baseline",
    "aer": "Aer circuit lane",
    "hardware": "IBM hardware lane",
}


def _is_fixed_n_summary_row(record: dict[str, Any]) -> bool:
    """Return whether a JSON record already looks like a fixed-n comparison summary row."""
    return any(
        _parse_summary_key(key)[0] in {"fill_ratio", "metric", "metric_ci", "delta", "significant"}
        for key in record.keys()
    )


def merge_fixed_n_summary_rows(summary_rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge fixed-n comparison summary rows that share the same physical-qubit count and delay."""
    grouped: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    for row in summary_rows:
        grouped[(int(row.get("n_physical", -1)), int(row.get("delay_dt", 0)))].append(row)

    merged_rows: list[dict[str, Any]] = []
    for key in sorted(grouped.keys()):
        group = grouped[key]
        merged = _merge_summary_source_records(group)
        source_lanes = sorted(
            {
                lane.strip()
                for row in group
                for lane in str(row.get("source_simulation_lanes", "")).split(",")
                if lane.strip()
            }
        )
        if source_lanes:
            merged["source_simulation_lanes"] = ",".join(source_lanes)
        merged["contains_theory_baseline"] = any(
            bool(row.get("contains_theory_baseline")) for row in group
        )
        merged["contains_explicit_theory_mixing"] = any(
            bool(row.get("contains_explicit_theory_mixing")) for row in group
        )
        merged_rows.append(merged)
    return merged_rows


def load_fixed_n_summary_rows(
    input_paths: Sequence[str],
    *,
    n_physical: int,
    dt_ns_per_dt: float | None = None,
) -> list[dict[str, Any]]:
    """Load one or more fixed-n summary or raw-record JSON files and normalize them to summary rows."""
    raw_records: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    for path in input_paths:
        records = load_json_records(path)
        if not records:
            continue
        if all(_is_fixed_n_summary_row(record) for record in records):
            summary_rows.extend(records)
        else:
            raw_records.extend(records)

    if raw_records:
        summary_rows.extend(
            summarize_fixed_n_comparison(
                raw_records,
                n_physical=n_physical,
                dt_ns_per_dt=dt_ns_per_dt,
            )
        )

    filtered_rows = [
        row for row in summary_rows if int(row.get("n_physical", -1)) == n_physical
    ]
    if not filtered_rows:
        raise ValueError(f"no fixed-n comparison rows found for n_physical={n_physical}")
    return merge_fixed_n_summary_rows(filtered_rows)


def summarize_three_lane_fixed_n_table(
    lane_summaries: Mapping[str, Sequence[dict[str, Any]]],
    *,
    lane_labels: Mapping[str, str] | None = None,
    metric_order: Sequence[str] = _THREE_LANE_METRIC_ORDER,
) -> list[dict[str, Any]]:
    """Build tidy rows for a three-lane fixed-n comparison report."""
    if not lane_summaries:
        raise ValueError("lane_summaries cannot be empty")

    resolved_lane_labels = dict(_THREE_LANE_LANE_LABELS)
    if lane_labels is not None:
        resolved_lane_labels.update(lane_labels)

    dimensions = sorted(
        {
            dimension
            for rows in lane_summaries.values()
            for row in rows
            for key in row.keys()
            for kind, dimension, _, _ in [_parse_summary_key(key)]
            if kind in {"fill_ratio", "metric"} and dimension is not None
        }
    )
    if not dimensions:
        raise ValueError("lane summaries do not expose any fixed-n dimensions")
    reference_dimension = max(dimensions)
    comparison_dimension = dimensions[-2] if len(dimensions) >= 2 else reference_dimension

    lane_order = list(_THREE_LANE_LANE_ORDER) + sorted(
        lane for lane in lane_summaries.keys() if lane not in _THREE_LANE_LANE_ORDER
    )
    lane_index = {lane: idx for idx, lane in enumerate(lane_order)}

    rows: list[dict[str, Any]] = []
    for lane in lane_order:
        if lane not in lane_summaries:
            continue
        summary_rows = sorted(
            lane_summaries[lane],
            key=lambda row: (
                float(row["dt_ns"]) if row.get("dt_ns") is not None else float("inf"),
                int(row.get("delay_dt", 0)),
            ),
        )
        for summary_row in summary_rows:
            available_metrics = [
                metric
                for metric in metric_order
                if any(_summary_metric_key(dim, metric) in summary_row for dim in dimensions)
            ]
            for metric in available_metrics:
                row: dict[str, Any] = {
                    "lane": lane,
                    "lane_label": resolved_lane_labels.get(lane, lane.replace("_", " ").title()),
                    "lane_order": lane_index[lane],
                    "n_physical": int(summary_row["n_physical"]),
                    "delay_dt": int(summary_row.get("delay_dt", 0)),
                    "dt_ns": summary_row.get("dt_ns"),
                    "metric": metric,
                    "dimensions": ",".join(str(dim) for dim in dimensions),
                    "reference_dimension": reference_dimension,
                    "comparison_dimension": comparison_dimension,
                    "source_simulation_lanes": summary_row.get("source_simulation_lanes"),
                    "contains_theory_baseline": bool(summary_row.get("contains_theory_baseline")),
                    "contains_explicit_theory_mixing": bool(
                        summary_row.get("contains_explicit_theory_mixing")
                    ),
                }
                for dim in dimensions:
                    fill_key = _summary_fill_ratio_key(dim)
                    metric_key = _summary_metric_key(dim, metric)
                    if fill_key in summary_row:
                        row[f"d{dim}_fill_ratio"] = float(summary_row[fill_key])
                    if metric_key in summary_row:
                        row[f"d{dim}_value"] = float(summary_row[metric_key])
                    ci_bounds = _summary_metric_ci_bounds_from_row(summary_row, dim, metric)
                    if ci_bounds is not None:
                        row[f"d{dim}_ci_low"] = ci_bounds[0]
                        row[f"d{dim}_ci_high"] = ci_bounds[1]
                for dim in dimensions:
                    if dim == reference_dimension:
                        continue
                    delta_key = _summary_delta_key(reference_dimension, dim, metric)
                    significance_key = _summary_significant_key(reference_dimension, dim, metric)
                    if delta_key in summary_row:
                        row[f"delta_d{reference_dimension}_minus_d{dim}"] = float(
                            summary_row[delta_key]
                        )
                    if significance_key in summary_row:
                        row[f"significant_d{reference_dimension}_minus_d{dim}"] = bool(
                            summary_row[significance_key]
                        )
                rows.append(row)

    rows.sort(
        key=lambda row: (
            metric_order.index(str(row["metric"]))
            if str(row["metric"]) in metric_order
            else len(metric_order),
            int(row["lane_order"]),
            int(row["delay_dt"]),
        )
    )
    return rows


def _three_lane_metric_title(metric: str) -> str:
    """Return a readable markdown section title for a three-lane comparison metric."""
    titles = {
        "fidelity": "State fidelity",
        "leakage": "Leakage",
        "in_subspace_fidelity": "In-subspace fidelity",
        "process_fidelity": "Process fidelity",
        "average_gate_fidelity": "Average gate fidelity",
    }
    return titles.get(metric, metric.replace("_", " "))


def _three_lane_format_metric_value(row: dict[str, Any], dimension: int) -> str:
    """Format one dimension-specific value and its confidence interval for markdown tables."""
    value = row.get(f"d{dimension}_value")
    if value is None:
        return "—"
    ci_low = row.get(f"d{dimension}_ci_low")
    ci_high = row.get(f"d{dimension}_ci_high")
    if ci_low is None or ci_high is None:
        return f"{float(value):.6f}"
    return f"{float(value):.6f} [{float(ci_low):.6f}, {float(ci_high):.6f}]"


def _three_lane_format_delta(row: dict[str, Any], reference_dimension: int, dimension: int) -> str:
    """Format a comparison delta cell for the markdown report."""
    value = row.get(f"delta_d{reference_dimension}_minus_d{dimension}")
    if value is None:
        return "—"
    return f"{float(value):+.6f}"


def _three_lane_format_significance(row: dict[str, Any], reference_dimension: int, dimension: int) -> str:
    """Format the CI-separation flag for the markdown report."""
    value = row.get(f"significant_d{reference_dimension}_minus_d{dimension}")
    if value is None:
        return "—"
    return "yes" if bool(value) else "overlap"


def _three_lane_format_delay_grid(rows: Sequence[dict[str, Any]]) -> str:
    """Format the native delay grid used by one lane."""
    seen: set[tuple[int, float | None]] = set()
    ordered_pairs: list[tuple[int, float | None]] = []
    for row in sorted(rows, key=lambda item: int(item["delay_dt"])):
        pair = (
            int(row["delay_dt"]),
            float(row["dt_ns"]) if row.get("dt_ns") is not None else None,
        )
        if pair in seen:
            continue
        seen.add(pair)
        ordered_pairs.append(pair)
    parts = []
    for delay_dt, dt_ns in ordered_pairs:
        if dt_ns is None:
            parts.append(f"{delay_dt} dt")
        else:
            parts.append(f"{delay_dt} dt ({dt_ns:.1f} ns)")
    return ", ".join(parts)


def _three_lane_format_significance_count(
    rows: Sequence[dict[str, Any]],
    *,
    metric: str,
    reference_dimension: int,
    dimension: int,
) -> str:
    """Count how often a d_ref-d_dim comparison is CI-separated within one lane."""
    values = [
        bool(row[f"significant_d{reference_dimension}_minus_d{dimension}"])
        for row in rows
        if row.get("metric") == metric
        and f"significant_d{reference_dimension}_minus_d{dimension}" in row
    ]
    if not values:
        return "—"
    return f"{sum(values)}/{len(values)} delays"


def save_three_lane_fixed_n_markdown_report(
    rows: Sequence[dict[str, Any]],
    *,
    path: str | Path,
    title: str = "Three-lane fixed-n comparison",
) -> Path:
    """Write one markdown report that places theory, Aer, and hardware fixed-n summaries side by side."""
    if not rows:
        raise ValueError("rows cannot be empty")

    reference_dimension = int(rows[0]["reference_dimension"])
    comparison_dimension = int(rows[0]["comparison_dimension"])
    dimensions = [int(item) for item in str(rows[0]["dimensions"]).split(",") if item]
    control_dimension = min(dimensions)
    lane_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        lane_groups[str(row["lane"])].append(row)

    lane_order = list(_THREE_LANE_LANE_ORDER) + sorted(
        lane for lane in lane_groups.keys() if lane not in _THREE_LANE_LANE_ORDER
    )
    metric_order = [
        metric for metric in _THREE_LANE_METRIC_ORDER if any(row["metric"] == metric for row in rows)
    ]

    lines = [f"# {title}", ""]
    lines.extend(
        [
            "## Scope",
            "",
            "- This report preserves each lane's native delay grid instead of interpolating missing points.",
            "- Hardware rows merge the saved state-tomography and process-tomography comparison summaries on the same backend.",
            "- Process metrics are shown only for the Aer and hardware lanes because the theory baseline does not expose channel tomography.",
            "- For the full-fill-ratio case (here d=4, phi=1.000), leakage is structurally zero because no unused Hilbert-space states remain. Treat any reported L=0.000 in that column as definitional rather than as an independently measured absence of noise.",
        ]
    )
    if any(bool(row.get("contains_theory_baseline")) for row in rows):
        lines.append(
            "- The theory lane remains a baseline-only effective model; any nonzero theory-lane leakage comes from its explicit codespace-mixing term rather than from circuit execution."
        )
    lines.append("")

    lines.extend(
        [
            "## Lane Overview",
            "",
            "| Lane | Delay grid | Metrics | d4-d3 fidelity sig | d4-d3 process sig |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for lane in lane_order:
        if lane not in lane_groups:
            continue
        group = lane_groups[lane]
        label = str(group[0]["lane_label"])
        metrics = ", ".join(
            metric for metric in metric_order if any(row["metric"] == metric for row in group)
        )
        lines.append(
            "| "
            + " | ".join(
                [
                    label,
                    _three_lane_format_delay_grid(group),
                    metrics or "—",
                    _three_lane_format_significance_count(
                        group,
                        metric="fidelity",
                        reference_dimension=reference_dimension,
                        dimension=comparison_dimension,
                    ),
                    _three_lane_format_significance_count(
                        group,
                        metric="process_fidelity",
                        reference_dimension=reference_dimension,
                        dimension=comparison_dimension,
                    ),
                ]
            )
            + " |"
        )
    lines.append("")

    for metric in metric_order:
        metric_rows = [
            row
            for lane in lane_order
            for row in sorted(
                lane_groups.get(lane, []),
                key=lambda item: int(item["delay_dt"]),
            )
            if row["metric"] == metric
        ]
        if not metric_rows:
            continue
        lines.extend(
            [
                f"## {_three_lane_metric_title(metric)}",
                "",
                f"| Lane | delay_dt | dt_ns | d{control_dimension} | d{comparison_dimension} | d{reference_dimension} | Δ(d{reference_dimension}-d{comparison_dimension}) | sig | Δ(d{reference_dimension}-d{control_dimension}) | sig |",
                "| --- | ---: | ---: | --- | --- | --- | ---: | --- | ---: | --- |",
            ]
        )
        for row in metric_rows:
            dt_ns = row.get("dt_ns")
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(row["lane_label"]),
                        str(int(row["delay_dt"])),
                        f"{float(dt_ns):.3f}" if dt_ns is not None else "—",
                        _three_lane_format_metric_value(row, control_dimension),
                        _three_lane_format_metric_value(row, comparison_dimension),
                        _three_lane_format_metric_value(row, reference_dimension),
                        _three_lane_format_delta(row, reference_dimension, comparison_dimension),
                        _three_lane_format_significance(row, reference_dimension, comparison_dimension),
                        _three_lane_format_delta(row, reference_dimension, control_dimension),
                        _three_lane_format_significance(row, reference_dimension, control_dimension),
                    ]
                )
                + " |"
            )
        lines.append("")

    output = _normalize_path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines).rstrip() + "\n")
    return output



def save_fixed_n_markdown_report(
    summary_rows: Sequence[dict[str, Any]],
    *,
    path: str | Path,
    title: str = "Fixed-n comparison report",
) -> Path:
    """Filesystem or reporting helper used by the analysis and artifact pipeline."""
    if not summary_rows:
        raise ValueError("summary_rows cannot be empty")
    lines = [f"# {title}", ""]
    dims = sorted(
        {
            dimension
            for row in summary_rows
            for key in row.keys()
            for kind, dimension, _, _ in [_parse_summary_key(key)]
            if kind in {"fill_ratio", "metric"} and dimension is not None
        }
    )
    metric_names = sorted(
        {
            metric
            for row in summary_rows
            for key in row.keys()
            for kind, _, _, metric in [_parse_summary_key(key)]
            if kind == "metric" and metric is not None
        }
    )
    significance_values = [
        bool(value)
        for row in summary_rows
        for key, value in row.items()
        if _parse_summary_key(key)[0] == "significant"
    ]
    contains_theory_baseline = any(
        bool(row.get("contains_theory_baseline")) for row in summary_rows
    )
    contains_explicit_theory_mixing = any(
        bool(row.get("contains_explicit_theory_mixing")) for row in summary_rows
    )
    leakage_values = [
        float(row[_summary_metric_key(dim, "leakage")])
        for row in summary_rows
        for dim in dims
        if dim != max(dims) and _summary_metric_key(dim, "leakage") in row
    ]
    reference_dimension = max(dims)
    reference_fill_ratio_key = _summary_fill_ratio_key(reference_dimension)
    reference_is_full_fill = any(
        reference_fill_ratio_key in row
        and abs(float(row[reference_fill_ratio_key]) - 1.0) <= 1e-12
        for row in summary_rows
    )
    interpretation_notes: list[str] = []
    if reference_is_full_fill:
        interpretation_notes.append(
            f"For the full-fill-ratio case (here d={reference_dimension}, phi=1.000), leakage is "
            "structurally zero because no unused Hilbert-space states remain. Treat any reported "
            "L=0.000 for that row as definitional rather than as an independently measured absence "
            "of noise."
        )
    if contains_theory_baseline:
        interpretation_notes.append(
            "These records come from the effective Markovian theory lane. Treat them as a "
            "baseline-only model rather than as a circuit-level leakage study alongside Aer "
            "or hardware."
        )
    if contains_explicit_theory_mixing:
        interpretation_notes.append(
            "Any nonzero leakage in these theory-lane rows is generated by the explicit "
            "codespace-mixing term (`t_dep` or `depolarizing_probability`). That is a different "
            "mechanism from circuit-level leakage caused by entangling gates, measurement, "
            "readout, and feed-forward noise."
        )
    if significance_values and not any(significance_values):
        interpretation_notes.append(
            "All reported confidence intervals overlap. In this regime the current model does not "
            "resolve statistically distinguishable differences between encoded dimensions."
        )
    if leakage_values and all(abs(value) <= 1e-12 for value in leakage_values):
        interpretation_notes.append(
            "Leakage is identically zero in these source records. For the Markovian lane this usually "
            "means only codespace-preserving T1/T2 terms were enabled; add an explicit codespace-mixing "
            "term such as t_dep or depolarizing_probability to study fill-ratio leakage."
        )
    if interpretation_notes:
        lines.append("## Interpretation")
        lines.append("")
        for note in interpretation_notes:
            lines.append(f"- {note}")
        lines.append("")
    for row in summary_rows:
        if row.get("dt_ns") is None:
            lines.append(f"## delay_dt = {row['delay_dt']}")
        else:
            lines.append(f"## delay_dt = {row['delay_dt']} ({float(row['dt_ns']):.3f} ns)")
        lines.append("")
        for dim in dims:
            phi_key = _summary_fill_ratio_key(dim)
            if phi_key in row:
                lines.append(f"- d={dim}, phi={row[phi_key]:.3f}")
            for metric in metric_names:
                metric_key = _summary_metric_key(dim, metric)
                if metric_key in row:
                    ci_bounds = _summary_metric_ci_bounds_from_row(row, dim, metric)
                    if ci_bounds is None:
                        lines.append(f"  - {metric}: {row[metric_key]:.6f}")
                    else:
                        lines.append(
                            f"  - {metric}: {row[metric_key]:.6f} "
                            f"[CI {ci_bounds[0]:.6f}, {ci_bounds[1]:.6f}]"
                        )
        delta_keys = sorted(key for key in row.keys() if _parse_summary_key(key)[0] == "delta")
        if delta_keys:
            lines.append("- differences")
            for key in delta_keys:
                kind, ref_dim, dim, metric = _parse_summary_key(key)
                if kind == "delta" and ref_dim is not None and dim is not None and metric is not None:
                    significance_key = _summary_significant_key(ref_dim, dim, metric)
                    significance = row.get(significance_key)
                    suffix = ""
                    if isinstance(significance, bool):
                        suffix = "; statistically distinguishable" if significance else "; CIs overlap"
                    lines.append(f"  - delta {metric} (d={ref_dim} - d={dim}): {float(row[key]):+.6f}{suffix}")
        lines.append("")
    output = _normalize_path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines).rstrip() + "\n")
    return output


def save_blp_markdown_report(
    records: Sequence[dict[str, Any]],
    *,
    path: str | Path,
    title: str = "BLP scan report",
) -> Path:
    """Write a concise markdown summary for correlated-memory or random-telegraph BLP scans."""
    if not records:
        raise ValueError("records cannot be empty")

    ordered = sorted(
        records,
        key=lambda item: (
            int(item.get("dimension", 0)),
            int(item.get("n_physical", 0)),
            float(item.get("memory_strength", item.get("switching_probability", 0.0))),
        ),
    )
    first = ordered[0]
    lines = [f"# {title}", ""]
    if "switching_probability" in first:
        lines.extend(
            [
                "- model: random telegraph dephasing",
                f"- probe pair: {first.get('probe_pair', 'unspecified')}",
                f"- coupling_strength: {float(first['coupling_strength']):.6f}",
                f"- steps: {int(first['steps'])}",
                f"- dt_per_step: {float(first['dt_per_step']):.6f}",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "- model: correlated-memory Pauli lane",
                f"- steps: {int(first['steps'])}",
                f"- base_phase_flip_probability: {float(first['base_phase_flip_probability']):.6f}",
                "",
            ]
        )

    grouped: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    for record in ordered:
        grouped[(int(record["dimension"]), int(record["n_physical"]))].append(record)

    for (dimension, n_physical), group in sorted(grouped.items()):
        fill = float(group[0]["fill_ratio"])
        if "switching_probability" in group[0]:
            group_sorted = sorted(group, key=lambda item: float(item["switching_probability"]))
            monotone = all(
                float(group_sorted[i + 1]["blp_measure"]) <= float(group_sorted[i]["blp_measure"]) + 1e-12
                for i in range(len(group_sorted) - 1)
            )
        else:
            group_sorted = sorted(group, key=lambda item: float(item["memory_strength"]))
            monotone = all(
                float(group_sorted[i + 1]["blp_measure"]) >= float(group_sorted[i]["blp_measure"]) - 1e-12
                for i in range(len(group_sorted) - 1)
            )
        lines.extend(
            [
                f"## d={dimension}, n={n_physical}, phi={fill:.3f}",
                f"- monotone trend across scanned parameter: {'yes' if monotone else 'no'}",
            ]
        )
        if "switching_probability" in group[0]:
            for record in group_sorted:
                tau_steps = record.get("correlation_time_steps")
                tau_label = "inf" if tau_steps is None else f"{float(tau_steps):.3f} steps"
                lines.append(
                    f"- p_switch={float(record['switching_probability']):.4f}, "
                    f"tau_corr≈{tau_label}, BLP={float(record['blp_measure']):.6f}"
                )
        else:
            for record in group_sorted:
                lines.append(
                    f"- memory_strength={float(record['memory_strength']):.3f}, "
                    f"BLP={float(record['blp_measure']):.6f}"
                )
        lines.append("")

    output = _normalize_path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines).rstrip() + "\n")
    return output


def save_random_telegraph_calibration_markdown_report(
    calibration: dict[str, Any],
    *,
    path: str | Path,
    title: str = "Random-telegraph calibration report",
) -> Path:
    """Write a concise markdown summary for backend-anchored RTN calibration."""
    lines = [f"# {title}", ""]
    lines.extend(
        [
            f"- source backend: {calibration.get('source_backend_name', 'unknown')}",
            f"- source lane: {calibration.get('source_simulation_lane', 'unknown')}",
            f"- logical dimension: d={int(calibration['dimension'])}",
            f"- physical qubits: n={int(calibration['n_physical'])}",
            f"- source metric: {calibration['metric']}",
            f"- fit mode: {calibration['fit_mode']}",
            f"- baseline metric value: {float(calibration['baseline_metric_value']):.6f}",
            f"- calibration floor: {float(calibration['calibration_floor']):.6f}",
            (
                f"- fitted effective T2: {float(calibration['effective_t2_ns']):.3f} ns"
                if calibration.get("effective_t2_ns_ci_low") is None
                else (
                    f"- fitted effective T2: {float(calibration['effective_t2_ns']):.3f} ns "
                    f"[CI {float(calibration['effective_t2_ns_ci_low']):.3f}, "
                    f"{float(calibration['effective_t2_ns_ci_high']):.3f}]"
                )
            ),
            f"- assumed correlation time: tau_corr := T2_eff = {float(calibration['correlation_time_ns']):.3f} ns",
            (
                f"- recommended switching probability: {float(calibration['switching_probability']):.6f} per {float(calibration['dt_ns_per_step']):.3f} ns step"
                if calibration.get("switching_probability_ci_low") is None
                else (
                    f"- recommended switching probability: {float(calibration['switching_probability']):.6f} "
                    f"[CI {float(calibration['switching_probability_ci_low']):.6f}, "
                    f"{float(calibration['switching_probability_ci_high']):.6f}] "
                    f"per {float(calibration['dt_ns_per_step']):.3f} ns step"
                )
            ),
            f"- calibration formula: {calibration['calibration_formula']}",
            f"- calibration assumption: {calibration['calibration_assumption']}",
            "",
            "## Selected Delay Points",
            "",
        ]
    )

    for point in calibration.get("selected_points", []):
        ratio = float(point["normalized_decay_ratio"])
        if "normalized_decay_ratio_ci_low" in point and "normalized_decay_ratio_ci_high" in point:
            lines.append(
                f"- delay_dt={int(point['delay_dt'])}, delay={float(point['delay_ns']):.3f} ns, "
                f"normalized_ratio={ratio:.6f} "
                f"[CI {float(point['normalized_decay_ratio_ci_low']):.6f}, "
                f"{float(point['normalized_decay_ratio_ci_high']):.6f}]"
            )
        else:
            lines.append(
                f"- delay_dt={int(point['delay_dt'])}, delay={float(point['delay_ns']):.3f} ns, "
                f"normalized_ratio={ratio:.6f}"
            )

    output = _normalize_path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines).rstrip() + "\n")
    return output

# === END reports.py ===

# === BEGIN sweeps.py ===

from collections.abc import Callable, Sequence
from typing import Any

import numpy as np


ProgressCallback = Callable[[str], None]


def _emit_progress(progress: ProgressCallback | None, message: str) -> None:
    """Emit optional progress updates for long-running sweep commands."""
    if progress is not None:
        progress(message)


def make_probe_state(config: SweepConfig) -> np.ndarray:
    """Construct make probe state for simulation, tomography, or benchmarking."""
    if config.state_family == "haar":
        return random_haar_state(config.dimension, seed=config.random_seed)
    if config.state_family == "computational":
        return computational_basis_state(config.dimension, 0)
    if config.state_family == "fourier":
        return fourier_state(config.dimension, 0)
    raise ValueError(f"unsupported state_family: {config.state_family}")


def fixed_n_dimensions(n_physical: int) -> list[int]:
    """Generate fixed-physical-qubit experiment plans for fair dimension comparisons."""
    if n_physical < 1:
        raise ValueError("n_physical must be >= 1")
    if n_physical == 1:
        return [2]
    return list(range(2 ** (n_physical - 1), 2**n_physical + 1))


def fixed_n_sweep_configs(
    n_physical_values: Sequence[int],
    *,
    delay_dt_values: Sequence[int],
    state_family: str = "haar",
    random_seed: int = 7,
) -> list[SweepConfig]:
    """Generate fixed-physical-qubit experiment plans for fair dimension comparisons."""
    configs: list[SweepConfig] = []
    for n_physical in n_physical_values:
        for dimension in fixed_n_dimensions(n_physical):
            configs.append(
                SweepConfig(
                    dimension=dimension,
                    n_physical=n_physical,
                    delay_dt_values=list(delay_dt_values),
                    state_family=state_family,  # type: ignore[arg-type]
                    random_seed=random_seed,
                )
            )
    return configs


def _average_markovian_observables(
    dimension: int,
    *,
    n_physical: int | None = None,
    delay: float,
    t1: float | None = None,
    t2: float | None = None,
    t_dep: float | None = None,
    depolarizing_probability: float | None = None,
    bootstrap_samples: int = 0,
    confidence_level: float = 0.95,
    seed: int | None = None,
) -> dict[str, float]:
    """Average probe-state observables into a single fixed-n theory-lane record."""
    states = canonical_probe_states(dimension)
    values = [
        markovian_delay_observables(
            state,
            dimension,
            n_physical=n_physical,
            delay=delay,
            t1=t1,
            t2=t2,
            t_dep=t_dep,
            depolarizing_probability=depolarizing_probability,
        )
        for state in states
    ]
    summary = {
        "avg_probe_fidelity": float(np.mean([item["fidelity"] for item in values])),
        "avg_probe_leakage": float(np.mean([item["leakage"] for item in values])),
        "avg_probe_in_subspace_fidelity": float(
            np.mean([item["in_subspace_fidelity"] for item in values])
        ),
        "probe_ensemble_size": float(len(states)),
    }
    if bootstrap_samples > 0:
        summary.update(
            bootstrap_probe_mean_observables(
                values,
                bootstrap_samples=bootstrap_samples,
                confidence_level=confidence_level,
                seed=seed,
            )
        )
    return summary
    return summary


def run_markovian_fixed_n_sweep(
    configs: Sequence[SweepConfig],
    *,
    t1: float | None = None,
    t2: float | None = None,
    t_dep: float | None = None,
    depolarizing_probability: float | None = None,
    bootstrap_samples: int = 0,
    confidence_level: float = 0.95,
    dt_ns_per_dt: float | None = None,
    progress: ProgressCallback | None = None,
) -> list[dict[str, Any]]:
    """Run the phenomenological Markovian fixed-``n`` sweep.

    ``delay_dt_values`` are treated as theory-lane delay coordinates. They only inherit a
    physical meaning if the caller provides ``t1``, ``t2``, and ``t_dep`` in the same units.
    """
    records: list[dict[str, Any]] = []
    total = sum(len(sweep.delay_dt_values) for sweep in configs)
    completed = 0
    for sweep in configs:
        n_physical = resolved_n_physical(sweep.dimension, sweep.n_physical)
        for delay_dt in sweep.delay_dt_values:
            completed += 1
            _emit_progress(progress, f"markovian sweep {completed}/{total}: d={sweep.dimension}, n={n_physical}, delay_dt={delay_dt}")
            avg_observables = _average_markovian_observables(
                sweep.dimension,
                n_physical=n_physical,
                delay=float(delay_dt),
                t1=t1,
                t2=t2,
                t_dep=t_dep,
                depolarizing_probability=depolarizing_probability,
                bootstrap_samples=bootstrap_samples,
                confidence_level=confidence_level,
                seed=sweep.random_seed + completed,
            )
            records.append(
                {
                    "dimension": sweep.dimension,
                    "n_physical": n_physical,
                    "physical_hilbert_dimension": physical_hilbert_dimension_for_logical_dimension(
                        sweep.dimension, n_physical
                    ),
                    "fill_ratio": fill_ratio(sweep.dimension, n_physical),
                    "delay_dt": int(delay_dt),
                    "dt_ns": delay_dt_to_ns(delay_dt, dt_ns_per_dt=dt_ns_per_dt),
                    "shots": sweep.shots,
                    "state_family": "canonical_probe_average",
                    "simulation_lane": "markovian_model",
                    "t1": t1,
                    "t2": t2,
                    "t_dep": t_dep,
                    "depolarizing_probability": depolarizing_probability,
                    "fidelity": avg_observables["avg_probe_fidelity"],
                    "leakage": avg_observables["avg_probe_leakage"],
                    "in_subspace_fidelity": avg_observables["avg_probe_in_subspace_fidelity"],
                    **avg_observables,
                }
            )
    return records


def run_aer_fixed_n_sweep(
    configs: Sequence[SweepConfig],
    *,
    correction_mode: CorrectionMode = "dynamic",
    depolarizing_1q: float = 0.0,
    depolarizing_2q: float = 0.0,
    t1: float | None = None,
    t2: float | None = None,
    method: str = "automatic",
    bootstrap_samples: int = 0,
    confidence_level: float = 0.95,
    dt_ns_per_dt: float | None = None,
    seed_simulator: int = 17,
    progress: ProgressCallback | None = None,
) -> list[dict[str, Any]]:
    """Run fixed-``n`` sweeps through the full Aer teleportation circuit."""
    noise_model = build_basic_noise_model(
        depolarizing_1q=depolarizing_1q,
        depolarizing_2q=depolarizing_2q,
        t1=t1,
        t2=t2,
    )
    backend_config = BackendConfig(shots=max(int(cfg.shots) for cfg in configs), correction_mode=correction_mode)
    simulator = make_aer_simulator(method=method, noise_model=noise_model)
    resolved_dt_ns = resolved_aer_dt_ns_per_dt(dt_ns_per_dt)

    records: list[dict[str, Any]] = []
    total = sum(len(sweep.delay_dt_values) for sweep in configs)
    completed = 0
    for sweep in configs:
        canonical_states = canonical_probe_states(sweep.dimension)
        n_physical = resolved_n_physical(sweep.dimension, sweep.n_physical)
        for delay_dt in sweep.delay_dt_values:
            completed += 1
            _emit_progress(
                progress,
                f"aer circuit sweep {completed}/{total}: d={sweep.dimension}, n={n_physical}, delay_dt={delay_dt}",
            )
            probe_records: list[dict[str, Any]] = []
            probe_setting_counts: list[dict[str, dict[str, int]]] = []
            for probe_index, logical_state in enumerate(canonical_states):
                state_record, setting_counts, _ = _run_aer_tomography_for_state(
                    logical_state,
                    sweep.dimension,
                    n_physical=n_physical,
                    delay_dt=int(delay_dt),
                    backend_config=BackendConfig(
                        shots=sweep.shots,
                        correction_mode=correction_mode,
                        optimization_level=backend_config.optimization_level,
                    ),
                    simulator=simulator,
                    noise_model=noise_model,
                    seed_simulator=seed_simulator + 1000 * completed + probe_index,
                    dt_ns_per_dt=dt_ns_per_dt,
                    state_family="canonical_probe",
                )
                probe_records.append(state_record)
                probe_setting_counts.append(setting_counts)

            record = {
                "dimension": sweep.dimension,
                "n_physical": n_physical,
                "physical_hilbert_dimension": physical_hilbert_dimension_for_logical_dimension(
                    sweep.dimension, n_physical
                ),
                "fill_ratio": fill_ratio(sweep.dimension, n_physical),
                "delay_dt": int(delay_dt),
                "dt_ns": delay_dt_to_ns(delay_dt, dt_ns_per_dt=resolved_dt_ns),
                "shots": sweep.shots,
                "state_family": "canonical_probe_average",
                "simulation_lane": "aer_circuit",
                "backend_name": getattr(simulator, "name", type(simulator).__name__),
                "correction_mode": correction_mode,
                "depolarizing_1q": float(depolarizing_1q),
                "depolarizing_2q": float(depolarizing_2q),
                "t1": t1,
                "t2": t2,
                "fidelity": float(np.mean([item["fidelity"] for item in probe_records])),
                "leakage": float(np.mean([item["leakage"] for item in probe_records])),
                "in_subspace_fidelity": float(np.mean([item["in_subspace_fidelity"] for item in probe_records])),
                "avg_probe_fidelity": float(np.mean([item["fidelity"] for item in probe_records])),
                "avg_probe_leakage": float(np.mean([item["leakage"] for item in probe_records])),
                "avg_probe_in_subspace_fidelity": float(
                    np.mean([item["in_subspace_fidelity"] for item in probe_records])
                ),
                "probe_ensemble_size": float(len(canonical_states)),
            }
            if bootstrap_samples > 0:
                ci_summary = bootstrap_average_tomography_metrics(
                    canonical_states,
                    sweep.dimension,
                    probe_setting_counts,
                    n_physical=n_physical,
                    bootstrap_samples=bootstrap_samples,
                    confidence_level=confidence_level,
                    seed=seed_simulator + 50000 * completed,
                )
                record["observed_fidelity"] = record["fidelity"]
                record["observed_leakage"] = record["leakage"]
                record["observed_in_subspace_fidelity"] = record["in_subspace_fidelity"]
                record["observed_avg_probe_fidelity"] = record["avg_probe_fidelity"]
                record["observed_avg_probe_leakage"] = record["avg_probe_leakage"]
                record["observed_avg_probe_in_subspace_fidelity"] = record["avg_probe_in_subspace_fidelity"]
                record.update(ci_summary)
                record["fidelity"] = ci_summary["avg_probe_fidelity_bootstrap_mean"]
                record["leakage"] = ci_summary["avg_probe_leakage_bootstrap_mean"]
                record["in_subspace_fidelity"] = ci_summary["avg_probe_in_subspace_fidelity_bootstrap_mean"]
                record["avg_probe_fidelity"] = ci_summary["avg_probe_fidelity_bootstrap_mean"]
                record["avg_probe_leakage"] = ci_summary["avg_probe_leakage_bootstrap_mean"]
                record["avg_probe_in_subspace_fidelity"] = ci_summary["avg_probe_in_subspace_fidelity_bootstrap_mean"]
                record["fidelity_ci_low"] = ci_summary["avg_probe_fidelity_ci_low"]
                record["fidelity_ci_high"] = ci_summary["avg_probe_fidelity_ci_high"]
                record["leakage_ci_low"] = ci_summary["avg_probe_leakage_ci_low"]
                record["leakage_ci_high"] = ci_summary["avg_probe_leakage_ci_high"]
                record["in_subspace_fidelity_ci_low"] = ci_summary["avg_probe_in_subspace_fidelity_ci_low"]
                record["in_subspace_fidelity_ci_high"] = ci_summary["avg_probe_in_subspace_fidelity_ci_high"]
            records.append(record)
    return records


def run_correlated_memory_fixed_n_sweep(
    configs: Sequence[SweepConfig],
    *,
    steps: int,
    base_phase_flip_probability: float,
    memory_strength: float,
    samples: int = 2048,
    progress: ProgressCallback | None = None,
) -> list[dict[str, Any]]:
    """Run correlated memory fixed n sweep and return structured records for downstream analysis."""
    records: list[dict[str, Any]] = []
    total = len(configs)
    for index, sweep in enumerate(configs, start=1):
        _emit_progress(progress, f"correlated-memory sweep {index}/{total}: d={sweep.dimension}, n={resolved_n_physical(sweep.dimension, sweep.n_physical)}")
        state = make_probe_state(sweep)
        n_physical = resolved_n_physical(sweep.dimension, sweep.n_physical)
        observables = correlated_memory_observables(
            state,
            sweep.dimension,
            n_physical=n_physical,
            steps=steps,
            base_phase_flip_probability=base_phase_flip_probability,
            memory_strength=memory_strength,
            samples=samples,
            seed=sweep.random_seed,
        )
        for item in observables:
            records.append(
                {
                    "dimension": sweep.dimension,
                    "n_physical": n_physical,
                    "physical_hilbert_dimension": physical_hilbert_dimension_for_logical_dimension(
                        sweep.dimension, n_physical
                    ),
                    "fill_ratio": fill_ratio(sweep.dimension, n_physical),
                    "step": int(item["step"]),
                    "shots": sweep.shots,
                    "state_family": sweep.state_family,
                    "simulation_lane": "correlated_memory_model",
                    "memory_strength": float(memory_strength),
                    "base_phase_flip_probability": float(base_phase_flip_probability),
                    "samples": int(samples),
                    **item,
                }
            )
    return records


def run_blp_memory_scan(
    dimensions: Sequence[int],
    memory_strengths: Sequence[float],
    *,
    steps: int,
    base_phase_flip_probability: float,
    samples: int = 2048,
    seed: int = 7,
    progress: ProgressCallback | None = None,
) -> list[dict[str, Any]]:
    """Run blp memory scan and return structured records for downstream analysis."""
    records: list[dict[str, Any]] = []
    total = len(dimensions) * len(memory_strengths)
    completed = 0
    for dimension in dimensions:
        state_a = computational_basis_state(dimension, 0)
        state_b = fourier_state(dimension, 0)
        n_physical = num_physical_qubits_for_dimension(dimension)
        for memory_strength in memory_strengths:
            completed += 1
            _emit_progress(progress, f"blp scan {completed}/{total}: d={dimension}, memory_strength={float(memory_strength):.3f}")
            result = blp_non_markovianity(
                state_a,
                state_b,
                dimension,
                steps=steps,
                base_phase_flip_probability=base_phase_flip_probability,
                memory_strength=float(memory_strength),
                samples=samples,
                seed=seed,
            )
            records.append(
                {
                    "dimension": dimension,
                    "n_physical": n_physical,
                    "fill_ratio": fill_ratio(dimension),
                    "memory_strength": float(memory_strength),
                    "steps": int(steps),
                    "base_phase_flip_probability": float(base_phase_flip_probability),
                    "samples": int(samples),
                    **result,
                }
            )
    return records


def run_blp_random_telegraph_scan(
    dimensions: Sequence[int],
    switching_probabilities: Sequence[float],
    *,
    n_physical: int | None = None,
    steps: int,
    coupling_strength: float,
    dt: float = 1.0,
    samples: int = 2048,
    seed: int = 7,
    progress: ProgressCallback | None = None,
) -> list[dict[str, Any]]:
    """Run a calibrated BLP sweep for the random-telegraph dephasing model.

    The scan uses a Fourier-mode probe pair because phase-sensitive superpositions are the
    relevant states for dephasing-induced distinguishability backflow. ``switching_probability``
    is the discrete-time telegraph switching rate; ``dt`` and the derived correlation times
    are expressed in the same arbitrary units used by the theory lane.
    """
    records: list[dict[str, Any]] = []
    total = len(dimensions) * len(switching_probabilities)
    completed = 0
    for dimension in dimensions:
        state_a, state_b = random_telegraph_blp_probe_pair(dimension)
        resolved_n = resolved_n_physical(dimension, n_physical)
        for switching_probability in switching_probabilities:
            completed += 1
            probability = float(switching_probability)
            _emit_progress(
                progress,
                (
                    f"random-telegraph blp scan {completed}/{total}: "
                    f"d={dimension}, n={resolved_n}, p_switch={probability:.4f}"
                ),
            )
            result = blp_random_telegraph_non_markovianity(
                state_a,
                state_b,
                dimension,
                n_physical=resolved_n,
                steps=steps,
                coupling_strength=float(coupling_strength),
                switching_probability=probability,
                dt=dt,
                samples=samples,
                seed=seed,
            )
            correlation_time = switching_probability_to_correlation_time(probability, dt=dt)
            correlation_time_steps = (
                None if correlation_time is None or np.isclose(dt, 0.0) else float(correlation_time / float(dt))
            )
            records.append(
                {
                    "dimension": dimension,
                    "n_physical": resolved_n,
                    "fill_ratio": fill_ratio(dimension, resolved_n),
                    "switching_probability": probability,
                    "correlation_time_dt_units": correlation_time,
                    "correlation_time_steps": correlation_time_steps,
                    "dt_per_step": float(dt),
                    "steps": int(steps),
                    "coupling_strength": float(coupling_strength),
                    "samples": int(samples),
                    "probe_pair": "fourier_k0_vs_k1",
                    **result,
                }
            )
    return records


def _resolve_hardware_execution_dependencies() -> tuple:
    """Resolve the hardware-execution helpers explicitly and fail fast if they are unavailable."""
    required_names = (
        "select_backend",
        "validate_backend_for_experiment",
        "build_block_teleportation_circuit",
        "append_output_measurements",
        "transpile_isa",
        "run_sampler_job",
        "extract_register_counts",
        "extract_register_bitstrings",
        "corrected_counts_from_deferred_shots",
    )
    resolved = []
    missing = []
    global_ns = globals()
    for name in required_names:
        value = global_ns.get(name)
        if value is None:
            missing.append(name)
        else:
            resolved.append(value)
    if missing:
        joined = ", ".join(missing)
        raise RuntimeError(
            f"Hardware sweep dependencies are unavailable in the current module surface: {joined}"
        )
    return tuple(resolved)


def _collect_hardware_setting_counts_for_states(
    logical_states: Sequence[np.ndarray],
    dimension: int,
    *,
    n_physical: int,
    delay_dt: int,
    backend_config: BackendConfig,
    backend: Any,
    execution_dependencies: tuple,
) -> list[dict[str, dict[str, int]]]:
    """Acquire full tomography counts for one or more logical input states on hardware."""
    (
        _select_backend_fn,
        _validate_backend_for_experiment_fn,
        build_block_teleportation_circuit_fn,
        append_output_measurements_fn,
        transpile_isa_fn,
        run_sampler_job_fn,
        extract_register_counts_fn,
        extract_register_bitstrings_fn,
        corrected_counts_from_deferred_shots_fn,
    ) = execution_dependencies

    bases = all_measurement_bases(n_physical)
    tomo_circuits: list[Any] = []
    circuit_metadata: list[tuple[int, str]] = []
    for probe_index, logical_state in enumerate(logical_states):
        program = build_block_teleportation_circuit_fn(
            logical_state,
            dimension,
            n_physical=n_physical,
            delay_after_entanglement_dt=int(delay_dt),
            correction_mode=backend_config.correction_mode,
        )
        for basis in bases:
            tomo_circuits.append(append_output_measurements_fn(program, basis))
            circuit_metadata.append((probe_index, basis))

    isa_circuits = transpile_isa_fn(
        tomo_circuits,
        backend=backend,
        optimization_level=backend_config.optimization_level,
    )
    pub_results = run_sampler_job_fn(
        isa_circuits,
        backend=backend,
        shots=backend_config.shots,
        use_session=backend_config.use_session,
    )

    setting_counts_by_probe = [dict() for _ in logical_states]
    for (probe_index, basis), pub_result in zip(circuit_metadata, pub_results):
        reg_name = f"out_{basis}"
        if backend_config.correction_mode == "dynamic":
            setting_counts_by_probe[probe_index][basis] = extract_register_counts_fn(
                pub_result,
                reg_name,
            )
        else:
            output_shots = extract_register_bitstrings_fn(pub_result, reg_name)
            bell_shots = extract_register_bitstrings_fn(pub_result, "bell")
            setting_counts_by_probe[probe_index][basis] = corrected_counts_from_deferred_shots_fn(
                output_shots=output_shots,
                bell_shots=bell_shots,
                basis=basis,
            )
    return setting_counts_by_probe


def _hardware_state_metrics_from_setting_counts(
    logical_state: np.ndarray,
    dimension: int,
    setting_counts: dict[str, dict[str, int]],
    *,
    n_physical: int,
    delay_dt: int,
    dt_seconds: float | None,
    backend_name: str,
    backend_config: BackendConfig,
    state_family: str,
    simulation_lane: str = "ibm_runtime",
) -> tuple[dict[str, Any], np.ndarray]:
    """Reconstruct a hardware output state and compute the headline state metrics."""
    rho = reconstruct_density_matrix(setting_counts)
    embedded_target = embed_logical_state(logical_state, dimension, n_physical)
    record = {
        "dimension": dimension,
        "n_physical": n_physical,
        "physical_hilbert_dimension": physical_hilbert_dimension_for_logical_dimension(
            dimension, n_physical
        ),
        "fill_ratio": fill_ratio(dimension, n_physical),
        "delay_dt": int(delay_dt),
        "dt_ns": delay_dt_to_ns(delay_dt, dt_seconds=dt_seconds),
        "backend_name": backend_name,
        "fidelity": pure_state_fidelity(embedded_target, rho),
        "leakage": leakage_probability(rho, dimension, n_physical),
        "in_subspace_fidelity": in_subspace_fidelity(logical_state, rho, dimension, n_physical),
        "shots": backend_config.shots,
        "state_family": state_family,
        "correction_mode": backend_config.correction_mode,
        "simulation_lane": simulation_lane,
    }
    return record, rho


def run_hardware_delay_sweep(
    sweep: SweepConfig,
    backend_config: BackendConfig,
) -> list[dict]:
    """Run hardware delay sweep and return structured records for downstream analysis."""
    state = make_probe_state(sweep)
    n_physical = resolved_n_physical(sweep.dimension, sweep.n_physical)

    execution_dependencies = _resolve_hardware_execution_dependencies()
    (
        select_backend_fn,
        validate_backend_for_experiment_fn,
        *_rest,
    ) = execution_dependencies

    backend = select_backend_fn(backend_config)
    dt_seconds = backend_dt_seconds(backend)
    validate_backend_for_experiment_fn(
        backend,
        n_required_qubits=3 * n_physical,
        correction_mode=backend_config.correction_mode,
        require_delay=any(delay_dt > 0 for delay_dt in sweep.delay_dt_values),
    )

    results: list[dict] = []
    for delay_dt in sweep.delay_dt_values:
        setting_counts = _collect_hardware_setting_counts_for_states(
            [state],
            sweep.dimension,
            n_physical=n_physical,
            delay_dt=int(delay_dt),
            backend_config=backend_config,
            backend=backend,
            execution_dependencies=execution_dependencies,
        )[0]
        record, _rho = _hardware_state_metrics_from_setting_counts(
            state,
            sweep.dimension,
            setting_counts,
            n_physical=n_physical,
            delay_dt=int(delay_dt),
            dt_seconds=dt_seconds,
            backend_name=backend.name,
            backend_config=backend_config,
            state_family=sweep.state_family,
        )
        results.append(record)
    return results


def run_hardware_fixed_n_sweep(
    configs: Sequence[SweepConfig],
    backend_config: BackendConfig,
    *,
    bootstrap_samples: int = 0,
    confidence_level: float = 0.95,
    progress: ProgressCallback | None = None,
) -> list[dict[str, Any]]:
    """Run canonical-probe fixed-``n`` hardware sweeps on an IBM Runtime backend.

    For each logical dimension at a fixed physical-qubit count, the hardware lane prepares the
    canonical probe ensemble, performs full output-state tomography for every requested delay,
    and reports the average fidelity, leakage, and in-subspace fidelity across that ensemble.
    Optional multinomial bootstrapping is applied to the observed tomography counts rather than
    to a separate acquisition, so the point estimate and confidence interval are derived from the
    same live dataset.
    """
    if not configs:
        return []

    execution_dependencies = _resolve_hardware_execution_dependencies()
    (
        select_backend_fn,
        validate_backend_for_experiment_fn,
        *_rest,
    ) = execution_dependencies

    backend = select_backend_fn(backend_config)
    dt_seconds = backend_dt_seconds(backend)
    max_required_qubits = max(
        3 * resolved_n_physical(sweep.dimension, sweep.n_physical) for sweep in configs
    )
    validate_backend_for_experiment_fn(
        backend,
        n_required_qubits=max_required_qubits,
        correction_mode=backend_config.correction_mode,
        require_delay=any(delay_dt > 0 for sweep in configs for delay_dt in sweep.delay_dt_values),
    )

    results: list[dict[str, Any]] = []
    total = sum(len(sweep.delay_dt_values) for sweep in configs)
    completed = 0
    for sweep in configs:
        n_physical = resolved_n_physical(sweep.dimension, sweep.n_physical)
        bases = all_measurement_bases(n_physical)
        canonical_states = canonical_probe_states(sweep.dimension)
        for delay_dt in sweep.delay_dt_values:
            completed += 1
            _emit_progress(
                progress,
                (
                    f"hardware fixed-n sweep {completed}/{total}: "
                    f"d={sweep.dimension}, n={n_physical}, delay_dt={int(delay_dt)}"
                ),
            )

            setting_counts_by_probe = _collect_hardware_setting_counts_for_states(
                canonical_states,
                sweep.dimension,
                n_physical=n_physical,
                delay_dt=int(delay_dt),
                backend_config=backend_config,
                backend=backend,
                execution_dependencies=execution_dependencies,
            )

            probe_records: list[dict[str, float]] = []
            for logical_state, setting_counts in zip(canonical_states, setting_counts_by_probe):
                state_record, _rho = _hardware_state_metrics_from_setting_counts(
                    logical_state,
                    sweep.dimension,
                    setting_counts,
                    n_physical=n_physical,
                    delay_dt=int(delay_dt),
                    dt_seconds=dt_seconds,
                    backend_name=backend.name,
                    backend_config=backend_config,
                    state_family="canonical_probe",
                )
                probe_records.append(
                    {
                        "fidelity": float(state_record["fidelity"]),
                        "leakage": float(state_record["leakage"]),
                        "in_subspace_fidelity": float(state_record["in_subspace_fidelity"]),
                    }
                )

            record: dict[str, Any] = {
                "dimension": sweep.dimension,
                "n_physical": n_physical,
                "physical_hilbert_dimension": physical_hilbert_dimension_for_logical_dimension(
                    sweep.dimension, n_physical
                ),
                "fill_ratio": fill_ratio(sweep.dimension, n_physical),
                "delay_dt": int(delay_dt),
                "dt_ns": delay_dt_to_ns(delay_dt, dt_seconds=dt_seconds),
                "backend_name": backend.name,
                "shots": backend_config.shots,
                "state_family": "canonical_probe_average",
                "correction_mode": backend_config.correction_mode,
                "simulation_lane": "ibm_runtime",
                "probe_ensemble_size": float(len(canonical_states)),
                "fidelity": float(np.mean([item["fidelity"] for item in probe_records])),
                "leakage": float(np.mean([item["leakage"] for item in probe_records])),
                "in_subspace_fidelity": float(
                    np.mean([item["in_subspace_fidelity"] for item in probe_records])
                ),
                "avg_probe_fidelity": float(np.mean([item["fidelity"] for item in probe_records])),
                "avg_probe_leakage": float(np.mean([item["leakage"] for item in probe_records])),
                "avg_probe_in_subspace_fidelity": float(
                    np.mean([item["in_subspace_fidelity"] for item in probe_records])
                ),
            }
            if bootstrap_samples > 0:
                ci_summary = bootstrap_average_tomography_metrics(
                    canonical_states,
                    sweep.dimension,
                    setting_counts_by_probe,
                    n_physical=n_physical,
                    bootstrap_samples=bootstrap_samples,
                    confidence_level=confidence_level,
                    seed=sweep.random_seed + completed,
                )
                record["observed_fidelity"] = record["fidelity"]
                record["observed_leakage"] = record["leakage"]
                record["observed_in_subspace_fidelity"] = record["in_subspace_fidelity"]
                record["observed_avg_probe_fidelity"] = record["avg_probe_fidelity"]
                record["observed_avg_probe_leakage"] = record["avg_probe_leakage"]
                record["observed_avg_probe_in_subspace_fidelity"] = record["avg_probe_in_subspace_fidelity"]
                record.update(ci_summary)
                record["fidelity"] = ci_summary["avg_probe_fidelity_bootstrap_mean"]
                record["leakage"] = ci_summary["avg_probe_leakage_bootstrap_mean"]
                record["in_subspace_fidelity"] = ci_summary[
                    "avg_probe_in_subspace_fidelity_bootstrap_mean"
                ]
                record["avg_probe_fidelity"] = ci_summary["avg_probe_fidelity_bootstrap_mean"]
                record["avg_probe_leakage"] = ci_summary["avg_probe_leakage_bootstrap_mean"]
                record["avg_probe_in_subspace_fidelity"] = ci_summary[
                    "avg_probe_in_subspace_fidelity_bootstrap_mean"
                ]
                record["fidelity_ci_low"] = ci_summary["avg_probe_fidelity_ci_low"]
                record["fidelity_ci_high"] = ci_summary["avg_probe_fidelity_ci_high"]
                record["leakage_ci_low"] = ci_summary["avg_probe_leakage_ci_low"]
                record["leakage_ci_high"] = ci_summary["avg_probe_leakage_ci_high"]
                record["in_subspace_fidelity_ci_low"] = ci_summary[
                    "avg_probe_in_subspace_fidelity_ci_low"
                ]
                record["in_subspace_fidelity_ci_high"] = ci_summary[
                    "avg_probe_in_subspace_fidelity_ci_high"
                ]
            results.append(record)
    return results


def run_hardware_fixed_n_process_tomography(
    configs: Sequence[SweepConfig],
    backend_config: BackendConfig,
    *,
    bootstrap_samples: int = 0,
    confidence_level: float = 0.95,
    progress: ProgressCallback | None = None,
) -> list[dict[str, Any]]:
    """Run fixed-``n`` logical process tomography on IBM Runtime hardware."""
    if not configs:
        return []

    execution_dependencies = _resolve_hardware_execution_dependencies()
    (
        select_backend_fn,
        validate_backend_for_experiment_fn,
        *_rest,
    ) = execution_dependencies

    backend = select_backend_fn(backend_config)
    dt_seconds = backend_dt_seconds(backend)
    max_required_qubits = max(
        3 * resolved_n_physical(sweep.dimension, sweep.n_physical) for sweep in configs
    )
    validate_backend_for_experiment_fn(
        backend,
        n_required_qubits=max_required_qubits,
        correction_mode=backend_config.correction_mode,
        require_delay=any(delay_dt > 0 for sweep in configs for delay_dt in sweep.delay_dt_values),
    )

    results: list[dict[str, Any]] = []
    total = sum(len(sweep.delay_dt_values) for sweep in configs)
    completed = 0
    for sweep in configs:
        n_physical = resolved_n_physical(sweep.dimension, sweep.n_physical)
        input_states = process_tomography_probe_states(sweep.dimension)
        input_densities = [pure_state_density(state) for state in input_states]
        for delay_dt in sweep.delay_dt_values:
            completed += 1
            _emit_progress(
                progress,
                (
                    f"hardware process tomography {completed}/{total}: "
                    f"d={sweep.dimension}, n={n_physical}, delay_dt={int(delay_dt)}"
                ),
            )
            setting_counts_by_probe = _collect_hardware_setting_counts_for_states(
                input_states,
                sweep.dimension,
                n_physical=n_physical,
                delay_dt=int(delay_dt),
                backend_config=backend_config,
                backend=backend,
                execution_dependencies=execution_dependencies,
            )

            probe_records: list[dict[str, Any]] = []
            logical_outputs: list[np.ndarray] = []
            for logical_state, setting_counts in zip(input_states, setting_counts_by_probe):
                state_record, rho = _hardware_state_metrics_from_setting_counts(
                    logical_state,
                    sweep.dimension,
                    setting_counts,
                    n_physical=n_physical,
                    delay_dt=int(delay_dt),
                    dt_seconds=dt_seconds,
                    backend_name=backend.name,
                    backend_config=backend_config,
                    state_family="process_tomography_probe",
                    simulation_lane="ibm_runtime_process_tomography",
                )
                probe_records.append(state_record)
                logical_outputs.append(
                    renormalized_logical_subspace_density(rho, sweep.dimension, n_physical)
                )

            superoperator = reconstruct_superoperator(input_densities, logical_outputs)
            process_fidelity = process_fidelity_to_identity(superoperator, sweep.dimension)
            record: dict[str, Any] = {
                "dimension": sweep.dimension,
                "n_physical": n_physical,
                "physical_hilbert_dimension": physical_hilbert_dimension_for_logical_dimension(
                    sweep.dimension, n_physical
                ),
                "fill_ratio": fill_ratio(sweep.dimension, n_physical),
                "delay_dt": int(delay_dt),
                "dt_ns": delay_dt_to_ns(delay_dt, dt_seconds=dt_seconds),
                "backend_name": backend.name,
                "shots": backend_config.shots,
                "state_family": "process_tomography_probe",
                "correction_mode": backend_config.correction_mode,
                "simulation_lane": "ibm_runtime_process_tomography",
                "probe_ensemble_size": float(len(input_states)),
                "fidelity": float(np.mean([item["fidelity"] for item in probe_records])),
                "leakage": float(np.mean([item["leakage"] for item in probe_records])),
                "in_subspace_fidelity": float(
                    np.mean([item["in_subspace_fidelity"] for item in probe_records])
                ),
                "avg_probe_fidelity": float(np.mean([item["fidelity"] for item in probe_records])),
                "avg_probe_leakage": float(np.mean([item["leakage"] for item in probe_records])),
                "avg_probe_in_subspace_fidelity": float(
                    np.mean([item["in_subspace_fidelity"] for item in probe_records])
                ),
                "process_fidelity": process_fidelity,
                "average_gate_fidelity": average_gate_fidelity_from_process_fidelity(
                    process_fidelity, sweep.dimension
                ),
            }
            if bootstrap_samples > 0:
                avg_ci_summary = bootstrap_average_tomography_metrics(
                    input_states,
                    sweep.dimension,
                    setting_counts_by_probe,
                    n_physical=n_physical,
                    bootstrap_samples=bootstrap_samples,
                    confidence_level=confidence_level,
                    seed=sweep.random_seed + 10000 * completed,
                )
                record["observed_fidelity"] = record["fidelity"]
                record["observed_leakage"] = record["leakage"]
                record["observed_in_subspace_fidelity"] = record["in_subspace_fidelity"]
                record["observed_avg_probe_fidelity"] = record["avg_probe_fidelity"]
                record["observed_avg_probe_leakage"] = record["avg_probe_leakage"]
                record["observed_avg_probe_in_subspace_fidelity"] = record[
                    "avg_probe_in_subspace_fidelity"
                ]
                record.update(avg_ci_summary)
                record["fidelity"] = avg_ci_summary["avg_probe_fidelity_bootstrap_mean"]
                record["leakage"] = avg_ci_summary["avg_probe_leakage_bootstrap_mean"]
                record["in_subspace_fidelity"] = avg_ci_summary[
                    "avg_probe_in_subspace_fidelity_bootstrap_mean"
                ]
                record["avg_probe_fidelity"] = avg_ci_summary["avg_probe_fidelity_bootstrap_mean"]
                record["avg_probe_leakage"] = avg_ci_summary["avg_probe_leakage_bootstrap_mean"]
                record["avg_probe_in_subspace_fidelity"] = avg_ci_summary[
                    "avg_probe_in_subspace_fidelity_bootstrap_mean"
                ]
                record["fidelity_ci_low"] = avg_ci_summary["avg_probe_fidelity_ci_low"]
                record["fidelity_ci_high"] = avg_ci_summary["avg_probe_fidelity_ci_high"]
                record["leakage_ci_low"] = avg_ci_summary["avg_probe_leakage_ci_low"]
                record["leakage_ci_high"] = avg_ci_summary["avg_probe_leakage_ci_high"]
                record["in_subspace_fidelity_ci_low"] = avg_ci_summary[
                    "avg_probe_in_subspace_fidelity_ci_low"
                ]
                record["in_subspace_fidelity_ci_high"] = avg_ci_summary[
                    "avg_probe_in_subspace_fidelity_ci_high"
                ]
                process_ci_summary = bootstrap_process_tomography_metrics(
                    sweep.dimension,
                    input_states,
                    setting_counts_by_probe,
                    n_physical=n_physical,
                    bootstrap_samples=bootstrap_samples,
                    confidence_level=confidence_level,
                    seed=sweep.random_seed + 20000 * completed,
                )
                record["observed_process_fidelity"] = record["process_fidelity"]
                record["observed_average_gate_fidelity"] = record["average_gate_fidelity"]
                record.update(process_ci_summary)
                record["process_fidelity"] = process_ci_summary["process_fidelity_bootstrap_mean"]
                record["average_gate_fidelity"] = process_ci_summary[
                    "average_gate_fidelity_bootstrap_mean"
                ]
            results.append(record)
    return results


def run_hardware_process_tomography(
    sweep: SweepConfig,
    backend_config: BackendConfig,
    *,
    bootstrap_samples: int = 0,
    confidence_level: float = 0.95,
    progress: ProgressCallback | None = None,
) -> list[dict[str, Any]]:
    """Run logical process tomography on IBM Runtime hardware for one dimension sweep."""
    return run_hardware_fixed_n_process_tomography(
        [sweep],
        backend_config,
        bootstrap_samples=bootstrap_samples,
        confidence_level=confidence_level,
        progress=progress,
    )


def summarize_results(records: list[dict]) -> str:
    """Build or parse structured comparison summaries for fixed-n analysis reports."""
    if not records:
        return "No records."
    lines = []
    for rec in records:
        if "delay_dt" in rec and rec.get("dt_ns") is not None:
            x_label = f"delay_dt={rec['delay_dt']} ({float(rec['dt_ns']):.3f} ns)"
        elif "delay_dt" in rec:
            x_label = f"delay_dt={rec['delay_dt']}"
        else:
            x_label = f"step={rec.get('step', '?')}"
        parts = [
            f"d={rec['dimension']}",
            f"n={rec['n_physical']}",
            f"phi={rec['fill_ratio']:.3f}",
            x_label,
            f"F={rec['fidelity']:.6f}",
            f"L={rec['leakage']:.6f}",
            f"F_sub={rec['in_subspace_fidelity']:.6f}",
        ]
        if "process_fidelity" in rec:
            parts.append(f"F_proc={float(rec['process_fidelity']):.6f}")
        if "average_gate_fidelity" in rec:
            parts.append(f"F_avg={float(rec['average_gate_fidelity']):.6f}")
        parts.append(f"lane={rec.get('simulation_lane', 'unknown')}")
        lines.append(" | ".join(parts))
    return "\n".join(lines)

# === END sweeps.py ===

# === BEGIN cli.py ===

import json

import typer


app = typer.Typer(no_args_is_help=True)



def _echo_records_or_paths(records: list[dict[str, Any]], *, output_stem: str | None = None, plot_delay: bool = True) -> None:
    """Utility function used by the monolithic teleportation experiment toolkit."""
    typer.echo(summarize_results(records), err=True)
    if output_stem is None:
        typer.echo(json.dumps(records, indent=2))
        return
    save_json(records, f"{output_stem}.json")
    save_csv(records, f"{output_stem}.csv")
    if plot_delay:
        plot_metric_vs_delay(records, metric="fidelity", path=f"{output_stem}_fidelity.png")
        plot_metric_vs_delay(records, metric="leakage", path=f"{output_stem}_leakage.png")


@app.command()
def hardware_delay_sweep(
    dimension: int = typer.Option(..., help="Logical Hilbert-space dimension."),
    n_physical: int | None = typer.Option(None, help="Optional explicit physical qubit count for fixed-n hardware comparisons."),
    backend_name: str | None = typer.Option(None, help="IBM backend name."),
    shots: int = typer.Option(2048, help="Number of shots per tomography setting."),
    correction_mode: str = typer.Option("dynamic", help="dynamic or deferred."),
    delays: str = typer.Option("0,64,128", help="Comma-separated delay values in dt units."),
    output_stem: str | None = typer.Option(None, help="Optional file stem for json/csv/plots."),
) -> None:
    """Typer CLI command for the monolithic teleportation experiment toolkit."""
    sweep = SweepConfig(
        dimension=dimension,
        n_physical=n_physical,
        delay_dt_values=[int(x.strip()) for x in delays.split(",") if x.strip()],
        shots=shots,
    )
    backend = BackendConfig(
        backend_name=backend_name,
        shots=shots,
        correction_mode=correction_mode,  # type: ignore[arg-type]
    )
    records = run_hardware_delay_sweep(sweep, backend)
    _echo_records_or_paths(records, output_stem=output_stem)


@app.command()
def hardware_fixed_n_sweep(
    n_values: str = typer.Option("2", help="Comma-separated fixed physical-qubit counts."),
    backend_name: str | None = typer.Option(None, help="IBM backend name."),
    shots: int = typer.Option(2048, help="Number of shots per tomography setting."),
    correction_mode: str = typer.Option("dynamic", help="dynamic or deferred."),
    delays: str = typer.Option("0,64,128", help="Comma-separated delay values in dt units."),
    bootstrap_samples: int = typer.Option(0, help="Optional number of bootstrap resamples for tomography confidence intervals."),
    confidence_level: float = typer.Option(0.95, help="Confidence level for bootstrap intervals."),
    output_stem: str | None = typer.Option(None, help="Optional file stem for json/csv/plots."),
) -> None:
    """Run a fixed-``n`` canonical-probe hardware sweep for d=2..2^n on IBM Runtime."""
    configs = fixed_n_sweep_configs(
        [int(x.strip()) for x in n_values.split(",") if x.strip()],
        delay_dt_values=[int(x.strip()) for x in delays.split(",") if x.strip()],
    )
    backend = BackendConfig(
        backend_name=backend_name,
        shots=shots,
        correction_mode=correction_mode,  # type: ignore[arg-type]
    )
    records = run_hardware_fixed_n_sweep(
        configs,
        backend,
        bootstrap_samples=bootstrap_samples,
        confidence_level=confidence_level,
        progress=lambda message: typer.echo(message, err=True),
    )
    _echo_records_or_paths(records, output_stem=output_stem)


@app.command()
def hardware_process_tomography(
    dimension: int = typer.Option(..., help="Logical Hilbert-space dimension."),
    n_physical: int | None = typer.Option(None, help="Optional explicit physical qubit count for fixed-n embeddings."),
    backend_name: str | None = typer.Option(None, help="IBM backend name."),
    shots: int = typer.Option(2048, help="Number of shots per tomography setting."),
    correction_mode: str = typer.Option("dynamic", help="dynamic or deferred."),
    delays: str = typer.Option("0,64,128", help="Comma-separated delay values in dt units."),
    bootstrap_samples: int = typer.Option(0, help="Optional number of bootstrap resamples for CIs."),
    confidence_level: float = typer.Option(0.95, help="Confidence level for bootstrap intervals."),
    output_stem: str | None = typer.Option(None, help="Optional file stem for json/csv/plots."),
) -> None:
    """Run logical process tomography on IBM Runtime hardware."""
    sweep = SweepConfig(
        dimension=dimension,
        n_physical=n_physical,
        delay_dt_values=[int(x.strip()) for x in delays.split(",") if x.strip()],
        shots=shots,
    )
    backend = BackendConfig(
        backend_name=backend_name,
        shots=shots,
        correction_mode=correction_mode,  # type: ignore[arg-type]
    )
    records = run_hardware_process_tomography(
        sweep,
        backend,
        bootstrap_samples=bootstrap_samples,
        confidence_level=confidence_level,
        progress=lambda msg: typer.echo(msg, err=True),
    )
    _echo_records_or_paths(records, output_stem=output_stem)
    if output_stem:
        plot_metric_vs_delay(
            records,
            metric="process_fidelity",
            path=f"{output_stem}_process_fidelity.png",
        )


@app.command()
def hardware_fixed_n_process_tomography(
    n_values: str = typer.Option("2", help="Comma-separated fixed physical-qubit counts."),
    backend_name: str | None = typer.Option(None, help="IBM backend name."),
    shots: int = typer.Option(2048, help="Number of shots per tomography setting."),
    correction_mode: str = typer.Option("dynamic", help="dynamic or deferred."),
    delays: str = typer.Option("0,64,128", help="Comma-separated delay values in dt units."),
    bootstrap_samples: int = typer.Option(0, help="Optional number of bootstrap resamples for CIs."),
    confidence_level: float = typer.Option(0.95, help="Confidence level for bootstrap intervals."),
    output_stem: str | None = typer.Option(None, help="Optional file stem for json/csv/plots."),
) -> None:
    """Run fixed-``n`` logical process tomography on IBM Runtime hardware."""
    configs = fixed_n_sweep_configs(
        [int(x.strip()) for x in n_values.split(",") if x.strip()],
        delay_dt_values=[int(x.strip()) for x in delays.split(",") if x.strip()],
    )
    backend = BackendConfig(
        backend_name=backend_name,
        shots=shots,
        correction_mode=correction_mode,  # type: ignore[arg-type]
    )
    records = run_hardware_fixed_n_process_tomography(
        configs,
        backend,
        bootstrap_samples=bootstrap_samples,
        confidence_level=confidence_level,
        progress=lambda msg: typer.echo(msg, err=True),
    )
    _echo_records_or_paths(records, output_stem=output_stem)
    if output_stem:
        plot_metric_vs_delay(
            records,
            metric="process_fidelity",
            path=f"{output_stem}_process_fidelity.png",
        )


@app.command()
def aer_delay_sweep(
    dimension: int = typer.Option(..., help="Logical Hilbert-space dimension."),
    shots: int = typer.Option(2048, help="Number of shots per tomography setting."),
    correction_mode: str = typer.Option("dynamic", help="dynamic or deferred."),
    delays: str = typer.Option("0,64,128", help="Comma-separated delay values in dt units."),
    depolarizing_1q: float = typer.Option(0.0),
    depolarizing_2q: float = typer.Option(0.0),
    t1: float | None = typer.Option(DEFAULT_AER_T1_SECONDS),
    t2: float | None = typer.Option(DEFAULT_AER_T2_SECONDS),
    method: str = typer.Option("automatic"),
    bootstrap_samples: int = typer.Option(0, help="Optional number of bootstrap resamples for 95% CIs."),
    confidence_level: float = typer.Option(0.95, help="Confidence level for bootstrap intervals."),
    dt_ns_per_dt: float | None = typer.Option(DEFAULT_AER_DT_NS_PER_DT, help="Nanoseconds per backend dt tick used for delay calibration."),
    output_stem: str | None = typer.Option(None),
) -> None:
    """Aer simulation helper for local noisy validation of encoded teleportation circuits."""
    sweep = SweepConfig(
        dimension=dimension,
        delay_dt_values=[int(x.strip()) for x in delays.split(",") if x.strip()],
        shots=shots,
    )
    backend = BackendConfig(
        shots=shots,
        correction_mode=correction_mode,  # type: ignore[arg-type]
    )
    try:
        noise_model = build_basic_noise_model(
            depolarizing_1q=depolarizing_1q,
            depolarizing_2q=depolarizing_2q,
            t1=t1,
            t2=t2,
        )
        records = run_aer_delay_sweep(
            sweep,
            backend,
            noise_model=noise_model,
            method=method,
            bootstrap_samples=bootstrap_samples,
            confidence_level=confidence_level,
            dt_ns_per_dt=dt_ns_per_dt,
        )
    except AerExecutionError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1)
    _echo_records_or_paths(records, output_stem=output_stem)


@app.command()
def fixed_n_plan(
    n_values: str = typer.Option("1,2,3", help="Comma-separated physical-qubit counts."),
    delays: str = typer.Option("0,64,128", help="Comma-separated delay values in dt units."),
) -> None:
    """Generate fixed-physical-qubit experiment plans for fair dimension comparisons."""
    configs = fixed_n_sweep_configs(
        [int(x.strip()) for x in n_values.split(",") if x.strip()],
        delay_dt_values=[int(x.strip()) for x in delays.split(",") if x.strip()],
    )
    typer.echo(
        json.dumps(
            [
                {
                    "dimension": cfg.dimension,
                    "n_physical": cfg.n_physical,
                    "delay_dt_values": list(cfg.delay_dt_values),
                    "state_family": cfg.state_family,
                }
                for cfg in configs
            ],
            indent=2,
        )
    )


@app.command()
def markovian_model(
    dimension: int = typer.Option(...),
    delay: float = typer.Option(...),
    t1: float | None = typer.Option(None),
    t2: float | None = typer.Option(None),
    t_dep: float | None = typer.Option(None),
    depolarizing_probability: float | None = typer.Option(None),
    seed: int = typer.Option(7),
) -> None:
    """Evaluate the Markovian effective-noise model for a given delay and encoded dimension."""
    state = random_haar_state(dimension, seed=seed)
    observables = markovian_delay_observables(
        state,
        dimension,
        delay=delay,
        t1=t1,
        t2=t2,
        t_dep=t_dep,
        depolarizing_probability=depolarizing_probability,
    )
    typer.echo(json.dumps(observables, indent=2))


@app.command()
def correlated_memory_model(
    dimension: int = typer.Option(...),
    steps: int = typer.Option(8),
    probability: float = typer.Option(0.02),
    memory_strength: float = typer.Option(0.8),
    samples: int = typer.Option(1024),
    seed: int = typer.Option(7),
) -> None:
    """Evaluate the correlated-memory effective model used as the non-Markovian lane."""
    state = random_haar_state(dimension, seed=seed)
    observables = correlated_memory_observables(
        state,
        dimension,
        steps=steps,
        base_phase_flip_probability=probability,
        memory_strength=memory_strength,
        samples=samples,
        seed=seed,
    )
    typer.echo(json.dumps(observables, indent=2))


@app.command()
def blp_scan(
    dimension: int = typer.Option(...),
    steps: int = typer.Option(8),
    probability: float = typer.Option(0.02),
    memory_strength: float = typer.Option(0.8),
    samples: int = typer.Option(1024),
    seed: int = typer.Option(7),
) -> None:
    """Typer CLI command for the monolithic teleportation experiment toolkit."""
    state_a = computational_basis_state(dimension, 0)
    state_b = fourier_state(dimension, 0)
    result = blp_non_markovianity(
        state_a,
        state_b,
        dimension,
        steps=steps,
        base_phase_flip_probability=probability,
        memory_strength=memory_strength,
        samples=samples,
        seed=seed,
    )
    typer.echo(json.dumps(result, indent=2))


@app.command()
def markovian_fixed_n_sweep(
    n_values: str = typer.Option("1,2,3", help="Comma-separated physical-qubit counts."),
    delays: str = typer.Option("0,64,128", help="Comma-separated delay values in dt units."),
    t1: float | None = typer.Option(None),
    t2: float | None = typer.Option(None),
    t_dep: float | None = typer.Option(None),
    depolarizing_probability: float | None = typer.Option(None),
    bootstrap_samples: int = typer.Option(0, help="Optional probe-resampling bootstrap count for confidence intervals."),
    confidence_level: float = typer.Option(0.95, help="Confidence level for bootstrap intervals."),
    dt_ns_per_dt: float | None = typer.Option(DEFAULT_AER_DT_NS_PER_DT, help="Nanoseconds per delay_dt unit used for plotting and export."),
    output_stem: str | None = typer.Option(None, help="Optional file stem for json/csv/plots."),
) -> None:
    """Evaluate the Markovian effective-noise model for a given delay and encoded dimension."""
    configs = fixed_n_sweep_configs(
        [int(x.strip()) for x in n_values.split(",") if x.strip()],
        delay_dt_values=[int(x.strip()) for x in delays.split(",") if x.strip()],
    )
    records = run_markovian_fixed_n_sweep(
        configs,
        t1=t1,
        t2=t2,
        t_dep=t_dep,
        depolarizing_probability=depolarizing_probability,
        bootstrap_samples=bootstrap_samples,
        confidence_level=confidence_level,
        dt_ns_per_dt=dt_ns_per_dt,
        progress=lambda msg: typer.echo(msg, err=True),
    )
    _echo_records_or_paths(records, output_stem=output_stem)
    if output_stem:
        plot_metric_vs_fill_ratio(records, metric="fidelity", path=f"{output_stem}_phi_fidelity.png")


@app.command()
def aer_fixed_n_sweep(
    n_values: str = typer.Option("1,2,3", help="Comma-separated physical-qubit counts."),
    delays: str = typer.Option("0,64,128", help="Comma-separated delay values in dt units."),
    shots: int = typer.Option(2048, help="Number of shots per tomography setting."),
    correction_mode: str = typer.Option("dynamic", help="dynamic or deferred."),
    depolarizing_1q: float = typer.Option(0.0),
    depolarizing_2q: float = typer.Option(0.0),
    t1: float | None = typer.Option(DEFAULT_AER_T1_SECONDS),
    t2: float | None = typer.Option(DEFAULT_AER_T2_SECONDS),
    method: str = typer.Option("automatic"),
    bootstrap_samples: int = typer.Option(0, help="Optional number of bootstrap resamples for CIs."),
    confidence_level: float = typer.Option(0.95, help="Confidence level for bootstrap intervals."),
    dt_ns_per_dt: float | None = typer.Option(DEFAULT_AER_DT_NS_PER_DT, help="Nanoseconds per backend dt tick used for delay calibration."),
    output_stem: str | None = typer.Option(None, help="Optional file stem for json/csv/plots."),
) -> None:
    """Run the full Aer teleportation circuit for fixed-n sweeps."""
    configs = fixed_n_sweep_configs(
        [int(x.strip()) for x in n_values.split(",") if x.strip()],
        delay_dt_values=[int(x.strip()) for x in delays.split(",") if x.strip()],
    )
    for config in configs:
        config.shots = shots
    records = run_aer_fixed_n_sweep(
        configs,
        correction_mode=correction_mode,  # type: ignore[arg-type]
        depolarizing_1q=depolarizing_1q,
        depolarizing_2q=depolarizing_2q,
        t1=t1,
        t2=t2,
        method=method,
        bootstrap_samples=bootstrap_samples,
        confidence_level=confidence_level,
        dt_ns_per_dt=dt_ns_per_dt,
        progress=lambda msg: typer.echo(msg, err=True),
    )
    _echo_records_or_paths(records, output_stem=output_stem)
    if output_stem:
        plot_metric_vs_fill_ratio(records, metric="fidelity", path=f"{output_stem}_phi_fidelity.png")


@app.command()
def correlated_memory_fixed_n_sweep(
    n_values: str = typer.Option("1,2,3", help="Comma-separated physical-qubit counts."),
    steps: int = typer.Option(8),
    probability: float = typer.Option(0.02),
    memory_strength: float = typer.Option(0.8),
    samples: int = typer.Option(1024),
    output_stem: str | None = typer.Option(None),
) -> None:
    """Evaluate the correlated-memory effective model used as the non-Markovian lane."""
    configs = fixed_n_sweep_configs(
        [int(x.strip()) for x in n_values.split(",") if x.strip()],
        delay_dt_values=[0],
    )
    records = run_correlated_memory_fixed_n_sweep(
        configs,
        steps=steps,
        base_phase_flip_probability=probability,
        memory_strength=memory_strength,
        samples=samples,
        progress=lambda msg: typer.echo(msg, err=True),
    )
    _echo_records_or_paths(records, output_stem=output_stem)


@app.command()
def blp_memory_scan(
    dimensions: str = typer.Option("2,3,4", help="Comma-separated logical dimensions."),
    memory_strengths: str = typer.Option("0.0,0.2,0.4,0.6,0.8,1.0"),
    steps: int = typer.Option(8),
    probability: float = typer.Option(0.02),
    samples: int = typer.Option(1024),
    output_stem: str | None = typer.Option(None),
) -> None:
    """Typer CLI command for the monolithic teleportation experiment toolkit."""
    records = run_blp_memory_scan(
        [int(x.strip()) for x in dimensions.split(",") if x.strip()],
        [float(x.strip()) for x in memory_strengths.split(",") if x.strip()],
        steps=steps,
        base_phase_flip_probability=probability,
        samples=samples,
        progress=lambda msg: typer.echo(msg, err=True),
    )
    if output_stem:
        save_json(records, f"{output_stem}.json")
        save_csv(records, f"{output_stem}.csv")
        plot_blp_vs_memory_strength(records, path=f"{output_stem}_blp.png")
    typer.echo(json.dumps(records, indent=2))


@app.command()
def blp_random_telegraph_scan(
    dimensions: str = typer.Option("2,3,4", help="Comma-separated logical dimensions."),
    n_physical: int | None = typer.Option(None, help="Optional fixed physical qubit count for fair fill-ratio comparisons."),
    switching_probabilities: str = typer.Option("0.005,0.0125,0.025,0.05,0.1,0.2"),
    coupling_strength: float = typer.Option(0.4),
    steps: int = typer.Option(16),
    dt: float = typer.Option(1.0, help="Theory-lane time step used in the telegraph update rule."),
    samples: int = typer.Option(2048),
    output_stem: str | None = typer.Option(None),
) -> None:
    """Run a calibrated BLP sweep for the random-telegraph dephasing model."""
    records = run_blp_random_telegraph_scan(
        [int(x.strip()) for x in dimensions.split(",") if x.strip()],
        [float(x.strip()) for x in switching_probabilities.split(",") if x.strip()],
        n_physical=n_physical,
        steps=steps,
        coupling_strength=coupling_strength,
        dt=dt,
        samples=samples,
        progress=lambda msg: typer.echo(msg, err=True),
    )
    if output_stem:
        save_json(records, f"{output_stem}.json")
        save_csv(records, f"{output_stem}.csv")
        save_blp_markdown_report(records, path=f"{output_stem}.md", title="Random-telegraph BLP scan")
        plot_blp_vs_switching_probability(records, path=f"{output_stem}_blp.png")
    typer.echo(json.dumps(records, indent=2))


@app.command()
def calibrate_random_telegraph(
    input_json: str = typer.Option(..., help="JSON record file with dt_ns-calibrated delay records."),
    dimension: int = typer.Option(..., help="Logical dimension to calibrate against."),
    n_physical: int | None = typer.Option(None, help="Optional physical qubit count filter."),
    metric: str = typer.Option("process_fidelity", help="Calibration metric: process_fidelity, average_gate_fidelity, in_subspace_fidelity, or fidelity."),
    dt_ns_per_step: float = typer.Option(..., help="Nanoseconds represented by one telegraph update step / backend delay tick."),
    fit_mode: str = typer.Option("first_nonzero", help="first_nonzero or regression."),
    output_stem: str | None = typer.Option(None, help="Optional file stem for json/markdown outputs."),
) -> None:
    """Calibrate a random-telegraph switching rate from backend or Aer delay data."""
    records = load_json_records(input_json)
    calibration = calibrate_random_telegraph_from_records(
        records,
        dimension=dimension,
        n_physical=n_physical,
        metric=metric,
        dt_ns_per_step=dt_ns_per_step,
        fit_mode=fit_mode,
    )
    if output_stem:
        json_path = _normalize_path(f"{output_stem}.json")
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(calibration, indent=2) + "\n")
        save_random_telegraph_calibration_markdown_report(
            calibration,
            path=f"{output_stem}.md",
        )
    typer.echo(json.dumps(calibration, indent=2))


@app.command()
def aer_process_tomography(
    dimension: int = typer.Option(..., help="Logical Hilbert-space dimension."),
    n_physical: int | None = typer.Option(None, help="Optional explicit physical qubit count for fixed-n embeddings."),
    shots: int = typer.Option(2048, help="Number of shots per tomography setting."),
    correction_mode: str = typer.Option("dynamic", help="dynamic or deferred."),
    delays: str = typer.Option("0,64,128", help="Comma-separated delay values in dt units."),
    depolarizing_1q: float = typer.Option(0.0),
    depolarizing_2q: float = typer.Option(0.0),
    t1: float | None = typer.Option(DEFAULT_AER_T1_SECONDS),
    t2: float | None = typer.Option(DEFAULT_AER_T2_SECONDS),
    method: str = typer.Option("automatic"),
    bootstrap_samples: int = typer.Option(0, help="Optional number of bootstrap resamples for CIs."),
    confidence_level: float = typer.Option(0.95, help="Confidence level for bootstrap intervals."),
    dt_ns_per_dt: float | None = typer.Option(DEFAULT_AER_DT_NS_PER_DT, help="Nanoseconds per backend dt tick used for delay calibration."),
    output_stem: str | None = typer.Option(None),
) -> None:
    """Run logical process tomography on the Aer teleportation circuit."""
    sweep = SweepConfig(
        dimension=dimension,
        n_physical=n_physical,
        delay_dt_values=[int(x.strip()) for x in delays.split(",") if x.strip()],
        shots=shots,
    )
    backend = BackendConfig(
        shots=shots,
        correction_mode=correction_mode,  # type: ignore[arg-type]
    )
    try:
        noise_model = build_basic_noise_model(
            depolarizing_1q=depolarizing_1q,
            depolarizing_2q=depolarizing_2q,
            t1=t1,
            t2=t2,
        )
        records = run_aer_process_tomography(
            sweep,
            backend,
            noise_model=noise_model,
            method=method,
            bootstrap_samples=bootstrap_samples,
            confidence_level=confidence_level,
            dt_ns_per_dt=dt_ns_per_dt,
        )
    except AerExecutionError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1)
    typer.echo(summarize_results(records), err=True)
    if output_stem:
        save_json(records, f"{output_stem}.json")
        save_csv(records, f"{output_stem}.csv")
        plot_metric_vs_delay(records, metric="process_fidelity", path=f"{output_stem}_process_fidelity.png")
        plot_metric_vs_delay(
            records,
            metric="average_gate_fidelity",
            path=f"{output_stem}_average_gate_fidelity.png",
        )
    typer.echo(json.dumps(records, indent=2))


@app.command()
def compare_fixed_n(
    input_json: str = typer.Option(..., help="Path to one JSON records file, or a comma-separated list of JSON files."),
    n_physical: int = typer.Option(..., help="Physical qubit count to compare."),
    dt_ns_per_dt: float | None = typer.Option(None, help="Optional nanoseconds per delay_dt step when records do not already include dt_ns."),
    output_stem: str | None = typer.Option(None),
) -> None:
    """Typer CLI command for the monolithic teleportation experiment toolkit."""
    input_paths = [item.strip() for item in input_json.split(",") if item.strip()]
    records: list[dict[str, Any]] = []
    for path in input_paths:
        records.extend(load_json_records(path))
    summary = summarize_fixed_n_comparison(records, n_physical=n_physical, dt_ns_per_dt=dt_ns_per_dt)
    if output_stem:
        save_json(summary, f"{output_stem}.json")
        save_csv(summary, f"{output_stem}.csv")
        save_fixed_n_markdown_report(summary, path=f"{output_stem}.md")
    typer.echo(json.dumps(summary, indent=2))


@app.command()
def compare_three_lanes(
    theory_json: str = typer.Option(..., help="Path to one theory-lane compare JSON file, or a comma-separated list of theory summary/raw JSON files."),
    aer_json: str = typer.Option(..., help="Path to one Aer-lane compare JSON file, or a comma-separated list of Aer summary/raw JSON files."),
    hardware_json: str = typer.Option(..., help="Path to one hardware-lane compare JSON file, or a comma-separated list of hardware state/process summary JSON files."),
    n_physical: int = typer.Option(..., help="Physical qubit count to compare."),
    title: str = typer.Option("Three-lane fixed-n comparison", help="Markdown report title."),
    output_stem: str | None = typer.Option(None),
) -> None:
    """Build one report that places theory, Aer, and hardware fixed-n results side by side."""
    lane_summaries = {
        "theory": load_fixed_n_summary_rows(
            [item.strip() for item in theory_json.split(",") if item.strip()],
            n_physical=n_physical,
        ),
        "aer": load_fixed_n_summary_rows(
            [item.strip() for item in aer_json.split(",") if item.strip()],
            n_physical=n_physical,
        ),
        "hardware": load_fixed_n_summary_rows(
            [item.strip() for item in hardware_json.split(",") if item.strip()],
            n_physical=n_physical,
        ),
    }
    rows = summarize_three_lane_fixed_n_table(lane_summaries)
    if output_stem:
        save_json(rows, f"{output_stem}.json")
        save_csv(rows, f"{output_stem}.csv")
        save_three_lane_fixed_n_markdown_report(rows, path=f"{output_stem}.md", title=title)
    typer.echo(json.dumps(rows, indent=2))


@app.command()
def plot_records(
    input_json: str = typer.Option(..., help="Path to JSON records file."),
    metric: str = typer.Option("fidelity"),
    mode: str = typer.Option("delay", help="delay, fill_ratio, or blp"),
    output_path: str = typer.Option(...),
    delay_dt: int | None = typer.Option(None),
) -> None:
    """Generate a matplotlib figure for one of the thesis analysis outputs."""
    records = load_json_records(input_json)
    if mode == "delay":
        path = plot_metric_vs_delay(records, metric=metric, path=output_path)
    elif mode == "fill_ratio":
        path = plot_metric_vs_fill_ratio(records, metric=metric, path=output_path, delay_dt=delay_dt)
    elif mode == "blp":
        if records and "switching_probability" in records[0]:
            path = plot_blp_vs_switching_probability(records, path=output_path)
        else:
            path = plot_blp_vs_memory_strength(records, path=output_path)
    else:
        raise typer.BadParameter("mode must be one of: delay, fill_ratio, blp")
    typer.echo(str(path))

# === END cli.py ===

__version__ = "0.3.1"

__all__ = [
    "BackendConfig", "SweepConfig", "EncodingError", "CircuitBuildError",
    "HardwareError", "AerExecutionError", "PostprocessError",
    "TeleportationLayout", "TeleportationProgram", "app",
    "num_physical_qubits_for_dimension", "physical_hilbert_dimension_for_logical_dimension",
    "fill_ratio", "dt_seconds_to_ns", "delay_dt_to_ns", "logical_basis_indices", "logical_subspace_projector",
    "resolved_n_physical",
    "normalize_logical_state", "embed_logical_state", "extract_logical_density_subspace",
    "counts_to_probabilities", "expectation_from_counts", "pure_state_density",
    "pure_state_fidelity", "leakage_probability", "logical_subspace_population",
    "renormalized_logical_subspace_density", "in_subspace_fidelity",
    "physical_and_logical_summary", "average_gate_fidelity_from_process_fidelity",
    "random_haar_state", "computational_basis_state", "fourier_state",
    "canonical_probe_states",
    "all_measurement_bases", "all_pauli_strings", "pauli_operator",
    "compatible_measurement_setting", "project_to_physical_density_matrix", "reconstruct_density_matrix",
    "process_tomography_probe_states", "vectorize_operator", "apply_superoperator",
    "reconstruct_superoperator", "choi_matrix_from_superoperator", "process_fidelity_to_identity",
    "resample_counts_multinomial", "bootstrap_tomography_metrics",
    "bootstrap_average_tomography_metrics", "bootstrap_process_tomography_metrics",
    "bootstrap_probe_mean_observables",
    "markovian_delay_density", "markovian_delay_observables", "markovian_delay_fidelity",
    "switching_probability_to_correlation_time", "correlation_time_to_switching_probability",
    "estimate_effective_t2_from_records", "calibrate_random_telegraph_from_records",
    "random_telegraph_dephasing_density_trajectory", "random_telegraph_dephasing_observables",
    "correlated_memory_density_trajectory", "correlated_memory_observables",
    "correlated_memory_fidelity", "trace_distance", "blp_non_markovianity",
    "blp_random_telegraph_non_markovianity", "random_telegraph_blp_probe_pair",
    "pauli_frame_flip_for_basis_label", "correct_output_bitstring_for_deferred_frame",
    "corrected_counts_from_deferred_shots", "prepare_embedded_logical_state",
    "build_block_teleportation_circuit", "append_output_measurements",
    "backend_operation_names", "backend_supports_dynamic_circuits", "backend_supports_delay",
    "backend_dt_seconds",
    "validate_backend_for_experiment", "select_backend", "transpile_isa", "run_sampler_job",
    "extract_register_counts", "extract_register_bitstrings", "counts_register_layout_from_circuit",
    "split_combined_register_string", "marginalize_combined_counts_for_register",
    "extract_register_shots_from_memory", "build_basic_noise_model", "make_aer_simulator",
    "run_aer_delay_sweep", "run_aer_process_tomography", "save_json", "save_csv", "load_json_records",
    "plot_metric_vs_delay", "plot_metric_vs_fill_ratio", "plot_blp_vs_memory_strength",
    "plot_blp_vs_switching_probability",
    "merge_fixed_n_summary_rows", "load_fixed_n_summary_rows",
    "summarize_fixed_n_comparison", "summarize_three_lane_fixed_n_table",
    "save_fixed_n_markdown_report", "save_three_lane_fixed_n_markdown_report",
    "save_blp_markdown_report",
    "save_random_telegraph_calibration_markdown_report", "make_probe_state",
    "fixed_n_dimensions", "fixed_n_sweep_configs", "run_markovian_fixed_n_sweep",
    "run_aer_fixed_n_sweep",
    "run_correlated_memory_fixed_n_sweep", "run_blp_memory_scan", "run_blp_random_telegraph_scan",
    "main",
    "run_hardware_delay_sweep", "run_hardware_fixed_n_sweep", "run_hardware_process_tomography",
    "run_hardware_fixed_n_process_tomography", "summarize_results",
]

_LEGACY_SUBMODULE_EXPORTS = {
    "config": ["BackendConfig", "SweepConfig", "CorrectionMode"],
    "encoding": [
        "EncodingError", "num_physical_qubits_for_dimension",
        "physical_hilbert_dimension_for_logical_dimension", "fill_ratio",
        "dt_seconds_to_ns", "delay_dt_to_ns",
        "logical_basis_indices", "logical_subspace_projector", "normalize_logical_state",
        "embed_logical_state", "extract_logical_density_subspace", "resolved_n_physical",
    ],
    "states": ["random_haar_state", "computational_basis_state", "fourier_state", "canonical_probe_states"],
    "metrics": [
        "counts_to_probabilities", "expectation_from_counts", "pure_state_density",
        "pure_state_fidelity", "leakage_probability", "logical_subspace_population",
        "renormalized_logical_subspace_density", "in_subspace_fidelity",
        "physical_and_logical_summary", "average_gate_fidelity_from_process_fidelity",
    ],
    "postprocess": [
        "PostprocessError", "pauli_frame_flip_for_basis_label",
        "correct_output_bitstring_for_deferred_frame", "corrected_counts_from_deferred_shots",
    ],
    "tomography": [
        "all_measurement_bases", "all_pauli_strings", "pauli_operator",
        "compatible_measurement_setting", "project_to_physical_density_matrix",
        "reconstruct_density_matrix",
    ],
    "process": [
        "process_tomography_probe_states", "vectorize_operator", "apply_superoperator",
        "reconstruct_superoperator", "choi_matrix_from_superoperator", "process_fidelity_to_identity",
    ],
    "statistics": [
        "resample_counts_multinomial", "bootstrap_tomography_metrics",
        "bootstrap_average_tomography_metrics", "bootstrap_process_tomography_metrics",
        "bootstrap_probe_mean_observables",
    ],
    "simulation": [
        "markovian_delay_density", "markovian_delay_observables", "markovian_delay_fidelity",
        "switching_probability_to_correlation_time", "correlation_time_to_switching_probability",
        "estimate_effective_t2_from_records", "calibrate_random_telegraph_from_records",
        "random_telegraph_dephasing_density_trajectory", "random_telegraph_dephasing_observables",
        "correlated_memory_density_trajectory", "correlated_memory_observables",
        "correlated_memory_fidelity", "trace_distance", "blp_non_markovianity",
        "blp_random_telegraph_non_markovianity", "random_telegraph_blp_probe_pair",
    ],
    "circuits": [
        "CircuitBuildError", "TeleportationLayout", "TeleportationProgram",
        "prepare_embedded_logical_state", "build_block_teleportation_circuit",
        "append_output_measurements",
    ],
    "hardware": [
        "HardwareError", "backend_operation_names", "backend_supports_dynamic_circuits",
        "backend_supports_delay", "backend_dt_seconds", "validate_backend_for_experiment", "select_backend",
        "transpile_isa", "run_sampler_job", "extract_register_counts",
        "extract_register_bitstrings", "counts_register_layout_from_circuit",
        "split_combined_register_string", "marginalize_combined_counts_for_register",
        "extract_register_shots_from_memory",
    ],
    "aer": [
        "AerExecutionError", "build_basic_noise_model", "make_aer_simulator",
        "run_aer_delay_sweep", "run_aer_process_tomography", "split_combined_register_string",
        "marginalize_combined_counts_for_register", "extract_register_shots_from_memory",
    ],
    "reports": [
        "save_json", "save_csv", "load_json_records", "plot_metric_vs_delay",
        "plot_metric_vs_fill_ratio", "plot_blp_vs_memory_strength", "plot_blp_vs_switching_probability",
        "merge_fixed_n_summary_rows", "load_fixed_n_summary_rows",
        "summarize_fixed_n_comparison", "summarize_three_lane_fixed_n_table",
        "save_fixed_n_markdown_report", "save_three_lane_fixed_n_markdown_report",
        "save_blp_markdown_report",
        "save_random_telegraph_calibration_markdown_report",
    ],
    "sweeps": [
        "make_probe_state", "fixed_n_dimensions", "fixed_n_sweep_configs",
        "run_markovian_fixed_n_sweep", "run_aer_fixed_n_sweep", "run_correlated_memory_fixed_n_sweep",
        "run_blp_memory_scan", "run_blp_random_telegraph_scan", "run_hardware_delay_sweep",
        "run_hardware_fixed_n_sweep", "run_hardware_process_tomography",
        "run_hardware_fixed_n_process_tomography", "summarize_results",
    ],
    "cli": ["app", "main"],
}


def _register_legacy_submodule(name: str, exports: list[str]) -> None:
    """Convert between Qiskit register bit ordering conventions used in post-processing."""
    module_name = f"{__name__}.{name}"
    module = types.ModuleType(module_name)
    module.__dict__.update({export: globals()[export] for export in exports})
    module.__all__ = tuple(exports)
    sys.modules[module_name] = module
    globals()[name] = module


def main() -> None:
    """Entry point used by the console script and python -m execution."""
    app()


for _submodule_name, _exports in _LEGACY_SUBMODULE_EXPORTS.items():
    _register_legacy_submodule(_submodule_name, _exports)


if __name__ == "__main__":  # pragma: no cover
    main()
