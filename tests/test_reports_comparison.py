from __future__ import annotations

from typing import Any
import json
from pathlib import Path

from teleportdim.reports import (
    load_backend_fixed_n_summary_rows,
    merge_backend_fixed_n_summary_rows,
    merge_fixed_n_summary_rows,
    save_backend_fixed_n_markdown_report,
    save_fixed_n_markdown_report,
    save_hardware_theory_divergence_markdown_report,
    save_three_lane_fixed_n_markdown_report,
    summarize_backend_fixed_n_comparison,
    summarize_backend_fixed_n_table,
    summarize_fixed_n_comparison,
    summarize_hardware_theory_divergence,
    summarize_three_lane_fixed_n_table,
)


def _sample_records() -> Any:
    return [
        {"dimension": 2, "n_physical": 2, "fill_ratio": 0.50, "delay_dt": 0, "avg_probe_fidelity": 0.94, "avg_probe_leakage": 0.01, "avg_probe_in_subspace_fidelity": 0.96, "simulation_lane": "markovian_model", "t_dep": 10.0},
        {"dimension": 3, "n_physical": 2, "fill_ratio": 0.75, "delay_dt": 0, "avg_probe_fidelity": 0.95, "avg_probe_leakage": 0.02, "avg_probe_in_subspace_fidelity": 0.97, "simulation_lane": "markovian_model", "t_dep": 10.0},
        {"dimension": 4, "n_physical": 2, "fill_ratio": 1.00, "delay_dt": 0, "avg_probe_fidelity": 0.97, "avg_probe_leakage": 0.00, "avg_probe_in_subspace_fidelity": 0.97, "simulation_lane": "markovian_model", "t_dep": 10.0},
        {"dimension": 2, "n_physical": 2, "fill_ratio": 0.50, "delay_dt": 10, "avg_probe_fidelity": 0.75, "avg_probe_leakage": 0.10, "avg_probe_in_subspace_fidelity": 0.83, "simulation_lane": "markovian_model", "t_dep": 10.0},
        {"dimension": 3, "n_physical": 2, "fill_ratio": 0.75, "delay_dt": 10, "avg_probe_fidelity": 0.80, "avg_probe_leakage": 0.08, "avg_probe_in_subspace_fidelity": 0.87, "simulation_lane": "markovian_model", "t_dep": 10.0},
        {"dimension": 4, "n_physical": 2, "fill_ratio": 1.00, "delay_dt": 10, "avg_probe_fidelity": 0.85, "avg_probe_leakage": 0.00, "avg_probe_in_subspace_fidelity": 0.85, "simulation_lane": "markovian_model", "t_dep": 10.0},
    ]


def test_summarize_fixed_n_comparison_builds_reference_delta_columns() -> None:
    summary = summarize_fixed_n_comparison(
        _sample_records(),
        n_physical=2,
        metric_keys=('avg_probe_fidelity', 'avg_probe_leakage', 'avg_probe_in_subspace_fidelity'),
    )
    assert len(summary) == 2
    assert 'delta|d4-d3|metric|avg_probe_fidelity' in summary[0]
    assert 'delta|d4-d2|metric|avg_probe_fidelity' in summary[0]
    assert summary[0]['delta|d4-d3|metric|avg_probe_fidelity'] > 0


def test_save_fixed_n_markdown_report_writes_file(tmp_path: Path) -> None:
    summary = summarize_fixed_n_comparison(
        _sample_records(),
        n_physical=2,
        metric_keys=('avg_probe_fidelity', 'avg_probe_leakage', 'avg_probe_in_subspace_fidelity'),
    )
    path = save_fixed_n_markdown_report(summary, path=tmp_path / 'compare.md')
    text = path.read_text()
    assert path.exists()
    assert "structurally zero" in text
    assert "baseline-only model" in text
    assert "different mechanism from circuit-level leakage" in text
    assert 'delay_dt = 0' in text
    assert 'd=2, phi=0.500' in text
    assert 'avg_probe_fidelity' in text


