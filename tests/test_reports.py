from __future__ import annotations

from typing import Any
from pathlib import Path

from teleportdim.reports import (
    load_json_records,
    plot_blp_vs_memory_strength,
    plot_metric_vs_delay,
    plot_metric_vs_fill_ratio,
    save_csv,
    save_json,
)


def _sample_records() -> Any:
    return [
        {"dimension": 3, "n_physical": 2, "fill_ratio": 0.75, "delay_dt": 0, "fidelity": 0.95, "leakage": 0.02},
        {"dimension": 3, "n_physical": 2, "fill_ratio": 0.75, "delay_dt": 10, "fidelity": 0.80, "leakage": 0.08},
        {"dimension": 4, "n_physical": 2, "fill_ratio": 1.00, "delay_dt": 0, "fidelity": 0.97, "leakage": 0.00},
        {"dimension": 4, "n_physical": 2, "fill_ratio": 1.00, "delay_dt": 10, "fidelity": 0.85, "leakage": 0.00},
    ]


def test_save_and_load_json_round_trip(tmp_path: Path) -> None:
    path = save_json(_sample_records(), tmp_path / 'records.json')
    loaded = load_json_records(path)
    assert loaded == _sample_records()


def test_save_csv_and_plots_create_files(tmp_path: Path) -> None:
    records = _sample_records()
    csv_path = save_csv(records, tmp_path / 'records.csv')
    delay_plot = plot_metric_vs_delay(records, metric='fidelity', path=tmp_path / 'delay.png')
    phi_plot = plot_metric_vs_fill_ratio(records, metric='leakage', path=tmp_path / 'phi.png', delay_dt=10)
    assert csv_path.exists()
    assert delay_plot.exists()
    assert phi_plot.exists()


def test_plot_blp_vs_memory_strength_creates_file(tmp_path: Path) -> None:
    records = [
        {"memory_strength": 0.0, "blp_measure": 0.0},
        {"memory_strength": 0.5, "blp_measure": 0.1},
        {"memory_strength": 1.0, "blp_measure": 0.4},
    ]
    plot_path = plot_blp_vs_memory_strength(records, path=tmp_path / 'blp.png')
    assert plot_path.exists()
