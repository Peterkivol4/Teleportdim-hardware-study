import numpy as np

from teleportdim.tomography import project_to_physical_density_matrix, reconstruct_density_matrix


def test_single_qubit_tomography_plus_state():
    setting_counts = {
        "X": {"0": 1000},
        "Y": {"0": 500, "1": 500},
        "Z": {"0": 500, "1": 500},
    }
    rho = reconstruct_density_matrix(setting_counts)
    expected = 0.5 * np.array([[1, 1], [1, 1]], dtype=complex)
    assert np.allclose(rho, expected, atol=1e-6)


def test_positivity_projection_clips_negative_eigenvalues_and_preserves_trace():
    rho = np.array([[1.1, 0.0], [0.0, -0.1]], dtype=complex)
    projected = project_to_physical_density_matrix(rho)
    eigvals = np.linalg.eigvalsh(projected)
    assert np.all(eigvals >= -1e-12)
    assert np.isclose(np.trace(projected), 1.0)
