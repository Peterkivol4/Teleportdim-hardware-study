from typing import Any
from teleportdim.hardware import (
    HardwareError,
    backend_supports_delay,
    backend_supports_dynamic_circuits,
    validate_backend_for_experiment,
)


class DummyTarget:
    def __init__(self, operation_names: Any) -> None:
        self.operation_names = operation_names


class DummyBackend:
    def __init__(self, operation_names: Any, num_qubits: Any=7, name: Any="dummy_backend") -> None:
        self.target = DummyTarget(operation_names)
        self.num_qubits = num_qubits
        self.name = name


def test_backend_support_helpers() -> None:
    backend = DummyBackend({"delay", "if_else", "measure"})
    assert backend_supports_dynamic_circuits(backend) is True
    assert backend_supports_delay(backend) is True


def test_validate_backend_rejects_missing_if_else_for_dynamic_mode() -> None:
    backend = DummyBackend({"delay", "measure"}, num_qubits=7)
    try:
        validate_backend_for_experiment(
            backend,
            n_required_qubits=3,
            correction_mode="dynamic",
            require_delay=False,
        )
    except HardwareError as exc:
        assert "if_else" in str(exc)
    else:
        raise AssertionError("expected HardwareError")


def test_validate_backend_accepts_deferred_mode_without_if_else() -> None:
    backend = DummyBackend({"delay", "measure"}, num_qubits=7)
    validate_backend_for_experiment(
        backend,
        n_required_qubits=3,
        correction_mode="deferred",
        require_delay=True,
    )