def _sample_three_lane_summaries() -> Any:
    theory_summary = summarize_fixed_n_comparison(
        [
            {
                "dimension": 2,
                "n_physical": 2,
                "fill_ratio": 0.50,
                "delay_dt": 0,
                "fidelity": 0.99,
                "fidelity_ci_low": 0.98,
                "fidelity_ci_high": 1.00,
                "leakage": 0.01,
                "leakage_ci_low": 0.00,
                "leakage_ci_high": 0.02,
                "in_subspace_fidelity": 1.00,
                "in_subspace_fidelity_ci_low": 0.99,
                "in_subspace_fidelity_ci_high": 1.00,
                "simulation_lane": "markovian_model",
                "t_dep": 10.0,
            },
            {
                "dimension": 3,
                "n_physical": 2,
                "fill_ratio": 0.75,
                "delay_dt": 0,
                "fidelity": 0.98,
                "fidelity_ci_low": 0.97,
                "fidelity_ci_high": 0.99,
                "leakage": 0.02,
                "leakage_ci_low": 0.01,
                "leakage_ci_high": 0.03,
                "in_subspace_fidelity": 0.99,
                "in_subspace_fidelity_ci_low": 0.98,
                "in_subspace_fidelity_ci_high": 1.00,
                "simulation_lane": "markovian_model",
                "t_dep": 10.0,
            },
            {
                "dimension": 4,
                "n_physical": 2,
                "fill_ratio": 1.00,
                "delay_dt": 0,
                "fidelity": 0.97,
                "fidelity_ci_low": 0.96,
                "fidelity_ci_high": 0.98,
                "leakage": 0.00,
                "leakage_ci_low": 0.00,
                "leakage_ci_high": 0.00,
                "in_subspace_fidelity": 0.97,
                "in_subspace_fidelity_ci_low": 0.96,
                "in_subspace_fidelity_ci_high": 0.98,
                "simulation_lane": "markovian_model",
                "t_dep": 10.0,
            },
        ],
        n_physical=2,
    )
    aer_summary = summarize_fixed_n_comparison(
        [
            {
                "dimension": 2,
                "n_physical": 2,
                "fill_ratio": 0.50,
                "delay_dt": 0,
                "fidelity": 0.95,
                "fidelity_ci_low": 0.94,
                "fidelity_ci_high": 0.96,
                "leakage": 0.02,
                "leakage_ci_low": 0.01,
                "leakage_ci_high": 0.03,
                "in_subspace_fidelity": 0.97,
                "in_subspace_fidelity_ci_low": 0.96,
                "in_subspace_fidelity_ci_high": 0.98,
                "process_fidelity": 0.94,
                "process_fidelity_ci_low": 0.93,
                "process_fidelity_ci_high": 0.95,
                "average_gate_fidelity": 0.96,
                "average_gate_fidelity_ci_low": 0.95,
                "average_gate_fidelity_ci_high": 0.97,
                "simulation_lane": "aer_process_tomography",
            },
            {
                "dimension": 3,
                "n_physical": 2,
                "fill_ratio": 0.75,
                "delay_dt": 0,
                "fidelity": 0.93,
                "fidelity_ci_low": 0.92,
                "fidelity_ci_high": 0.94,
                "leakage": 0.01,
                "leakage_ci_low": 0.01,
                "leakage_ci_high": 0.02,
                "in_subspace_fidelity": 0.95,
                "in_subspace_fidelity_ci_low": 0.94,
                "in_subspace_fidelity_ci_high": 0.96,
                "process_fidelity": 0.90,
                "process_fidelity_ci_low": 0.89,
                "process_fidelity_ci_high": 0.91,
                "average_gate_fidelity": 0.93,
                "average_gate_fidelity_ci_low": 0.92,
                "average_gate_fidelity_ci_high": 0.94,
                "simulation_lane": "aer_process_tomography",
            },
            {
                "dimension": 4,
                "n_physical": 2,
                "fill_ratio": 1.00,
                "delay_dt": 0,
                "fidelity": 0.90,
                "fidelity_ci_low": 0.89,
                "fidelity_ci_high": 0.91,
                "leakage": 0.00,
                "leakage_ci_low": 0.00,
                "leakage_ci_high": 0.00,
                "in_subspace_fidelity": 0.90,
                "in_subspace_fidelity_ci_low": 0.89,
                "in_subspace_fidelity_ci_high": 0.91,
                "process_fidelity": 0.85,
                "process_fidelity_ci_low": 0.84,
                "process_fidelity_ci_high": 0.86,
                "average_gate_fidelity": 0.88,
                "average_gate_fidelity_ci_low": 0.87,
                "average_gate_fidelity_ci_high": 0.89,
                "simulation_lane": "aer_process_tomography",
            },
        ],
        n_physical=2,
    )
    hardware_state_summary = summarize_fixed_n_comparison(
        [
            {
                "dimension": 2,
                "n_physical": 2,
                "fill_ratio": 0.50,
                "delay_dt": 0,
                "fidelity": 0.88,
                "fidelity_ci_low": 0.86,
                "fidelity_ci_high": 0.90,
                "leakage": 0.05,
                "leakage_ci_low": 0.04,
                "leakage_ci_high": 0.06,
                "in_subspace_fidelity": 0.93,
                "in_subspace_fidelity_ci_low": 0.92,
                "in_subspace_fidelity_ci_high": 0.94,
                "simulation_lane": "ibm_runtime_state_tomography",
            },
            {
                "dimension": 3,
                "n_physical": 2,
                "fill_ratio": 0.75,
                "delay_dt": 0,
                "fidelity": 0.86,
                "fidelity_ci_low": 0.85,
                "fidelity_ci_high": 0.87,
                "leakage": 0.03,
                "leakage_ci_low": 0.02,
                "leakage_ci_high": 0.04,
                "in_subspace_fidelity": 0.89,
                "in_subspace_fidelity_ci_low": 0.88,
                "in_subspace_fidelity_ci_high": 0.90,
                "simulation_lane": "ibm_runtime_state_tomography",
            },
            {
                "dimension": 4,
                "n_physical": 2,
                "fill_ratio": 1.00,
                "delay_dt": 0,
                "fidelity": 0.85,
                "fidelity_ci_low": 0.84,
                "fidelity_ci_high": 0.86,
                "leakage": 0.00,
                "leakage_ci_low": 0.00,
                "leakage_ci_high": 0.00,
                "in_subspace_fidelity": 0.85,
                "in_subspace_fidelity_ci_low": 0.84,
                "in_subspace_fidelity_ci_high": 0.86,
                "simulation_lane": "ibm_runtime_state_tomography",
            },
        ],
        n_physical=2,
    )
    hardware_process_summary = summarize_fixed_n_comparison(
        [
            {
                "dimension": 2,
                "n_physical": 2,
                "fill_ratio": 0.50,
                "delay_dt": 0,
                "process_fidelity": 0.87,
                "process_fidelity_ci_low": 0.84,
                "process_fidelity_ci_high": 0.90,
                "average_gate_fidelity": 0.91,
                "average_gate_fidelity_ci_low": 0.89,
                "average_gate_fidelity_ci_high": 0.93,
                "simulation_lane": "ibm_runtime_process_tomography",
            },
            {
                "dimension": 3,
                "n_physical": 2,
                "fill_ratio": 0.75,
                "delay_dt": 0,
                "process_fidelity": 0.74,
                "process_fidelity_ci_low": 0.71,
                "process_fidelity_ci_high": 0.77,
                "average_gate_fidelity": 0.81,
                "average_gate_fidelity_ci_low": 0.78,
                "average_gate_fidelity_ci_high": 0.83,
                "simulation_lane": "ibm_runtime_process_tomography",
            },
            {
                "dimension": 4,
                "n_physical": 2,
                "fill_ratio": 1.00,
                "delay_dt": 0,
                "process_fidelity": 0.63,
                "process_fidelity_ci_low": 0.61,
                "process_fidelity_ci_high": 0.65,
                "average_gate_fidelity": 0.70,
                "average_gate_fidelity_ci_low": 0.68,
                "average_gate_fidelity_ci_high": 0.72,
                "simulation_lane": "ibm_runtime_process_tomography",
            },
        ],
        n_physical=2,
    )
    return {
        "theory": theory_summary,
        "aer": aer_summary,
        "hardware": merge_fixed_n_summary_rows(
            hardware_state_summary + hardware_process_summary
        ),
    }


