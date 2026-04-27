from __future__ import annotations

import importlib.util

import pytest


@pytest.mark.skipif(importlib.util.find_spec("qiskit") is not None, reason="guard only matters without qiskit")
def test_circuit_build_without_qiskit_raises_clear_error() -> None:
    from teleportdim.circuits import CircuitBuildError, build_block_teleportation_circuit

    with pytest.raises(CircuitBuildError):
        build_block_teleportation_circuit([1, 0], 2)
