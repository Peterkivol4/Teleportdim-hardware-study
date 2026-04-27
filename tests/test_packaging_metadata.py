from pathlib import Path


def test_py_typed_marker_is_packaged() -> None:
    marker = Path(__file__).resolve().parents[1] / 'src' / 'teleportdim' / 'py.typed'
    assert marker.exists()


def test_pyproject_has_no_phantom_dependencies() -> None:
    pyproject = (Path(__file__).resolve().parents[1] / 'pyproject.toml').read_text()
    assert 'pydantic' not in pyproject
    assert 'scipy' not in pyproject


def test_repo_uses_pyproject_extras_and_mit_license() -> None:
    root = Path(__file__).resolve().parents[1]
    pyproject = (root / 'pyproject.toml').read_text()

    assert not (root / 'setup.py').exists()
    assert (root / 'LICENSE').read_text().startswith('MIT License')
    for extra in ('aer =', 'ibm =', 'full =', 'dev ='):
        assert extra in pyproject


def test_module_execution_uses_main_module_not_package_initializer() -> None:
    root = Path(__file__).resolve().parents[1]
    init_source = (root / 'src' / 'teleportdim' / '__init__.py').read_text()
    main_source = (root / 'src' / 'teleportdim' / '__main__.py').read_text()
    makefile = (root / 'Makefile').read_text()

    assert 'if __name__ == "__main__"' not in init_source
    assert 'from .cli import main' in main_source
    assert 'python src/teleportdim/__init__.py' not in makefile
    assert '-m teleportdim' in makefile
