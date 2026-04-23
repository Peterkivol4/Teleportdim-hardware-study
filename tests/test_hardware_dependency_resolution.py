import pytest
import teleportdim


def test_hardware_dependency_resolver_fails_fast_when_symbol_missing(monkeypatch):
    monkeypatch.delitem(teleportdim.__dict__, 'select_backend', raising=False)
    with pytest.raises(RuntimeError, match='select_backend'):
        teleportdim._resolve_hardware_execution_dependencies()
