from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from teleportdim import app


runner = CliRunner()


def test_fixed_n_plan_cli_returns_expected_dimensions():
    result = runner.invoke(app, ["fixed-n-plan", "--n-values", "2", "--delays", "0,64"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert [item["dimension"] for item in payload] == [2, 3, 4]


def test_markovian_model_cli_returns_json():
    result = runner.invoke(app, ["markovian-model", "--dimension", "3", "--delay", "5", "--t-dep", "10"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert set(payload) == {"fidelity", "leakage", "in_subspace_fidelity"}


def test_compare_fixed_n_cli_writes_summary_files(tmp_path: Path):
    state_path = tmp_path / "state_records.json"
    state_path.write_text(json.dumps([
        {
            "dimension": 3,
            "n_physical": 2,
            "fill_ratio": 0.75,
            "delay_dt": 0,
            "fidelity": 0.93,
            "fidelity_ci_low": 0.91,
            "fidelity_ci_high": 0.94,
        },
        {
            "dimension": 4,
            "n_physical": 2,
            "fill_ratio": 1.0,
            "delay_dt": 0,
            "fidelity": 0.97,
            "fidelity_ci_low": 0.96,
            "fidelity_ci_high": 0.98,
        },
    ]))
    process_path = tmp_path / "process_records.json"
    process_path.write_text(json.dumps([
        {
            "dimension": 3,
            "n_physical": 2,
            "fill_ratio": 0.75,
            "delay_dt": 0,
            "process_fidelity": 0.90,
            "process_fidelity_ci_low": 0.88,
            "process_fidelity_ci_high": 0.92,
        },
        {
            "dimension": 4,
            "n_physical": 2,
            "fill_ratio": 1.0,
            "delay_dt": 0,
            "process_fidelity": 0.95,
            "process_fidelity_ci_low": 0.94,
            "process_fidelity_ci_high": 0.96,
        },
    ]))
    output_stem = tmp_path / "compare"
    result = runner.invoke(
        app,
        [
            "compare-fixed-n",
            "--input-json",
            f"{state_path},{process_path}",
            "--n-physical",
            "2",
            "--dt-ns-per-dt",
            "0.222",
            "--output-stem",
            str(output_stem),
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload[0]["delta|d4-d3|metric|fidelity"] > 0
    assert payload[0]["d3|metric|process_fidelity"] == 0.9
    assert payload[0]["significant|d4-d3|metric|fidelity"] is True
    assert payload[0]["dt_ns"] == 0.0
    assert (tmp_path / "compare.json").exists()
    assert (tmp_path / "compare.csv").exists()
    assert (tmp_path / "compare.md").exists()


def test_compare_three_lanes_cli_writes_summary_files(tmp_path: Path):
    theory_path = tmp_path / "theory_compare.json"
    theory_path.write_text(json.dumps([
        {
            "n_physical": 2,
            "delay_dt": 0,
            "dt_ns": 0.0,
            "source_simulation_lanes": "markovian_model",
            "contains_theory_baseline": True,
            "contains_explicit_theory_mixing": True,
            "d2|fill_ratio": 0.5,
            "d2|metric|fidelity": 0.99,
            "d2|metric_ci|fidelity|low": 0.98,
            "d2|metric_ci|fidelity|high": 1.00,
            "d2|metric|leakage": 0.01,
            "d2|metric_ci|leakage|low": 0.00,
            "d2|metric_ci|leakage|high": 0.02,
            "d2|metric|in_subspace_fidelity": 1.00,
            "d2|metric_ci|in_subspace_fidelity|low": 0.99,
            "d2|metric_ci|in_subspace_fidelity|high": 1.00,
            "d3|fill_ratio": 0.75,
            "d3|metric|fidelity": 0.98,
            "d3|metric_ci|fidelity|low": 0.97,
            "d3|metric_ci|fidelity|high": 0.99,
            "d3|metric|leakage": 0.02,
            "d3|metric_ci|leakage|low": 0.01,
            "d3|metric_ci|leakage|high": 0.03,
            "d3|metric|in_subspace_fidelity": 0.99,
            "d3|metric_ci|in_subspace_fidelity|low": 0.98,
            "d3|metric_ci|in_subspace_fidelity|high": 1.00,
            "d4|fill_ratio": 1.0,
            "d4|metric|fidelity": 0.97,
            "d4|metric_ci|fidelity|low": 0.96,
            "d4|metric_ci|fidelity|high": 0.98,
            "d4|metric|leakage": 0.0,
            "d4|metric_ci|leakage|low": 0.0,
            "d4|metric_ci|leakage|high": 0.0,
            "d4|metric|in_subspace_fidelity": 0.97,
            "d4|metric_ci|in_subspace_fidelity|low": 0.96,
            "d4|metric_ci|in_subspace_fidelity|high": 0.98,
            "delta|d4-d3|metric|fidelity": -0.01,
            "significant|d4-d3|metric|fidelity": False,
            "delta|d4-d2|metric|fidelity": -0.02,
            "significant|d4-d2|metric|fidelity": True,
            "delta|d4-d3|metric|leakage": -0.02,
            "significant|d4-d3|metric|leakage": True,
            "delta|d4-d2|metric|leakage": -0.01,
            "significant|d4-d2|metric|leakage": False,
            "delta|d4-d3|metric|in_subspace_fidelity": -0.02,
            "significant|d4-d3|metric|in_subspace_fidelity": True,
            "delta|d4-d2|metric|in_subspace_fidelity": -0.03,
            "significant|d4-d2|metric|in_subspace_fidelity": True,
        }
    ]))
    aer_path = tmp_path / "aer_compare.json"
    aer_path.write_text(json.dumps([
        {
            "n_physical": 2,
            "delay_dt": 0,
            "dt_ns": 0.0,
            "source_simulation_lanes": "aer_process_tomography",
            "d2|fill_ratio": 0.5,
            "d2|metric|fidelity": 0.95,
            "d2|metric_ci|fidelity|low": 0.94,
            "d2|metric_ci|fidelity|high": 0.96,
            "d2|metric|process_fidelity": 0.94,
            "d2|metric_ci|process_fidelity|low": 0.93,
            "d2|metric_ci|process_fidelity|high": 0.95,
            "d2|metric|average_gate_fidelity": 0.96,
            "d2|metric_ci|average_gate_fidelity|low": 0.95,
            "d2|metric_ci|average_gate_fidelity|high": 0.97,
            "d3|fill_ratio": 0.75,
            "d3|metric|fidelity": 0.93,
            "d3|metric_ci|fidelity|low": 0.92,
            "d3|metric_ci|fidelity|high": 0.94,
            "d3|metric|process_fidelity": 0.90,
            "d3|metric_ci|process_fidelity|low": 0.89,
            "d3|metric_ci|process_fidelity|high": 0.91,
            "d3|metric|average_gate_fidelity": 0.93,
            "d3|metric_ci|average_gate_fidelity|low": 0.92,
            "d3|metric_ci|average_gate_fidelity|high": 0.94,
            "d4|fill_ratio": 1.0,
            "d4|metric|fidelity": 0.90,
            "d4|metric_ci|fidelity|low": 0.89,
            "d4|metric_ci|fidelity|high": 0.91,
            "d4|metric|process_fidelity": 0.85,
            "d4|metric_ci|process_fidelity|low": 0.84,
            "d4|metric_ci|process_fidelity|high": 0.86,
            "d4|metric|average_gate_fidelity": 0.88,
            "d4|metric_ci|average_gate_fidelity|low": 0.87,
            "d4|metric_ci|average_gate_fidelity|high": 0.89,
            "delta|d4-d3|metric|fidelity": -0.03,
            "significant|d4-d3|metric|fidelity": True,
            "delta|d4-d2|metric|fidelity": -0.05,
            "significant|d4-d2|metric|fidelity": True,
            "delta|d4-d3|metric|process_fidelity": -0.05,
            "significant|d4-d3|metric|process_fidelity": True,
            "delta|d4-d2|metric|process_fidelity": -0.09,
            "significant|d4-d2|metric|process_fidelity": True,
            "delta|d4-d3|metric|average_gate_fidelity": -0.05,
            "significant|d4-d3|metric|average_gate_fidelity": True,
            "delta|d4-d2|metric|average_gate_fidelity": -0.08,
            "significant|d4-d2|metric|average_gate_fidelity": True,
        }
    ]))
    hardware_state_path = tmp_path / "hardware_state_compare.json"
    hardware_state_path.write_text(json.dumps([
        {
            "n_physical": 2,
            "delay_dt": 0,
            "dt_ns": 0.0,
            "source_simulation_lanes": "ibm_runtime_state_tomography",
            "d2|fill_ratio": 0.5,
            "d2|metric|fidelity": 0.88,
            "d2|metric_ci|fidelity|low": 0.86,
            "d2|metric_ci|fidelity|high": 0.90,
            "d3|fill_ratio": 0.75,
            "d3|metric|fidelity": 0.86,
            "d3|metric_ci|fidelity|low": 0.85,
            "d3|metric_ci|fidelity|high": 0.87,
            "d4|fill_ratio": 1.0,
            "d4|metric|fidelity": 0.85,
            "d4|metric_ci|fidelity|low": 0.84,
            "d4|metric_ci|fidelity|high": 0.86,
            "delta|d4-d3|metric|fidelity": -0.01,
            "significant|d4-d3|metric|fidelity": False,
            "delta|d4-d2|metric|fidelity": -0.03,
            "significant|d4-d2|metric|fidelity": True,
        }
    ]))
    hardware_process_path = tmp_path / "hardware_process_compare.json"
    hardware_process_path.write_text(json.dumps([
        {
            "n_physical": 2,
            "delay_dt": 0,
            "dt_ns": 0.0,
            "source_simulation_lanes": "ibm_runtime_process_tomography",
            "d2|fill_ratio": 0.5,
            "d2|metric|process_fidelity": 0.87,
            "d2|metric_ci|process_fidelity|low": 0.84,
            "d2|metric_ci|process_fidelity|high": 0.90,
            "d3|fill_ratio": 0.75,
            "d3|metric|process_fidelity": 0.74,
            "d3|metric_ci|process_fidelity|low": 0.71,
            "d3|metric_ci|process_fidelity|high": 0.77,
            "d4|fill_ratio": 1.0,
            "d4|metric|process_fidelity": 0.63,
            "d4|metric_ci|process_fidelity|low": 0.61,
            "d4|metric_ci|process_fidelity|high": 0.65,
            "delta|d4-d3|metric|process_fidelity": -0.11,
            "significant|d4-d3|metric|process_fidelity": True,
            "delta|d4-d2|metric|process_fidelity": -0.24,
            "significant|d4-d2|metric|process_fidelity": True,
        }
    ]))
    output_stem = tmp_path / "three_lane"
    result = runner.invoke(
        app,
        [
            "compare-three-lanes",
            "--theory-json",
            str(theory_path),
            "--aer-json",
            str(aer_path),
            "--hardware-json",
            f"{hardware_state_path},{hardware_process_path}",
            "--n-physical",
            "2",
            "--output-stem",
            str(output_stem),
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert any(row["lane"] == "theory" and row["metric"] == "fidelity" for row in payload)
    assert any(
        row["lane"] == "hardware" and row["metric"] == "process_fidelity"
        for row in payload
    )
    assert (tmp_path / "three_lane.json").exists()
    assert (tmp_path / "three_lane.csv").exists()
    assert (tmp_path / "three_lane.md").exists()


def test_aer_fixed_n_sweep_cli_passes_requested_shots(monkeypatch):
    captured: dict[str, object] = {}

    def fake_run(configs, **kwargs):
        captured["shots"] = [config.shots for config in configs]
        captured["kwargs"] = kwargs
        return []

    monkeypatch.setattr("teleportdim.run_aer_fixed_n_sweep", fake_run)
    result = runner.invoke(
        app,
        [
            "aer-fixed-n-sweep",
            "--n-values",
            "2",
            "--delays",
            "0",
            "--shots",
            "321",
        ],
    )

    assert result.exit_code == 0
    assert captured["shots"] == [321, 321, 321]


def test_blp_random_telegraph_scan_cli_writes_summary_files(tmp_path: Path):
    output_stem = tmp_path / "blp_rt"
    result = runner.invoke(
        app,
        [
            "blp-random-telegraph-scan",
            "--dimensions",
            "2,3",
            "--n-physical",
            "2",
            "--switching-probabilities",
            "0.0125,0.05",
            "--coupling-strength",
            "0.4",
            "--steps",
            "8",
            "--samples",
            "128",
            "--output-stem",
            str(output_stem),
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert len(payload) == 4
    assert payload[0]["n_physical"] == 2
    assert "switching_probability" in payload[0]
    assert (tmp_path / "blp_rt.json").exists()
    assert (tmp_path / "blp_rt.csv").exists()
    assert (tmp_path / "blp_rt.md").exists()


def test_hardware_fixed_n_sweep_cli_passes_requested_parameters(monkeypatch):
    captured: dict[str, object] = {}

    def fake_run(configs, backend, **kwargs):
        captured["dimensions"] = [config.dimension for config in configs]
        captured["n_physical"] = [config.n_physical for config in configs]
        captured["delays"] = [list(config.delay_dt_values) for config in configs]
        captured["backend_name"] = backend.backend_name
        captured["shots"] = backend.shots
        captured["kwargs"] = kwargs
        return []

    monkeypatch.setattr("teleportdim.run_hardware_fixed_n_sweep", fake_run)
    result = runner.invoke(
        app,
        [
            "hardware-fixed-n-sweep",
            "--n-values",
            "2",
            "--backend-name",
            "ibm_fez",
            "--shots",
            "321",
            "--delays",
            "0,64",
            "--bootstrap-samples",
            "11",
        ],
    )

    assert result.exit_code == 0
    assert captured["dimensions"] == [2, 3, 4]
    assert captured["n_physical"] == [2, 2, 2]
    assert captured["delays"] == [[0, 64], [0, 64], [0, 64]]
    assert captured["backend_name"] == "ibm_fez"
    assert captured["shots"] == 321
    assert captured["kwargs"]["bootstrap_samples"] == 11
    assert captured["kwargs"]["confidence_level"] == 0.95
    assert callable(captured["kwargs"]["progress"])


def test_hardware_fixed_n_process_tomography_cli_passes_requested_parameters(monkeypatch):
    captured: dict[str, object] = {}

    def fake_run(configs, backend, **kwargs):
        captured["dimensions"] = [config.dimension for config in configs]
        captured["n_physical"] = [config.n_physical for config in configs]
        captured["delays"] = [list(config.delay_dt_values) for config in configs]
        captured["backend_name"] = backend.backend_name
        captured["shots"] = backend.shots
        captured["kwargs"] = kwargs
        return []

    monkeypatch.setattr("teleportdim.run_hardware_fixed_n_process_tomography", fake_run)
    result = runner.invoke(
        app,
        [
            "hardware-fixed-n-process-tomography",
            "--n-values",
            "2",
            "--backend-name",
            "ibm_fez",
            "--shots",
            "222",
            "--delays",
            "0,64",
            "--bootstrap-samples",
            "13",
        ],
    )

    assert result.exit_code == 0
    assert captured["dimensions"] == [2, 3, 4]
    assert captured["n_physical"] == [2, 2, 2]
    assert captured["delays"] == [[0, 64], [0, 64], [0, 64]]
    assert captured["backend_name"] == "ibm_fez"
    assert captured["shots"] == 222
    assert captured["kwargs"]["bootstrap_samples"] == 13
    assert captured["kwargs"]["confidence_level"] == 0.95
    assert callable(captured["kwargs"]["progress"])


def test_calibrate_random_telegraph_cli_writes_outputs(tmp_path: Path):
    input_path = tmp_path / "process_records.json"
    input_path.write_text(json.dumps([
        {
            "dimension": 2,
            "n_physical": 1,
            "delay_dt": 0,
            "dt_ns": 0.0,
            "process_fidelity": 0.9,
            "process_fidelity_ci_low": 0.88,
            "process_fidelity_ci_high": 0.92,
            "backend_name": "synthetic",
            "simulation_lane": "synthetic_decay",
        },
        {
            "dimension": 2,
            "n_physical": 1,
            "delay_dt": 1,
            "dt_ns": 50.0,
            "process_fidelity": 0.75,
            "process_fidelity_ci_low": 0.73,
            "process_fidelity_ci_high": 0.77,
            "backend_name": "synthetic",
            "simulation_lane": "synthetic_decay",
        },
    ]))
    output_stem = tmp_path / "rtn_cal"
    result = runner.invoke(
        app,
        [
            "calibrate-random-telegraph",
            "--input-json",
            str(input_path),
            "--dimension",
            "2",
            "--n-physical",
            "1",
            "--metric",
            "process_fidelity",
            "--dt-ns-per-step",
            "5.0",
            "--fit-mode",
            "first_nonzero",
            "--output-stem",
            str(output_stem),
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["metric"] == "process_fidelity"
    assert payload["fit_mode"] == "first_nonzero"
    assert payload["switching_probability"] > 0.0
    assert (tmp_path / "rtn_cal.json").exists()
    assert (tmp_path / "rtn_cal.md").exists()
