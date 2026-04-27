import json
from pathlib import Path

import teleportdim
from teleportdim.runner import (
    build_fixed_n_runner_configs,
    parse_delay_grid,
    write_run_artifacts,
)


def test_circuit_and_runner_symbols_are_owned_by_real_modules() -> None:
    assert teleportdim.build_block_teleportation_circuit.__module__ == "teleportdim.circuits"
    assert teleportdim.parse_delay_grid.__module__ == "teleportdim.runner"


def test_parse_delay_grid_accepts_cli_string_and_rejects_negative_values() -> None:
    assert parse_delay_grid("0,64, 128") == [0, 64, 128]
    assert parse_delay_grid([0, 32]) == [0, 32]

    try:
        parse_delay_grid("0,-1")
    except ValueError as exc:
        assert "non-negative" in str(exc)
    else:
        raise AssertionError("negative delay grid should fail")


def test_build_fixed_n_runner_configs_sets_shots_and_delay_grid() -> None:
    configs = build_fixed_n_runner_configs([2], delay_dt_values="0,64", shots=123)

    assert [config.dimension for config in configs] == [2, 3, 4]
    assert [config.n_physical for config in configs] == [2, 2, 2]
    assert [list(config.delay_dt_values) for config in configs] == [[0, 64], [0, 64], [0, 64]]
    assert [config.shots for config in configs] == [123, 123, 123]


def test_write_run_artifacts_creates_json_csv_and_requested_plot(tmp_path: Path) -> None:
    records = [
        {
            "dimension": 2,
            "n_physical": 2,
            "fill_ratio": 0.5,
            "delay_dt": 0,
            "dt_ns": 0.0,
            "fidelity": 0.99,
            "leakage": 0.01,
        },
        {
            "dimension": 2,
            "n_physical": 2,
            "fill_ratio": 0.5,
            "delay_dt": 64,
            "dt_ns": 14.2,
            "fidelity": 0.95,
            "leakage": 0.02,
        },
    ]

    artifacts = write_run_artifacts(
        records,
        tmp_path / "runner_smoke",
        delay_metrics=("fidelity",),
    )

    assert artifacts.json_path is not None
    assert artifacts.csv_path is not None
    assert artifacts.json_path.exists()
    assert artifacts.csv_path.exists()
    assert artifacts.plots["fidelity_delay"].exists()
    assert json.loads(artifacts.json_path.read_text())[0]["fidelity"] == 0.99
