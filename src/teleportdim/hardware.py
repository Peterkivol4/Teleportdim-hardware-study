from __future__ import annotations

from .config import BackendConfig

from collections.abc import Iterable
from typing import Any, cast

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


def select_backend(config: BackendConfig) -> Any:
    """Return an IBM backend satisfying the hardware run configuration.

    ``config.min_num_qubits`` is a hardware-qubit count, ``config.shots`` is a
    dimensionless shot count, and backend delay units remain backend-native dt.
    """
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


def transpile_isa(
    circuits: Iterable[Any],
    backend: Any,
    optimization_level: int = 1,
) -> list[Any]:
    """Transpile circuits into the backend ISA without changing shot counts.

    ``optimization_level`` is the Qiskit preset-pass-manager level; delays, when
    present, remain expressed in backend dt units.
    """
    _require_runtime_imports()
    pm = generate_preset_pass_manager(backend=backend, optimization_level=optimization_level)
    return [pm.run(circuit) for circuit in circuits]


def run_sampler_job(
    circuits: list[Any],
    backend: Any,
    shots: int = 4096,
    use_session: bool = False,
) -> Any:
    """Run SamplerV2 circuits and return the primitive result.

    ``shots`` is a raw hardware sampling count, not a normalized probability.
    """
    _require_runtime_imports()
    if use_session:
        with Session(backend=backend) as session:
            sampler = SamplerV2(mode=session)
            job = sampler.run(circuits, shots=shots)
            return job.result()
    sampler = SamplerV2(mode=backend)
    job = sampler.run(circuits, shots=shots)
    return job.result()


def _get_register_bitarray(pub_result: Any, register_name: str) -> Any:
    """Read per-register count or shot data from a primitive result object."""
    data_bin = pub_result.data
    if not hasattr(data_bin, register_name):
        available = [name for name in dir(data_bin) if not name.startswith("_")]
        raise HardwareError(
            f"result register {register_name!r} not found; available entries: {available}"
        )
    return getattr(data_bin, register_name)


def extract_register_counts(pub_result: Any, register_name: str) -> dict[str, int]:
    """Extract raw shot counts for an output classical register."""
    bitarray = _get_register_bitarray(pub_result, register_name)
    try:
        return cast(dict[str, int], bitarray.get_counts())
    except TypeError:
        return cast(dict[str, int], bitarray.get_counts(0))


def extract_register_bitstrings(pub_result: Any, register_name: str) -> list[str]:
    """Extract per-shot bitstrings for an output classical register."""
    bitarray = _get_register_bitarray(pub_result, register_name)
    try:
        return list(bitarray.get_bitstrings())
    except TypeError:
        return list(bitarray.get_bitstrings(0))


__all__ = [
    "HardwareError",
    "backend_operation_names",
    "backend_supports_dynamic_circuits",
    "backend_supports_delay",
    "backend_dt_seconds",
    "validate_backend_for_experiment",
    "select_backend",
    "transpile_isa",
    "run_sampler_job",
    "extract_register_counts",
    "extract_register_bitstrings",
]
