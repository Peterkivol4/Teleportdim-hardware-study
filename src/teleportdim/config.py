from __future__ import annotations


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


__all__ = [
    "BackendConfig",
    "SweepConfig",
    "CorrectionMode",
    "DEFAULT_AER_DT_NS_PER_DT",
    "DEFAULT_AER_T1_SECONDS",
    "DEFAULT_AER_T2_SECONDS",
]
