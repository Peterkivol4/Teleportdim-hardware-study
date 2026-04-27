from typing import Any, cast

import numpy as np

from teleportdim.encoding import embed_logical_state, num_physical_qubits_for_dimension


def test_num_physical_qubits_for_dimension() -> None:
    assert num_physical_qubits_for_dimension(2) == 1
    assert num_physical_qubits_for_dimension(3) == 2
    assert num_physical_qubits_for_dimension(4) == 2
    assert num_physical_qubits_for_dimension(5) == 3


def test_embed_logical_state_qutrit() -> None:
    state = np.array([1, 1j, -1], dtype=complex)
    embedded = embed_logical_state(state, 3)
    assert embedded.shape == (4,)
    assert np.isclose(np.linalg.norm(embedded), 1.0)
    assert np.isclose(embedded[3], 0.0)


from teleportdim import BackendConfig, SweepConfig


def test_backend_and_sweep_config_validate_runtime_literals() -> None:
    try:
        BackendConfig(correction_mode=cast(Any, "typo"))
        raise AssertionError("BackendConfig should reject invalid correction_mode")
    except ValueError:
        pass
    try:
        SweepConfig(dimension=2, state_family=cast(Any, "bad"))
        raise AssertionError("SweepConfig should reject invalid state_family")
    except ValueError:
        pass
