from typing import Any
import pytest
import teleportdim

from teleportdim.sweeps import _resolve_hardware_execution_dependencies


def test_hardware_dependency_resolver_fails_fast_when_symbol_missing(monkeypatch: Any) -> None:
    monkeypatch.delitem(teleportdim.__dict__, 'select_backend', raising=False)
    with pytest.raises(RuntimeError, match='select_backend'):
        _resolve_hardware_execution_dependencies()
