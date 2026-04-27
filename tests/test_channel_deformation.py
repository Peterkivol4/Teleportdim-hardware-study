from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import numpy as np
import pytest
from typer.testing import CliRunner

from teleportdim import app
from teleportdim.body_sweeps import evaluate_channel_body_record, run_channel_body_sweep
from teleportdim.deformation import compute_channel_deformation_vector
from teleportdim.fingerprinting import compare_body_fingerprints, expand_dimension_summary_records
from teleportdim.metrics import leakage_probability, pure_state_fidelity, renormalized_logical_subspace_density
from teleportdim.noise_bodies import NoiseBodyConfig, apply_noise_body_to_density
from teleportdim.states import computational_basis_state, fourier_state


def test_noise_body_config_validation() -> None:
    valid = NoiseBodyConfig(body="dephasing", strength=0.01, memory_strength=0.5)
    assert valid.body == "dephasing"
    with pytest.raises(ValueError, match="unsupported noise body"):
        NoiseBodyConfig(body="not_a_body", strength=0.0)
    with pytest.raises(ValueError, match="strength must be nonnegative"):
        NoiseBodyConfig(body="dephasing", strength=-0.1)
    with pytest.raises(ValueError, match="memory_strength"):
        NoiseBodyConfig(body="correlated_memory", strength=0.1, memory_strength=1.5)
    with pytest.raises(ValueError, match="leakage_rate"):
        NoiseBodyConfig(body="leakage_mixing", strength=0.1, leakage_rate=1.5)


def test_deformation_vector_zero_for_ideal_identity() -> None:
    record = evaluate_channel_body_record(
        dimension=2,
        n_physical=1,
        body_config=NoiseBodyConfig(body="ideal", strength=0.0),
        delay_dt=0,
        samples=32,
    )
    vector = compute_channel_deformation_vector(record)
    assert vector["delta_process"] == pytest.approx(0.0, abs=1e-10)
    assert vector["delta_avg_gate"] == pytest.approx(0.0, abs=1e-10)
    assert vector["leakage"] == pytest.approx(0.0, abs=1e-10)
    assert vector["delta_subspace"] == pytest.approx(0.0, abs=1e-10)
    assert vector["nonunitality"] == pytest.approx(0.0, abs=1e-10)
    assert vector["anisotropy"] == pytest.approx(0.0, abs=1e-10)


def test_leakage_body_moves_population_outside_codespace() -> None:
    state = computational_basis_state(3, 0)
    rho = apply_noise_body_to_density(
        state,
        3,
        NoiseBodyConfig(body="leakage_mixing", strength=0.25, leakage_rate=0.25),
        n_physical=2,
        delay_dt=0,
    )
    leakage = leakage_probability(rho, 3, 2)
    reduced = renormalized_logical_subspace_density(rho, 3, 2)
    assert leakage > 0.0
    assert 1.0 - leakage < 1.0
    assert np.trace(reduced) == pytest.approx(1.0)


def test_full_occupancy_has_zero_computational_leakage_but_can_deform_channel() -> None:
    state = fourier_state(4, 0)
    rho = apply_noise_body_to_density(
        state,
        4,
        NoiseBodyConfig(body="coherent_z_drift", strength=0.4),
        n_physical=2,
        delay_dt=64,
    )
    fidelity = pure_state_fidelity(state, rho)
    assert leakage_probability(rho, 4, 2) == pytest.approx(0.0, abs=1e-12)
    assert fidelity < 1.0


def test_dephasing_reduces_fourier_state_more_than_basis_state() -> None:
    body = NoiseBodyConfig(body="dephasing", strength=0.2)
    basis = computational_basis_state(2, 0)
    fourier = fourier_state(2, 0)
    basis_rho = apply_noise_body_to_density(basis, 2, body, n_physical=1, delay_dt=64)
    fourier_rho = apply_noise_body_to_density(fourier, 2, body, n_physical=1, delay_dt=64)
    assert pure_state_fidelity(basis, basis_rho) > pure_state_fidelity(fourier, fourier_rho)


def test_amplitude_damping_is_nonunital() -> None:
    record = evaluate_channel_body_record(
        dimension=2,
        n_physical=1,
        body_config=NoiseBodyConfig(body="amplitude_damping", strength=0.2),
        delay_dt=64,
        samples=32,
    )
    assert cast(float, record["nonunitality"]) > 0.0


def test_channel_body_sweep_returns_standard_records() -> None:
    records = run_channel_body_sweep(
        [1],
        dimensions=[2],
        bodies=["ideal", "dephasing"],
        strengths=[0.0],
        delays=[0],
        samples=32,
    )
    assert len(records) == 2
    assert {record["body"] for record in records} == {"ideal", "dephasing"}
    assert all("process_fidelity" in record for record in records)
    assert all("anisotropy" in record for record in records)


def test_compare_body_fingerprints_ranks_known_synthetic_match() -> None:
    body_records: list[dict[str, Any]] = [
        {
            "dimension": 2,
            "n_physical": 1,
            "delay_dt": 0,
            "body": "dephasing",
            "body_strength": 0.01,
            "process_fidelity": 0.8,
            "average_gate_fidelity": 0.866,
            "leakage": 0.0,
            "in_subspace_fidelity": 0.9,
        },
        {
            "dimension": 2,
            "n_physical": 1,
            "delay_dt": 0,
            "body": "coherent_z_drift",
            "body_strength": 0.01,
            "process_fidelity": 0.5,
            "average_gate_fidelity": 0.666,
            "leakage": 0.0,
            "in_subspace_fidelity": 0.6,
        },
    ]
    hardware_records = [
        {
            "dimension": 2,
            "n_physical": 1,
            "delay_dt": 0,
            "process_fidelity": 0.8,
            "average_gate_fidelity": 0.866,
            "leakage": 0.0,
            "in_subspace_fidelity": 0.9,
            "backend_name": "synthetic_hardware",
        }
    ]
    ranked = compare_body_fingerprints(
        body_records,
        hardware_records,
        metrics=["process_fidelity", "average_gate_fidelity", "leakage", "in_subspace_fidelity"],
    )
    assert ranked[0]["candidate_body"] == "dephasing"
    assert ranked[0]["rank"] == 1


def test_expand_dimension_summary_records_handles_fixed_n_compare_rows() -> None:
    expanded = expand_dimension_summary_records(
        [
            {
                "n_physical": 2,
                "delay_dt": 64,
                "dt_ns": 14.2,
                "source_simulation_lanes": "ibm_runtime_process_tomography",
                "d3|fill_ratio": 0.75,
                "d3|metric|process_fidelity": 0.72,
                "d4|fill_ratio": 1.0,
                "d4|metric|process_fidelity": 0.61,
            }
        ]
    )
    assert [record["dimension"] for record in expanded] == [3, 4]
    assert expanded[0]["process_fidelity"] == 0.72
    assert expanded[1]["fill_ratio"] == 1.0


def test_channel_body_sweep_cli_writes_json_csv_md(tmp_path: Path) -> None:
    output_stem = tmp_path / "body_sweep"
    result = CliRunner().invoke(
        app,
        [
            "channel-body-sweep",
            "--n-values",
            "1",
            "--dimensions",
            "2",
            "--bodies",
            "ideal,dephasing",
            "--strengths",
            "0",
            "--delays",
            "0",
            "--samples",
            "32",
            "--output-stem",
            str(output_stem),
        ],
    )
    assert result.exit_code == 0
    records = json.loads((tmp_path / "body_sweep.json").read_text())
    assert len(records) == 2
    assert (tmp_path / "body_sweep.csv").exists()
    assert (tmp_path / "body_sweep.md").exists()