def test_summarize_three_lane_fixed_n_table_builds_lane_metric_rows() -> None:
    rows = summarize_three_lane_fixed_n_table(_sample_three_lane_summaries())
    assert any(row["lane"] == "theory" and row["metric"] == "fidelity" for row in rows)
    assert any(
        row["lane"] == "hardware" and row["metric"] == "process_fidelity"
        for row in rows
    )
    assert all(row["reference_dimension"] == 4 for row in rows)


def test_save_three_lane_fixed_n_markdown_report_writes_file(tmp_path: Path) -> None:
    rows = summarize_three_lane_fixed_n_table(_sample_three_lane_summaries())
    path = save_three_lane_fixed_n_markdown_report(
        rows,
        path=tmp_path / "three_lane.md",
    )
    text = path.read_text()
    assert path.exists()
    assert "Lane Overview" in text
    assert "Theory baseline" in text
    assert "IBM hardware lane" in text
    assert "preserves each lane's native delay grid" in text
    assert "structurally zero" in text
    assert "Process fidelity" in text


def _sample_multi_backend_records() -> Any:
    return [
        {
            "dimension": 2,
            "n_physical": 2,
            "fill_ratio": 0.50,
            "delay_dt": 0,
            "dt_ns": 0.0,
            "fidelity": 0.88,
            "fidelity_ci_low": 0.86,
            "fidelity_ci_high": 0.90,
            "process_fidelity": 0.87,
            "process_fidelity_ci_low": 0.84,
            "process_fidelity_ci_high": 0.90,
            "simulation_lane": "ibm_runtime_process_tomography",
            "backend_name": "ibm_fez",
        },
        {
            "dimension": 3,
            "n_physical": 2,
            "fill_ratio": 0.75,
            "delay_dt": 0,
            "dt_ns": 0.0,
            "fidelity": 0.86,
            "fidelity_ci_low": 0.85,
            "fidelity_ci_high": 0.87,
            "process_fidelity": 0.74,
            "process_fidelity_ci_low": 0.71,
            "process_fidelity_ci_high": 0.77,
            "simulation_lane": "ibm_runtime_process_tomography",
            "backend_name": "ibm_fez",
        },
        {
            "dimension": 4,
            "n_physical": 2,
            "fill_ratio": 1.00,
            "delay_dt": 0,
            "dt_ns": 0.0,
            "fidelity": 0.85,
            "fidelity_ci_low": 0.84,
            "fidelity_ci_high": 0.86,
            "process_fidelity": 0.63,
            "process_fidelity_ci_low": 0.61,
            "process_fidelity_ci_high": 0.65,
            "simulation_lane": "ibm_runtime_process_tomography",
            "backend_name": "ibm_fez",
        },
        {
            "dimension": 2,
            "n_physical": 2,
            "fill_ratio": 0.50,
            "delay_dt": 0,
            "dt_ns": 0.0,
            "fidelity": 0.90,
            "fidelity_ci_low": 0.88,
            "fidelity_ci_high": 0.92,
            "process_fidelity": 0.89,
            "process_fidelity_ci_low": 0.86,
            "process_fidelity_ci_high": 0.91,
            "simulation_lane": "ibm_runtime_process_tomography",
            "backend_name": "ibm_torino",
        },
        {
            "dimension": 3,
            "n_physical": 2,
            "fill_ratio": 0.75,
            "delay_dt": 0,
            "dt_ns": 0.0,
            "fidelity": 0.87,
            "fidelity_ci_low": 0.86,
            "fidelity_ci_high": 0.88,
            "process_fidelity": 0.76,
            "process_fidelity_ci_low": 0.73,
            "process_fidelity_ci_high": 0.79,
            "simulation_lane": "ibm_runtime_process_tomography",
            "backend_name": "ibm_torino",
        },
        {
            "dimension": 4,
            "n_physical": 2,
            "fill_ratio": 1.00,
            "delay_dt": 0,
            "dt_ns": 0.0,
            "fidelity": 0.84,
            "fidelity_ci_low": 0.83,
            "fidelity_ci_high": 0.85,
            "process_fidelity": 0.61,
            "process_fidelity_ci_low": 0.59,
            "process_fidelity_ci_high": 0.63,
            "simulation_lane": "ibm_runtime_process_tomography",
            "backend_name": "ibm_torino",
        },
    ]


