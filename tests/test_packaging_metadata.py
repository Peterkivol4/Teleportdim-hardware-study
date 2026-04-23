from pathlib import Path


def test_py_typed_marker_is_packaged():
    marker = Path(__file__).resolve().parents[1] / 'src' / 'teleportdim' / 'py.typed'
    assert marker.exists()


def test_pyproject_has_no_phantom_dependencies():
    pyproject = (Path(__file__).resolve().parents[1] / 'pyproject.toml').read_text()
    assert 'pydantic' not in pyproject
    assert 'scipy' not in pyproject