def test_summarize_backend_fixed_n_comparison_preserves_backend_names() -> None:
    summary_rows = summarize_backend_fixed_n_comparison(
        _sample_multi_backend_records(),
        n_physical=2,
    )
    assert {row["backend_name"] for row in summary_rows} == {"ibm_fez", "ibm_torino"}


def test_summarize_backend_fixed_n_table_and_report_write_backend_sections(tmp_path: Path) -> None:
    summary_rows = summarize_backend_fixed_n_comparison(
        _sample_multi_backend_records(),
        n_physical=2,
    )
    rows = summarize_backend_fixed_n_table(merge_backend_fixed_n_summary_rows(summary_rows))
    assert any(row["backend_name"] == "ibm_fez" and row["metric"] == "fidelity" for row in rows)
    assert any(row["backend_name"] == "ibm_torino" and row["metric"] == "process_fidelity" for row in rows)

    path = save_backend_fixed_n_markdown_report(rows, path=tmp_path / "backends.md")
    text = path.read_text()
    assert path.exists()
    assert "Backend Overview" in text
    assert "ibm_fez" in text
    assert "ibm_torino" in text
    assert "structurally zero" in text


def test_load_backend_fixed_n_summary_rows_infers_backend_name_from_path(tmp_path: Path) -> None:
    summary = summarize_fixed_n_comparison(
        [
            {
                "dimension": 2,
                "n_physical": 2,
                "fill_ratio": 0.50,
                "delay_dt": 0,
                "fidelity": 0.90,
            },
            {
                "dimension": 3,
                "n_physical": 2,
                "fill_ratio": 0.75,
                "delay_dt": 0,
                "fidelity": 0.87,
            },
            {
                "dimension": 4,
                "n_physical": 2,
                "fill_ratio": 1.00,
                "delay_dt": 0,
                "fidelity": 0.84,
            },
        ],
        n_physical=2,
    )
    path = tmp_path / "ibm_fez_compare.json"
    path.write_text(json.dumps(summary))
    loaded = load_backend_fixed_n_summary_rows([str(path)], n_physical=2)
    assert loaded[0]["backend_name"] == "ibm_fez"


def test_summarize_hardware_theory_divergence_and_report(tmp_path: Path) -> None:
    theory_summary = _sample_three_lane_summaries()["theory"]
    hardware_summary = merge_backend_fixed_n_summary_rows(
        summarize_backend_fixed_n_comparison(_sample_multi_backend_records(), n_physical=2)
    )
    rows = summarize_hardware_theory_divergence(
        theory_summary,
        hardware_summary,
        metrics=("fidelity",),
        dimensions=(3, 4),
    )
    assert any(row["backend_name"] == "ibm_fez" and row["dimension"] == 3 for row in rows)
    assert any(row["backend_name"] == "ibm_torino" and row["dimension"] == 4 for row in rows)
    assert any("delta_hardware_minus_theory" in row for row in rows)

    path = save_hardware_theory_divergence_markdown_report(
        rows,
        path=tmp_path / "hardware_theory.md",
    )
    text = path.read_text()
    assert path.exists()
    assert "Hardware versus theory divergence" in text
    assert "ibm_fez" in text
    assert "ibm_torino" in text
    assert "Δ(H-T)" in text
