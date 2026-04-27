from __future__ import annotations

import re
from typing import Mapping

from .encoding import delay_dt_to_ns

import csv
import json
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt


def _normalize_path(path: str | Path) -> Path:
    """Filesystem or reporting helper used by the analysis and artifact pipeline."""
    return Path(path).expanduser().resolve()


def save_json(records: Sequence[dict[str, Any]], path: str | Path) -> Path:
    """Filesystem or reporting helper used by the analysis and artifact pipeline."""
    output = _normalize_path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(list(records), indent=2))
    return output


def save_csv(records: Sequence[dict[str, Any]], path: str | Path) -> Path:
    """Filesystem or reporting helper used by the analysis and artifact pipeline."""
    output = _normalize_path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for record in records:
        for key in record.keys():
            if key not in fieldnames:
                fieldnames.append(key)
    with output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow(record)
    return output


def load_json_records(path: str | Path) -> list[dict[str, Any]]:
    """Filesystem or reporting helper used by the analysis and artifact pipeline."""
    input_path = _normalize_path(path)
    return list(json.loads(input_path.read_text()))


def _infer_backend_name_from_path(path: str | Path) -> str:
    """Infer a backend label from a saved artifact path when summary rows omit one."""
    stem = _normalize_path(path).stem
    match = re.search(r"(ibm_[a-zA-Z0-9]+)", stem)
    if match is not None:
        return match.group(1)
    return stem


def _group_label(record: dict[str, Any]) -> str:
    """Filesystem or reporting helper used by the analysis and artifact pipeline."""
    parts = [f"d={record.get('dimension')}", f"n={record.get('n_physical')}"]
    fill_ratio = record.get("fill_ratio")
    if fill_ratio is not None:
        parts.append(f"phi={float(fill_ratio):.3f}")
    return ", ".join(parts)


def plot_metric_vs_delay(
    records: Sequence[dict[str, Any]],
    *,
    metric: str,
    path: str | Path,
    title: str | None = None,
) -> Path:
    """Generate a matplotlib figure for one of the thesis analysis outputs."""
    if not records:
        raise ValueError("records cannot be empty")
    use_dt_ns = all(record.get("dt_ns") is not None for record in records)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[_group_label(record)].append(record)

    fig, ax = plt.subplots(figsize=(8, 5))
    for label, group in grouped.items():
        ordered = sorted(group, key=lambda item: item.get("delay_dt", item.get("step", 0)))
        if use_dt_ns:
            xs = [float(item["dt_ns"]) for item in ordered]
        else:
            xs = [item.get("delay_dt", item.get("step", 0)) for item in ordered]
        ys = [float(item[metric]) for item in ordered]
        ax.plot(xs, ys, marker="o", label=label)
    ax.set_xlabel("delay (ns)" if use_dt_ns else "delay_dt / step")
    ax.set_ylabel(metric)
    ax.set_title(title or f"{metric} vs delay")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    output = _normalize_path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180)
    plt.close(fig)
    return output


def plot_metric_vs_fill_ratio(
    records: Sequence[dict[str, Any]],
    *,
    metric: str,
    path: str | Path,
    delay_dt: int | None = None,
    title: str | None = None,
) -> Path:
    """Generate a matplotlib figure for one of the thesis analysis outputs."""
    if not records:
        raise ValueError("records cannot be empty")
    filtered = [record for record in records if delay_dt is None or int(record.get("delay_dt", -1)) == delay_dt]
    if not filtered:
        raise ValueError("no records remain after delay filter")

    fig, ax = plt.subplots(figsize=(8, 5))
    xs = [float(record["fill_ratio"]) for record in filtered]
    ys = [float(record[metric]) for record in filtered]
    ax.plot(xs, ys, marker="o")
    ax.set_xlabel("fill_ratio")
    ax.set_ylabel(metric)
    if delay_dt is None:
        ax.set_title(title or f"{metric} vs fill ratio")
    else:
        ax.set_title(title or f"{metric} vs fill ratio at delay_dt={delay_dt}")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    output = _normalize_path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180)
    plt.close(fig)
    return output


def plot_blp_vs_memory_strength(
    records: Sequence[dict[str, Any]],
    *,
    path: str | Path,
    title: str | None = None,
) -> Path:
    """Generate a matplotlib figure for one of the thesis analysis outputs."""
    if not records:
        raise ValueError("records cannot be empty")
    ordered = sorted(records, key=lambda item: float(item["memory_strength"]))
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(
        [float(record["memory_strength"]) for record in ordered],
        [float(record["blp_measure"]) for record in ordered],
        marker="o",
    )
    ax.set_xlabel("memory_strength")
    ax.set_ylabel("blp_measure")
    ax.set_title(title or "BLP non-Markovianity vs memory strength")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    output = _normalize_path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180)
    plt.close(fig)
    return output


def plot_blp_vs_switching_probability(
    records: Sequence[dict[str, Any]],
    *,
    path: str | Path,
    title: str | None = None,
) -> Path:
    """Plot BLP non-Markovianity against the random-telegraph switching probability."""
    if not records:
        raise ValueError("records cannot be empty")
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[_group_label(record)].append(record)

    fig, ax = plt.subplots(figsize=(8, 5))
    for label, group in grouped.items():
        ordered = sorted(group, key=lambda item: float(item["switching_probability"]))
        ax.plot(
            [float(record["switching_probability"]) for record in ordered],
            [float(record["blp_measure"]) for record in ordered],
            marker="o",
            label=label,
        )
    ax.set_xlabel("switching_probability")
    ax.set_ylabel("blp_measure")
    ax.set_title(title or "BLP non-Markovianity vs switching probability")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    output = _normalize_path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180)
    plt.close(fig)
    return output


def summarize_fixed_n_comparison(
    records: Sequence[dict[str, Any]],
    *,
    n_physical: int,
    metric_keys: Sequence[str] = (
        "fidelity",
        "leakage",
        "in_subspace_fidelity",
        "process_fidelity",
        "average_gate_fidelity",
    ),
    dt_ns_per_dt: float | None = None,
) -> list[dict[str, Any]]:
    """Build or parse structured comparison summaries for fixed-n analysis reports."""
    filtered = [record for record in records if int(record.get("n_physical", -1)) == n_physical]
    if not filtered:
        raise ValueError(f"no records found for n_physical={n_physical}")

    delays = sorted({int(record.get("delay_dt", 0)) for record in filtered})
    dimensions = sorted({int(record["dimension"]) for record in filtered})
    reference_dimension = max(dimensions)
    summary: list[dict[str, Any]] = []
    for delay in delays:
        row: dict[str, Any] = {
            "n_physical": n_physical,
            "delay_dt": delay,
            "dt_ns": delay_dt_to_ns(delay, dt_ns_per_dt=dt_ns_per_dt),
        }
        delay_records = [
            record for record in filtered if int(record.get("delay_dt", 0)) == delay
        ]
        source_lanes = sorted(
            {
                str(record.get("simulation_lane"))
                for record in delay_records
                if record.get("simulation_lane") is not None
            }
        )
        if source_lanes:
            row["source_simulation_lanes"] = ",".join(source_lanes)
        backend_names = sorted(
            {
                str(record.get("backend_name"))
                for record in delay_records
                if record.get("backend_name") not in {None, ""}
            }
        )
        if len(backend_names) == 1:
            row["backend_name"] = backend_names[0]
        elif backend_names:
            row["source_backend_names"] = ",".join(backend_names)
        contains_theory_baseline = any(
            record.get("simulation_lane") == "markovian_model" for record in delay_records
        )
        contains_explicit_theory_mixing = any(
            record.get("simulation_lane") == "markovian_model"
            and (
                (
                    record.get("t_dep") is not None
                    and float(record.get("t_dep", 0.0)) > 0.0
                )
                or (
                    record.get("depolarizing_probability") is not None
                    and float(record.get("depolarizing_probability", 0.0)) > 0.0
                )
            )
            for record in delay_records
        )
        row["contains_theory_baseline"] = contains_theory_baseline
        row["contains_explicit_theory_mixing"] = contains_explicit_theory_mixing
        by_dimension: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for record in filtered:
            if int(record.get("delay_dt", 0)) == delay:
                by_dimension[int(record["dimension"])].append(record)
        for dimension in dimensions:
            matching_records = by_dimension.get(dimension, [])
            if not matching_records:
                continue
            record = _merge_summary_source_records(matching_records)
            row[_summary_fill_ratio_key(dimension)] = float(record["fill_ratio"])
            if row["dt_ns"] is None and record.get("dt_ns") is not None:
                row["dt_ns"] = float(record["dt_ns"])
            for key in metric_keys:
                if key in record:
                    row[_summary_metric_key(dimension, key)] = float(record[key])
                bounds = _metric_confidence_interval_bounds(record, key)
                if bounds is not None:
                    row[_summary_metric_ci_key(dimension, key, "low")] = bounds[0]
                    row[_summary_metric_ci_key(dimension, key, "high")] = bounds[1]
        for dimension in dimensions:
            if dimension == reference_dimension:
                continue
            for key in metric_keys:
                ka = _summary_metric_key(dimension, key)
                kb = _summary_metric_key(reference_dimension, key)
                if ka in row and kb in row:
                    row[_summary_delta_key(reference_dimension, dimension, key)] = row[kb] - row[ka]
                    bounds_a = _summary_metric_ci_bounds_from_row(row, dimension, key)
                    bounds_b = _summary_metric_ci_bounds_from_row(row, reference_dimension, key)
                    if bounds_a is not None and bounds_b is not None:
                        row[_summary_significant_key(reference_dimension, dimension, key)] = _intervals_do_not_overlap(
                            bounds_b,
                            bounds_a,
                        )
        summary.append(row)
    return summary


def _summary_fill_ratio_key(dimension: int) -> str:
    """Build or parse structured comparison summaries for fixed-n analysis reports."""
    return f"d{dimension}|fill_ratio"



def _summary_metric_key(dimension: int, metric: str) -> str:
    """Build or parse structured comparison summaries for fixed-n analysis reports."""
    return f"d{dimension}|metric|{metric}"


def _summary_metric_ci_key(dimension: int, metric: str, bound: str) -> str:
    """Build the structured key used for per-dimension confidence intervals."""
    return f"d{dimension}|metric_ci|{metric}|{bound}"



def _summary_delta_key(reference_dimension: int, dimension: int, metric: str) -> str:
    """Build or parse structured comparison summaries for fixed-n analysis reports."""
    return f"delta|d{reference_dimension}-d{dimension}|metric|{metric}"


def _summary_significant_key(reference_dimension: int, dimension: int, metric: str) -> str:
    """Build the structured key used for report-level significance booleans."""
    return f"significant|d{reference_dimension}-d{dimension}|metric|{metric}"


def _merge_summary_source_records(records: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Merge multiple records for the same dimension/delay into one comparison source."""
    merged: dict[str, Any] = {}
    for record in records:
        for key, value in record.items():
            if value is None:
                continue
            merged[key] = value
    return merged


def _metric_confidence_interval_bounds(record: dict[str, Any], metric: str) -> tuple[float, float] | None:
    """Extract a confidence interval for a headline metric when a record exposes one."""
    for prefix in (metric, f"avg_probe_{metric}"):
        low_key = f"{prefix}_ci_low"
        high_key = f"{prefix}_ci_high"
        if low_key in record and high_key in record:
            return float(record[low_key]), float(record[high_key])
    return None


def _summary_metric_ci_bounds_from_row(
    row: dict[str, Any],
    dimension: int,
    metric: str,
) -> tuple[float, float] | None:
    """Extract a per-dimension confidence interval from a summary row."""
    low_key = _summary_metric_ci_key(dimension, metric, "low")
    high_key = _summary_metric_ci_key(dimension, metric, "high")
    if low_key in row and high_key in row:
        return float(row[low_key]), float(row[high_key])
    return None


def _intervals_do_not_overlap(
    left: tuple[float, float],
    right: tuple[float, float],
) -> bool:
    """Return whether two confidence intervals are separated."""
    return float(left[0]) > float(right[1]) or float(right[0]) > float(left[1])



def _parse_summary_key(key: str) -> tuple[str, int | None, int | None, str | None]:
    """Build or parse structured comparison summaries for fixed-n analysis reports."""
    parts = key.split("|")
    if len(parts) == 2 and parts[0].startswith("d") and parts[0][1:].isdigit() and parts[1] == "fill_ratio":
        return ("fill_ratio", int(parts[0][1:]), None, None)
    if len(parts) == 3 and parts[0].startswith("d") and parts[0][1:].isdigit() and parts[1] == "metric":
        return ("metric", int(parts[0][1:]), None, parts[2])
    if len(parts) == 4 and parts[0].startswith("d") and parts[0][1:].isdigit() and parts[1] == "metric_ci":
        return ("metric_ci", int(parts[0][1:]), None, parts[2])
    if len(parts) == 4 and parts[0] == "delta" and parts[1].startswith("d") and "-d" in parts[1] and parts[2] == "metric":
        ref_part, other_part = parts[1].split("-d", 1)
        if ref_part[1:].isdigit() and other_part.isdigit():
            return ("delta", int(ref_part[1:]), int(other_part), parts[3])
    if len(parts) == 4 and parts[0] == "significant" and parts[1].startswith("d") and "-d" in parts[1] and parts[2] == "metric":
        ref_part, other_part = parts[1].split("-d", 1)
        if ref_part[1:].isdigit() and other_part.isdigit():
            return ("significant", int(ref_part[1:]), int(other_part), parts[3])
    return ("other", None, None, None)


_THREE_LANE_METRIC_ORDER = (
    "fidelity",
    "leakage",
    "in_subspace_fidelity",
    "process_fidelity",
    "average_gate_fidelity",
)

_THREE_LANE_LANE_ORDER = ("theory", "aer", "hardware")

_THREE_LANE_LANE_LABELS = {
    "theory": "Theory baseline",
    "aer": "Aer circuit lane",
    "hardware": "IBM hardware lane",
}


def _is_fixed_n_summary_row(record: dict[str, Any]) -> bool:
    """Return whether a JSON record already looks like a fixed-n comparison summary row."""
    return any(
        _parse_summary_key(key)[0] in {"fill_ratio", "metric", "metric_ci", "delta", "significant"}
        for key in record.keys()
    )


def merge_fixed_n_summary_rows(summary_rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge fixed-n comparison summary rows that share the same physical-qubit count and delay."""
    grouped: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    for row in summary_rows:
        grouped[(int(row.get("n_physical", -1)), int(row.get("delay_dt", 0)))].append(row)

    merged_rows: list[dict[str, Any]] = []
    for key in sorted(grouped.keys()):
        group = grouped[key]
        merged = _merge_summary_source_records(group)
        source_lanes = sorted(
            {
                lane.strip()
                for row in group
                for lane in str(row.get("source_simulation_lanes", "")).split(",")
                if lane.strip()
            }
        )
        if source_lanes:
            merged["source_simulation_lanes"] = ",".join(source_lanes)
        merged["contains_theory_baseline"] = any(
            bool(row.get("contains_theory_baseline")) for row in group
        )
        merged["contains_explicit_theory_mixing"] = any(
            bool(row.get("contains_explicit_theory_mixing")) for row in group
        )
        merged_rows.append(merged)
    return merged_rows


def summarize_backend_fixed_n_comparison(
    records: Sequence[dict[str, Any]],
    *,
    n_physical: int,
    metric_keys: Sequence[str] = (
        "fidelity",
        "leakage",
        "in_subspace_fidelity",
        "process_fidelity",
        "average_gate_fidelity",
    ),
    dt_ns_per_dt: float | None = None,
    backend_field: str = "backend_name",
) -> list[dict[str, Any]]:
    """Build fixed-n comparison summaries separately for each hardware backend."""
    filtered = [record for record in records if int(record.get("n_physical", -1)) == n_physical]
    if not filtered:
        raise ValueError(f"no records found for n_physical={n_physical}")

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in filtered:
        backend_name = str(record.get(backend_field) or "unknown_backend")
        grouped[backend_name].append(record)

    summary_rows: list[dict[str, Any]] = []
    for backend_name in sorted(grouped):
        rows = summarize_fixed_n_comparison(
            grouped[backend_name],
            n_physical=n_physical,
            metric_keys=metric_keys,
            dt_ns_per_dt=dt_ns_per_dt,
        )
        for row in rows:
            row["backend_name"] = backend_name
        summary_rows.extend(rows)
    return summary_rows


def merge_backend_fixed_n_summary_rows(summary_rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge fixed-n summary rows while preserving backend identity."""
    grouped: dict[tuple[str, int, int], list[dict[str, Any]]] = defaultdict(list)
    for row in summary_rows:
        grouped[
            (
                str(row.get("backend_name") or "unknown_backend"),
                int(row.get("n_physical", -1)),
                int(row.get("delay_dt", 0)),
            )
        ].append(row)

    merged_rows: list[dict[str, Any]] = []
    for key in sorted(grouped.keys()):
        group = grouped[key]
        merged = _merge_summary_source_records(group)
        source_lanes = sorted(
            {
                lane.strip()
                for row in group
                for lane in str(row.get("source_simulation_lanes", "")).split(",")
                if lane.strip()
            }
        )
        if source_lanes:
            merged["source_simulation_lanes"] = ",".join(source_lanes)
        merged["backend_name"] = key[0]
        merged["contains_theory_baseline"] = any(
            bool(row.get("contains_theory_baseline")) for row in group
        )
        merged["contains_explicit_theory_mixing"] = any(
            bool(row.get("contains_explicit_theory_mixing")) for row in group
        )
        merged_rows.append(merged)
    return merged_rows


def load_backend_fixed_n_summary_rows(
    input_paths: Sequence[str],
    *,
    n_physical: int,
    dt_ns_per_dt: float | None = None,
) -> list[dict[str, Any]]:
    """Load raw or summary fixed-n hardware records and preserve backend grouping."""
    raw_records: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    for path in input_paths:
        records = load_json_records(path)
        if not records:
            continue
        if all(_is_fixed_n_summary_row(record) for record in records):
            inferred_backend_name = _infer_backend_name_from_path(path)
            for record in records:
                if not record.get("backend_name") and not record.get("source_backend_names"):
                    record["backend_name"] = inferred_backend_name
            summary_rows.extend(records)
        else:
            raw_records.extend(records)

    if raw_records:
        summary_rows.extend(
            summarize_backend_fixed_n_comparison(
                raw_records,
                n_physical=n_physical,
                dt_ns_per_dt=dt_ns_per_dt,
            )
        )

    filtered_rows = [
        row for row in summary_rows if int(row.get("n_physical", -1)) == n_physical
    ]
    if not filtered_rows:
        raise ValueError(f"no backend-aware fixed-n comparison rows found for n_physical={n_physical}")
    return merge_backend_fixed_n_summary_rows(filtered_rows)


def summarize_backend_fixed_n_table(
    summary_rows: Sequence[dict[str, Any]],
    *,
    metric_order: Sequence[str] = (
        "fidelity",
        "leakage",
        "in_subspace_fidelity",
        "process_fidelity",
        "average_gate_fidelity",
    ),
) -> list[dict[str, Any]]:
    """Build tidy fixed-n comparison rows grouped by hardware backend."""
    if not summary_rows:
        raise ValueError("summary_rows cannot be empty")

    dimensions = sorted(
        {
            dimension
            for row in summary_rows
            for key in row.keys()
            for kind, dimension, _, _ in [_parse_summary_key(key)]
            if kind in {"fill_ratio", "metric"} and dimension is not None
        }
    )
    if not dimensions:
        raise ValueError("summary rows do not expose any fixed-n dimensions")
    reference_dimension = max(dimensions)
    comparison_dimension = dimensions[-2] if len(dimensions) >= 2 else reference_dimension

    backend_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in summary_rows:
        backend_groups[str(row.get("backend_name") or "unknown_backend")].append(row)

    rows: list[dict[str, Any]] = []
    for backend_index, backend_name in enumerate(sorted(backend_groups)):
        group = sorted(
            backend_groups[backend_name],
            key=lambda row: (
                float(row["dt_ns"]) if row.get("dt_ns") is not None else float("inf"),
                int(row.get("delay_dt", 0)),
            ),
        )
        for summary_row in group:
            available_metrics = [
                metric
                for metric in metric_order
                if any(_summary_metric_key(dim, metric) in summary_row for dim in dimensions)
            ]
            for metric in available_metrics:
                output_row: dict[str, Any] = {
                    "backend_name": backend_name,
                    "backend_label": backend_name,
                    "backend_order": backend_index,
                    "n_physical": int(summary_row["n_physical"]),
                    "delay_dt": int(summary_row.get("delay_dt", 0)),
                    "dt_ns": summary_row.get("dt_ns"),
                    "metric": metric,
                    "dimensions": ",".join(str(dim) for dim in dimensions),
                    "reference_dimension": reference_dimension,
                    "comparison_dimension": comparison_dimension,
                    "source_simulation_lanes": summary_row.get("source_simulation_lanes"),
                }
                for dim in dimensions:
                    fill_key = _summary_fill_ratio_key(dim)
                    metric_key = _summary_metric_key(dim, metric)
                    if fill_key in summary_row:
                        output_row[f"d{dim}_fill_ratio"] = float(summary_row[fill_key])
                    if metric_key in summary_row:
                        output_row[f"d{dim}_value"] = float(summary_row[metric_key])
                    ci_bounds = _summary_metric_ci_bounds_from_row(summary_row, dim, metric)
                    if ci_bounds is not None:
                        output_row[f"d{dim}_ci_low"] = ci_bounds[0]
                        output_row[f"d{dim}_ci_high"] = ci_bounds[1]
                for dim in dimensions:
                    if dim == reference_dimension:
                        continue
                    delta_key = _summary_delta_key(reference_dimension, dim, metric)
                    significance_key = _summary_significant_key(reference_dimension, dim, metric)
                    if delta_key in summary_row:
                        output_row[f"delta_d{reference_dimension}_minus_d{dim}"] = float(
                            summary_row[delta_key]
                        )
                    if significance_key in summary_row:
                        output_row[f"significant_d{reference_dimension}_minus_d{dim}"] = bool(
                            summary_row[significance_key]
                        )
                rows.append(output_row)

    rows.sort(
        key=lambda row: (
            metric_order.index(str(row["metric"]))
            if str(row["metric"]) in metric_order
            else len(metric_order),
            int(row["backend_order"]),
            int(row["delay_dt"]),
        )
    )
    return rows


def save_backend_fixed_n_markdown_report(
    rows: Sequence[dict[str, Any]],
    *,
    path: str | Path,
    title: str = "Multi-backend fixed-n comparison",
) -> Path:
    """Write one markdown report that compares fixed-n results across hardware backends."""
    if not rows:
        raise ValueError("rows cannot be empty")

    reference_dimension = int(rows[0]["reference_dimension"])
    comparison_dimension = int(rows[0]["comparison_dimension"])
    dimensions = [int(item) for item in str(rows[0]["dimensions"]).split(",") if item]
    control_dimension = min(dimensions)
    backend_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        backend_groups[str(row["backend_name"])].append(row)

    metric_order = [
        metric for metric in _THREE_LANE_METRIC_ORDER if any(row["metric"] == metric for row in rows)
    ]

    lines = [f"# {title}", ""]
    lines.extend(
        [
            "## Scope",
            "",
            "- This report groups fixed-n hardware summaries by backend rather than collapsing them into one device-agnostic lane.",
            "- State- and process-tomography summaries for the same backend and delay are merged before reporting.",
            "- For the full-fill-ratio case (here d=4, phi=1.000), leakage is structurally zero because no unused Hilbert-space states remain. Treat any reported L=0.000 in that column as definitional rather than as an independently measured absence of noise.",
            "",
            "## Backend Overview",
            "",
            "| Backend | Delay grid | Metrics | d4-d3 fidelity sig | d4-d3 process sig |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for backend_name in sorted(backend_groups):
        group = backend_groups[backend_name]
        metrics = ", ".join(
            metric for metric in metric_order if any(row["metric"] == metric for row in group)
        )
        lines.append(
            "| "
            + " | ".join(
                [
                    backend_name,
                    _three_lane_format_delay_grid(group),
                    metrics or "—",
                    _three_lane_format_significance_count(
                        group,
                        metric="fidelity",
                        reference_dimension=reference_dimension,
                        dimension=comparison_dimension,
                    ),
                    _three_lane_format_significance_count(
                        group,
                        metric="process_fidelity",
                        reference_dimension=reference_dimension,
                        dimension=comparison_dimension,
                    ),
                ]
            )
            + " |"
        )
    lines.append("")

    for metric in metric_order:
        metric_rows = [
            row
            for backend_name in sorted(backend_groups)
            for row in sorted(
                backend_groups[backend_name],
                key=lambda item: int(item["delay_dt"]),
            )
            if row["metric"] == metric
        ]
        if not metric_rows:
            continue
        lines.extend(
            [
                f"## {_three_lane_metric_title(metric)}",
                "",
                f"| Backend | delay_dt | dt_ns | d{control_dimension} | d{comparison_dimension} | d{reference_dimension} | Δ(d{reference_dimension}-d{comparison_dimension}) | sig | Δ(d{reference_dimension}-d{control_dimension}) | sig |",
                "| --- | ---: | ---: | --- | --- | --- | ---: | --- | ---: | --- |",
            ]
        )
        for row in metric_rows:
            dt_ns = row.get("dt_ns")
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(row["backend_name"]),
                        str(int(row["delay_dt"])),
                        f"{float(dt_ns):.3f}" if dt_ns is not None else "—",
                        _three_lane_format_metric_value(row, control_dimension),
                        _three_lane_format_metric_value(row, comparison_dimension),
                        _three_lane_format_metric_value(row, reference_dimension),
                        _three_lane_format_delta(row, reference_dimension, comparison_dimension),
                        _three_lane_format_significance(row, reference_dimension, comparison_dimension),
                        _three_lane_format_delta(row, reference_dimension, control_dimension),
                        _three_lane_format_significance(row, reference_dimension, control_dimension),
                    ]
                )
                + " |"
            )
        lines.append("")

    output = _normalize_path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines).rstrip() + "\n")
    return output


def summarize_hardware_theory_divergence(
    theory_summary_rows: Sequence[dict[str, Any]],
    hardware_summary_rows: Sequence[dict[str, Any]],
    *,
    metrics: Sequence[str] = ("fidelity", "leakage", "in_subspace_fidelity"),
    dimensions: Sequence[int] | None = None,
) -> list[dict[str, Any]]:
    """Compare hardware fixed-n summaries against a shared-delay theory baseline."""
    if not theory_summary_rows:
        raise ValueError("theory_summary_rows cannot be empty")
    if not hardware_summary_rows:
        raise ValueError("hardware_summary_rows cannot be empty")

    theory_by_delay = {
        int(row.get("delay_dt", 0)): row
        for row in theory_summary_rows
    }
    hardware_by_backend: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in hardware_summary_rows:
        hardware_by_backend[str(row.get("backend_name") or "unknown_backend")].append(row)

    if dimensions is None:
        resolved_dimensions = sorted(
            {
                dimension
                for row in theory_summary_rows
                for key in row.keys()
                for kind, dimension, _, _ in [_parse_summary_key(key)]
                if kind in {"fill_ratio", "metric"} and dimension is not None
            }
        )
    else:
        resolved_dimensions = sorted(int(dimension) for dimension in dimensions)
    if not resolved_dimensions:
        raise ValueError("no dimensions available for theory-vs-hardware divergence")

    rows: list[dict[str, Any]] = []
    for backend_name in sorted(hardware_by_backend):
        for hardware_row in sorted(
            hardware_by_backend[backend_name],
            key=lambda row: int(row.get("delay_dt", 0)),
        ):
            theory_row = theory_by_delay.get(int(hardware_row.get("delay_dt", 0)))
            if theory_row is None:
                continue
            for metric in metrics:
                for dimension in resolved_dimensions:
                    theory_key = _summary_metric_key(dimension, metric)
                    hardware_key = _summary_metric_key(dimension, metric)
                    if theory_key not in theory_row or hardware_key not in hardware_row:
                        continue
                    theory_value = float(theory_row[theory_key])
                    hardware_value = float(hardware_row[hardware_key])
                    theory_ci = _summary_metric_ci_bounds_from_row(theory_row, dimension, metric)
                    hardware_ci = _summary_metric_ci_bounds_from_row(hardware_row, dimension, metric)
                    output_row: dict[str, Any] = {
                        "backend_name": backend_name,
                        "n_physical": int(hardware_row["n_physical"]),
                        "delay_dt": int(hardware_row.get("delay_dt", 0)),
                        "dt_ns": hardware_row.get("dt_ns", theory_row.get("dt_ns")),
                        "metric": metric,
                        "dimension": dimension,
                        "fill_ratio": hardware_row.get(
                            _summary_fill_ratio_key(dimension),
                            theory_row.get(_summary_fill_ratio_key(dimension)),
                        ),
                        "theory_value": theory_value,
                        "hardware_value": hardware_value,
                        "delta_hardware_minus_theory": hardware_value - theory_value,
                    }
                    if theory_ci is not None:
                        output_row["theory_ci_low"] = theory_ci[0]
                        output_row["theory_ci_high"] = theory_ci[1]
                    if hardware_ci is not None:
                        output_row["hardware_ci_low"] = hardware_ci[0]
                        output_row["hardware_ci_high"] = hardware_ci[1]
                    if theory_ci is not None and hardware_ci is not None:
                        output_row["significant"] = _intervals_do_not_overlap(hardware_ci, theory_ci)
                    rows.append(output_row)

    if not rows:
        raise ValueError("no overlapping theory/hardware metric rows found")
    return rows


def save_hardware_theory_divergence_markdown_report(
    rows: Sequence[dict[str, Any]],
    *,
    path: str | Path,
    title: str = "Hardware versus theory divergence",
) -> Path:
    """Write one markdown report comparing hardware data against the theory baseline."""
    if not rows:
        raise ValueError("rows cannot be empty")

    dimensions = sorted({int(row["dimension"]) for row in rows})
    metrics = [
        metric for metric in _THREE_LANE_METRIC_ORDER if any(row["metric"] == metric for row in rows)
    ]
    backend_names = sorted({str(row["backend_name"]) for row in rows})

    lines = [f"# {title}", ""]
    lines.extend(
        [
            "## Scope",
            "",
            "- This report compares hardware observables against the effective theory baseline on the shared delay grid.",
            "- Only metrics exposed by both sources are shown. In practice, the theory lane contributes fidelity, leakage, and in-subspace fidelity, but not process fidelity.",
            "- Positive Δ(H-T) means the hardware value exceeds the theory prediction; negative Δ(H-T) means the hardware value falls below the theory curve.",
            "",
            "## Backend Overview",
            "",
            f"- backends: {', '.join(backend_names)}",
            f"- dimensions: {', '.join(f'd={dimension}' for dimension in dimensions)}",
            "",
        ]
    )

    for metric in metrics:
        metric_rows = [row for row in rows if row["metric"] == metric]
        if not metric_rows:
            continue
        lines.extend(
            [
                f"## {_three_lane_metric_title(metric)}",
                "",
                "| Backend | delay_dt | dt_ns | dimension | theory | hardware | Δ(H-T) | sig |",
                "| --- | ---: | ---: | ---: | --- | --- | ---: | --- |",
            ]
        )
        for row in sorted(
            metric_rows,
            key=lambda item: (str(item["backend_name"]), int(item["dimension"]), int(item["delay_dt"])),
        ):
            theory_text = f"{float(row['theory_value']):.6f}"
            if row.get("theory_ci_low") is not None and row.get("theory_ci_high") is not None:
                theory_text = (
                    f"{float(row['theory_value']):.6f} "
                    f"[{float(row['theory_ci_low']):.6f}, {float(row['theory_ci_high']):.6f}]"
                )
            hardware_text = f"{float(row['hardware_value']):.6f}"
            if row.get("hardware_ci_low") is not None and row.get("hardware_ci_high") is not None:
                hardware_text = (
                    f"{float(row['hardware_value']):.6f} "
                    f"[{float(row['hardware_ci_low']):.6f}, {float(row['hardware_ci_high']):.6f}]"
                )
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(row["backend_name"]),
                        str(int(row["delay_dt"])),
                        f"{float(row['dt_ns']):.3f}" if row.get("dt_ns") is not None else "—",
                        str(int(row["dimension"])),
                        theory_text,
                        hardware_text,
                        f"{float(row['delta_hardware_minus_theory']):+.6f}",
                        "yes" if bool(row.get("significant")) else "overlap",
                    ]
                )
                + " |"
            )
        lines.append("")

    output = _normalize_path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines).rstrip() + "\n")
    return output


def plot_hardware_theory_curves(
    rows: Sequence[dict[str, Any]],
    *,
    metric: str,
    dimension: int,
    path: str | Path,
    title: str | None = None,
) -> Path:
    """Plot theory and hardware curves for one metric and logical dimension."""
    filtered = [
        row for row in rows if str(row["metric"]) == metric and int(row["dimension"]) == int(dimension)
    ]
    if not filtered:
        raise ValueError("no rows remain after metric/dimension filter")

    use_dt_ns = all(row.get("dt_ns") is not None for row in filtered)
    fig, ax = plt.subplots(figsize=(8, 5))

    theory_points = sorted(
        {
            (
                float(row["dt_ns"]) if use_dt_ns else float(row["delay_dt"]),
                float(row["theory_value"]),
            )
            for row in filtered
        }
    )
    ax.plot(
        [point[0] for point in theory_points],
        [point[1] for point in theory_points],
        linestyle="--",
        color="black",
        linewidth=2.0,
        label="theory",
    )

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in filtered:
        grouped[str(row["backend_name"])].append(row)
    for backend_name, group in sorted(grouped.items()):
        ordered = sorted(group, key=lambda row: int(row["delay_dt"]))
        xs = [
            float(row["dt_ns"]) if use_dt_ns else float(row["delay_dt"])
            for row in ordered
        ]
        ys = [float(row["hardware_value"]) for row in ordered]
        ax.plot(xs, ys, marker="o", label=backend_name)

    ax.set_xlabel("delay (ns)" if use_dt_ns else "delay_dt")
    ax.set_ylabel(metric)
    ax.set_title(title or f"Hardware vs theory: {metric}, d={dimension}")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    output = _normalize_path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180)
    plt.close(fig)
    return output


def plot_hardware_theory_divergence(
    rows: Sequence[dict[str, Any]],
    *,
    metric: str,
    dimension: int,
    path: str | Path,
    title: str | None = None,
) -> Path:
    """Plot hardware-minus-theory divergence for one metric and logical dimension."""
    filtered = [
        row for row in rows if str(row["metric"]) == metric and int(row["dimension"]) == int(dimension)
    ]
    if not filtered:
        raise ValueError("no rows remain after metric/dimension filter")

    use_dt_ns = all(row.get("dt_ns") is not None for row in filtered)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in filtered:
        grouped[str(row["backend_name"])].append(row)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.axhline(0.0, color="black", linewidth=1.0, linestyle="--")
    for backend_name, group in sorted(grouped.items()):
        ordered = sorted(group, key=lambda row: int(row["delay_dt"]))
        xs = [
            float(row["dt_ns"]) if use_dt_ns else float(row["delay_dt"])
            for row in ordered
        ]
        ys = [float(row["delta_hardware_minus_theory"]) for row in ordered]
        ax.plot(xs, ys, marker="o", label=backend_name)

    ax.set_xlabel("delay (ns)" if use_dt_ns else "delay_dt")
    ax.set_ylabel("hardware - theory")
    ax.set_title(title or f"Hardware-theory divergence: {metric}, d={dimension}")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    output = _normalize_path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180)
    plt.close(fig)
    return output


def load_fixed_n_summary_rows(
    input_paths: Sequence[str],
    *,
    n_physical: int,
    dt_ns_per_dt: float | None = None,
) -> list[dict[str, Any]]:
    """Load one or more fixed-n summary or raw-record JSON files and normalize them to summary rows."""
    raw_records: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    for path in input_paths:
        records = load_json_records(path)
        if not records:
            continue
        if all(_is_fixed_n_summary_row(record) for record in records):
            summary_rows.extend(records)
        else:
            raw_records.extend(records)

    if raw_records:
        summary_rows.extend(
            summarize_fixed_n_comparison(
                raw_records,
                n_physical=n_physical,
                dt_ns_per_dt=dt_ns_per_dt,
            )
        )

    filtered_rows = [
        row for row in summary_rows if int(row.get("n_physical", -1)) == n_physical
    ]
    if not filtered_rows:
        raise ValueError(f"no fixed-n comparison rows found for n_physical={n_physical}")
    return merge_fixed_n_summary_rows(filtered_rows)


def summarize_three_lane_fixed_n_table(
    lane_summaries: Mapping[str, Sequence[dict[str, Any]]],
    *,
    lane_labels: Mapping[str, str] | None = None,
    metric_order: Sequence[str] = _THREE_LANE_METRIC_ORDER,
) -> list[dict[str, Any]]:
    """Build tidy rows for a three-lane fixed-n comparison report."""
    if not lane_summaries:
        raise ValueError("lane_summaries cannot be empty")

    resolved_lane_labels = dict(_THREE_LANE_LANE_LABELS)
    if lane_labels is not None:
        resolved_lane_labels.update(lane_labels)

    dimensions = sorted(
        {
            dimension
            for rows in lane_summaries.values()
            for row in rows
            for key in row.keys()
            for kind, dimension, _, _ in [_parse_summary_key(key)]
            if kind in {"fill_ratio", "metric"} and dimension is not None
        }
    )
    if not dimensions:
        raise ValueError("lane summaries do not expose any fixed-n dimensions")
    reference_dimension = max(dimensions)
    comparison_dimension = dimensions[-2] if len(dimensions) >= 2 else reference_dimension

    lane_order = list(_THREE_LANE_LANE_ORDER) + sorted(
        lane for lane in lane_summaries.keys() if lane not in _THREE_LANE_LANE_ORDER
    )
    lane_index = {lane: idx for idx, lane in enumerate(lane_order)}

    rows: list[dict[str, Any]] = []
    for lane in lane_order:
        if lane not in lane_summaries:
            continue
        summary_rows = sorted(
            lane_summaries[lane],
            key=lambda row: (
                float(row["dt_ns"]) if row.get("dt_ns") is not None else float("inf"),
                int(row.get("delay_dt", 0)),
            ),
        )
        for summary_row in summary_rows:
            available_metrics = [
                metric
                for metric in metric_order
                if any(_summary_metric_key(dim, metric) in summary_row for dim in dimensions)
            ]
            for metric in available_metrics:
                row: dict[str, Any] = {
                    "lane": lane,
                    "lane_label": resolved_lane_labels.get(lane, lane.replace("_", " ").title()),
                    "lane_order": lane_index[lane],
                    "n_physical": int(summary_row["n_physical"]),
                    "delay_dt": int(summary_row.get("delay_dt", 0)),
                    "dt_ns": summary_row.get("dt_ns"),
                    "metric": metric,
                    "dimensions": ",".join(str(dim) for dim in dimensions),
                    "reference_dimension": reference_dimension,
                    "comparison_dimension": comparison_dimension,
                    "source_simulation_lanes": summary_row.get("source_simulation_lanes"),
                    "contains_theory_baseline": bool(summary_row.get("contains_theory_baseline")),
                    "contains_explicit_theory_mixing": bool(
                        summary_row.get("contains_explicit_theory_mixing")
                    ),
                }
                for dim in dimensions:
                    fill_key = _summary_fill_ratio_key(dim)
                    metric_key = _summary_metric_key(dim, metric)
                    if fill_key in summary_row:
                        row[f"d{dim}_fill_ratio"] = float(summary_row[fill_key])
                    if metric_key in summary_row:
                        row[f"d{dim}_value"] = float(summary_row[metric_key])
                    ci_bounds = _summary_metric_ci_bounds_from_row(summary_row, dim, metric)
                    if ci_bounds is not None:
                        row[f"d{dim}_ci_low"] = ci_bounds[0]
                        row[f"d{dim}_ci_high"] = ci_bounds[1]
                for dim in dimensions:
                    if dim == reference_dimension:
                        continue
                    delta_key = _summary_delta_key(reference_dimension, dim, metric)
                    significance_key = _summary_significant_key(reference_dimension, dim, metric)
                    if delta_key in summary_row:
                        row[f"delta_d{reference_dimension}_minus_d{dim}"] = float(
                            summary_row[delta_key]
                        )
                    if significance_key in summary_row:
                        row[f"significant_d{reference_dimension}_minus_d{dim}"] = bool(
                            summary_row[significance_key]
                        )
                rows.append(row)

    rows.sort(
        key=lambda row: (
            metric_order.index(str(row["metric"]))
            if str(row["metric"]) in metric_order
            else len(metric_order),
            int(row["lane_order"]),
            int(row["delay_dt"]),
        )
    )
    return rows


def _three_lane_metric_title(metric: str) -> str:
    """Return a readable markdown section title for a three-lane comparison metric."""
    titles = {
        "fidelity": "State fidelity",
        "leakage": "Leakage",
        "in_subspace_fidelity": "In-subspace fidelity",
        "process_fidelity": "Process fidelity",
        "average_gate_fidelity": "Average gate fidelity",
    }
    return titles.get(metric, metric.replace("_", " "))


def _three_lane_format_metric_value(row: dict[str, Any], dimension: int) -> str:
    """Format one dimension-specific value and its confidence interval for markdown tables."""
    value = row.get(f"d{dimension}_value")
    if value is None:
        return "—"
    ci_low = row.get(f"d{dimension}_ci_low")
    ci_high = row.get(f"d{dimension}_ci_high")
    if ci_low is None or ci_high is None:
        return f"{float(value):.6f}"
    return f"{float(value):.6f} [{float(ci_low):.6f}, {float(ci_high):.6f}]"


def _three_lane_format_delta(row: dict[str, Any], reference_dimension: int, dimension: int) -> str:
    """Format a comparison delta cell for the markdown report."""
    value = row.get(f"delta_d{reference_dimension}_minus_d{dimension}")
    if value is None:
        return "—"
    return f"{float(value):+.6f}"


def _three_lane_format_significance(row: dict[str, Any], reference_dimension: int, dimension: int) -> str:
    """Format the CI-separation flag for the markdown report."""
    value = row.get(f"significant_d{reference_dimension}_minus_d{dimension}")
    if value is None:
        return "—"
    return "yes" if bool(value) else "overlap"


def _three_lane_format_delay_grid(rows: Sequence[dict[str, Any]]) -> str:
    """Format the native delay grid used by one lane."""
    seen: set[tuple[int, float | None]] = set()
    ordered_pairs: list[tuple[int, float | None]] = []
    for row in sorted(rows, key=lambda item: int(item["delay_dt"])):
        pair = (
            int(row["delay_dt"]),
            float(row["dt_ns"]) if row.get("dt_ns") is not None else None,
        )
        if pair in seen:
            continue
        seen.add(pair)
        ordered_pairs.append(pair)
    parts = []
    for delay_dt, dt_ns in ordered_pairs:
        if dt_ns is None:
            parts.append(f"{delay_dt} dt")
        else:
            parts.append(f"{delay_dt} dt ({dt_ns:.1f} ns)")
    return ", ".join(parts)


def _three_lane_format_significance_count(
    rows: Sequence[dict[str, Any]],
    *,
    metric: str,
    reference_dimension: int,
    dimension: int,
) -> str:
    """Count how often a d_ref-d_dim comparison is CI-separated within one lane."""
    values = [
        bool(row[f"significant_d{reference_dimension}_minus_d{dimension}"])
        for row in rows
        if row.get("metric") == metric
        and f"significant_d{reference_dimension}_minus_d{dimension}" in row
    ]
    if not values:
        return "—"
    return f"{sum(values)}/{len(values)} delays"


def save_three_lane_fixed_n_markdown_report(
    rows: Sequence[dict[str, Any]],
    *,
    path: str | Path,
    title: str = "Three-lane fixed-n comparison",
) -> Path:
    """Write one markdown report that places theory, Aer, and hardware fixed-n summaries side by side."""
    if not rows:
        raise ValueError("rows cannot be empty")

    reference_dimension = int(rows[0]["reference_dimension"])
    comparison_dimension = int(rows[0]["comparison_dimension"])
    dimensions = [int(item) for item in str(rows[0]["dimensions"]).split(",") if item]
    control_dimension = min(dimensions)
    lane_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        lane_groups[str(row["lane"])].append(row)

    lane_order = list(_THREE_LANE_LANE_ORDER) + sorted(
        lane for lane in lane_groups.keys() if lane not in _THREE_LANE_LANE_ORDER
    )
    metric_order = [
        metric for metric in _THREE_LANE_METRIC_ORDER if any(row["metric"] == metric for row in rows)
    ]

    lines = [f"# {title}", ""]
    lines.extend(
        [
            "## Scope",
            "",
            "- This report preserves each lane's native delay grid instead of interpolating missing points.",
            "- Hardware rows merge the saved state-tomography and process-tomography comparison summaries on the same backend.",
            "- Process metrics are shown only for the Aer and hardware lanes because the theory baseline does not expose channel tomography.",
            "- For the full-fill-ratio case (here d=4, phi=1.000), leakage is structurally zero because no unused Hilbert-space states remain. Treat any reported L=0.000 in that column as definitional rather than as an independently measured absence of noise.",
        ]
    )
    if any(bool(row.get("contains_theory_baseline")) for row in rows):
        lines.append(
            "- The theory lane remains a baseline-only effective model; any nonzero theory-lane leakage comes from its explicit codespace-mixing term rather than from circuit execution."
        )
    lines.append("")

    lines.extend(
        [
            "## Lane Overview",
            "",
            "| Lane | Delay grid | Metrics | d4-d3 fidelity sig | d4-d3 process sig |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for lane in lane_order:
        if lane not in lane_groups:
            continue
        group = lane_groups[lane]
        label = str(group[0]["lane_label"])
        metrics = ", ".join(
            metric for metric in metric_order if any(row["metric"] == metric for row in group)
        )
        lines.append(
            "| "
            + " | ".join(
                [
                    label,
                    _three_lane_format_delay_grid(group),
                    metrics or "—",
                    _three_lane_format_significance_count(
                        group,
                        metric="fidelity",
                        reference_dimension=reference_dimension,
                        dimension=comparison_dimension,
                    ),
                    _three_lane_format_significance_count(
                        group,
                        metric="process_fidelity",
                        reference_dimension=reference_dimension,
                        dimension=comparison_dimension,
                    ),
                ]
            )
            + " |"
        )
    lines.append("")

    for metric in metric_order:
        metric_rows = [
            row
            for lane in lane_order
            for row in sorted(
                lane_groups.get(lane, []),
                key=lambda item: int(item["delay_dt"]),
            )
            if row["metric"] == metric
        ]
        if not metric_rows:
            continue
        lines.extend(
            [
                f"## {_three_lane_metric_title(metric)}",
                "",
                f"| Lane | delay_dt | dt_ns | d{control_dimension} | d{comparison_dimension} | d{reference_dimension} | Δ(d{reference_dimension}-d{comparison_dimension}) | sig | Δ(d{reference_dimension}-d{control_dimension}) | sig |",
                "| --- | ---: | ---: | --- | --- | --- | ---: | --- | ---: | --- |",
            ]
        )
        for row in metric_rows:
            dt_ns = row.get("dt_ns")
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(row["lane_label"]),
                        str(int(row["delay_dt"])),
                        f"{float(dt_ns):.3f}" if dt_ns is not None else "—",
                        _three_lane_format_metric_value(row, control_dimension),
                        _three_lane_format_metric_value(row, comparison_dimension),
                        _three_lane_format_metric_value(row, reference_dimension),
                        _three_lane_format_delta(row, reference_dimension, comparison_dimension),
                        _three_lane_format_significance(row, reference_dimension, comparison_dimension),
                        _three_lane_format_delta(row, reference_dimension, control_dimension),
                        _three_lane_format_significance(row, reference_dimension, control_dimension),
                    ]
                )
                + " |"
            )
        lines.append("")

    output = _normalize_path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines).rstrip() + "\n")
    return output



def save_fixed_n_markdown_report(
    summary_rows: Sequence[dict[str, Any]],
    *,
    path: str | Path,
    title: str = "Fixed-n comparison report",
) -> Path:
    """Filesystem or reporting helper used by the analysis and artifact pipeline."""
    if not summary_rows:
        raise ValueError("summary_rows cannot be empty")
    lines = [f"# {title}", ""]
    dims = sorted(
        {
            dimension
            for row in summary_rows
            for key in row.keys()
            for kind, dimension, _, _ in [_parse_summary_key(key)]
            if kind in {"fill_ratio", "metric"} and dimension is not None
        }
    )
    metric_names = sorted(
        {
            metric
            for row in summary_rows
            for key in row.keys()
            for kind, _, _, metric in [_parse_summary_key(key)]
            if kind == "metric" and metric is not None
        }
    )
    significance_values = [
        bool(value)
        for row in summary_rows
        for key, value in row.items()
        if _parse_summary_key(key)[0] == "significant"
    ]
    contains_theory_baseline = any(
        bool(row.get("contains_theory_baseline")) for row in summary_rows
    )
    contains_explicit_theory_mixing = any(
        bool(row.get("contains_explicit_theory_mixing")) for row in summary_rows
    )
    leakage_values = [
        float(row[_summary_metric_key(dim, "leakage")])
        for row in summary_rows
        for dim in dims
        if dim != max(dims) and _summary_metric_key(dim, "leakage") in row
    ]
    reference_dimension = max(dims)
    reference_fill_ratio_key = _summary_fill_ratio_key(reference_dimension)
    reference_is_full_fill = any(
        reference_fill_ratio_key in row
        and abs(float(row[reference_fill_ratio_key]) - 1.0) <= 1e-12
        for row in summary_rows
    )
    interpretation_notes: list[str] = []
    if reference_is_full_fill:
        interpretation_notes.append(
            f"For the full-fill-ratio case (here d={reference_dimension}, phi=1.000), leakage is "
            "structurally zero because no unused Hilbert-space states remain. Treat any reported "
            "L=0.000 for that row as definitional rather than as an independently measured absence "
            "of noise."
        )
    if contains_theory_baseline:
        interpretation_notes.append(
            "These records come from the effective Markovian theory lane. Treat them as a "
            "baseline-only model rather than as a circuit-level leakage study alongside Aer "
            "or hardware."
        )
    if contains_explicit_theory_mixing:
        interpretation_notes.append(
            "Any nonzero leakage in these theory-lane rows is generated by the explicit "
            "codespace-mixing term (`t_dep` or `depolarizing_probability`). That is a different "
            "mechanism from circuit-level leakage caused by entangling gates, measurement, "
            "readout, and feed-forward noise."
        )
    if significance_values and not any(significance_values):
        interpretation_notes.append(
            "All reported confidence intervals overlap. In this regime the current model does not "
            "resolve statistically distinguishable differences between encoded dimensions."
        )
    if leakage_values and all(abs(value) <= 1e-12 for value in leakage_values):
        interpretation_notes.append(
            "Leakage is identically zero in these source records. For the Markovian lane this usually "
            "means only codespace-preserving T1/T2 terms were enabled; add an explicit codespace-mixing "
            "term such as t_dep or depolarizing_probability to study fill-ratio leakage."
        )
    if interpretation_notes:
        lines.append("## Interpretation")
        lines.append("")
        for note in interpretation_notes:
            lines.append(f"- {note}")
        lines.append("")
    for row in summary_rows:
        if row.get("dt_ns") is None:
            lines.append(f"## delay_dt = {row['delay_dt']}")
        else:
            lines.append(f"## delay_dt = {row['delay_dt']} ({float(row['dt_ns']):.3f} ns)")
        lines.append("")
        for dim in dims:
            phi_key = _summary_fill_ratio_key(dim)
            if phi_key in row:
                lines.append(f"- d={dim}, phi={row[phi_key]:.3f}")
            for metric in metric_names:
                metric_key = _summary_metric_key(dim, metric)
                if metric_key in row:
                    ci_bounds = _summary_metric_ci_bounds_from_row(row, dim, metric)
                    if ci_bounds is None:
                        lines.append(f"  - {metric}: {row[metric_key]:.6f}")
                    else:
                        lines.append(
                            f"  - {metric}: {row[metric_key]:.6f} "
                            f"[CI {ci_bounds[0]:.6f}, {ci_bounds[1]:.6f}]"
                        )
        delta_keys = sorted(key for key in row.keys() if _parse_summary_key(key)[0] == "delta")
        if delta_keys:
            lines.append("- differences")
            for key in delta_keys:
                delta_kind, delta_ref_dim, delta_dim, delta_metric = _parse_summary_key(key)
                if (
                    delta_kind == "delta"
                    and delta_ref_dim is not None
                    and delta_dim is not None
                    and delta_metric is not None
                ):
                    significance_key = _summary_significant_key(
                        delta_ref_dim,
                        delta_dim,
                        delta_metric,
                    )
                    significance = row.get(significance_key)
                    suffix = ""
                    if isinstance(significance, bool):
                        suffix = "; statistically distinguishable" if significance else "; CIs overlap"
                    lines.append(
                        f"  - delta {delta_metric} "
                        f"(d={delta_ref_dim} - d={delta_dim}): "
                        f"{float(row[key]):+.6f}{suffix}"
                    )
        lines.append("")
    output = _normalize_path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines).rstrip() + "\n")
    return output


def save_blp_markdown_report(
    records: Sequence[dict[str, Any]],
    *,
    path: str | Path,
    title: str = "BLP scan report",
) -> Path:
    """Write a concise markdown summary for correlated-memory or random-telegraph BLP scans."""
    if not records:
        raise ValueError("records cannot be empty")

    ordered = sorted(
        records,
        key=lambda item: (
            int(item.get("dimension", 0)),
            int(item.get("n_physical", 0)),
            float(item.get("memory_strength", item.get("switching_probability", 0.0))),
        ),
    )
    first = ordered[0]
    lines = [f"# {title}", ""]
    if "switching_probability" in first:
        lines.extend(
            [
                "- model: random telegraph dephasing",
                f"- probe pair: {first.get('probe_pair', 'unspecified')}",
                f"- coupling_strength: {float(first['coupling_strength']):.6f}",
                f"- steps: {int(first['steps'])}",
                f"- dt_per_step: {float(first['dt_per_step']):.6f}",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "- model: correlated-memory Pauli lane",
                f"- steps: {int(first['steps'])}",
                f"- base_phase_flip_probability: {float(first['base_phase_flip_probability']):.6f}",
                "",
            ]
        )

    grouped: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    for record in ordered:
        grouped[(int(record["dimension"]), int(record["n_physical"]))].append(record)

    for (dimension, n_physical), group in sorted(grouped.items()):
        fill = float(group[0]["fill_ratio"])
        if "switching_probability" in group[0]:
            group_sorted = sorted(group, key=lambda item: float(item["switching_probability"]))
            monotone = all(
                float(group_sorted[i + 1]["blp_measure"]) <= float(group_sorted[i]["blp_measure"]) + 1e-12
                for i in range(len(group_sorted) - 1)
            )
        else:
            group_sorted = sorted(group, key=lambda item: float(item["memory_strength"]))
            monotone = all(
                float(group_sorted[i + 1]["blp_measure"]) >= float(group_sorted[i]["blp_measure"]) - 1e-12
                for i in range(len(group_sorted) - 1)
            )
        lines.extend(
            [
                f"## d={dimension}, n={n_physical}, phi={fill:.3f}",
                f"- monotone trend across scanned parameter: {'yes' if monotone else 'no'}",
            ]
        )
        if "switching_probability" in group[0]:
            for record in group_sorted:
                tau_steps = record.get("correlation_time_steps")
                tau_label = "inf" if tau_steps is None else f"{float(tau_steps):.3f} steps"
                lines.append(
                    f"- p_switch={float(record['switching_probability']):.4f}, "
                    f"tau_corr≈{tau_label}, BLP={float(record['blp_measure']):.6f}"
                )
        else:
            for record in group_sorted:
                lines.append(
                    f"- memory_strength={float(record['memory_strength']):.3f}, "
                    f"BLP={float(record['blp_measure']):.6f}"
                )
        lines.append("")

    output = _normalize_path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines).rstrip() + "\n")
    return output


def save_random_telegraph_calibration_markdown_report(
    calibration: dict[str, Any],
    *,
    path: str | Path,
    title: str = "Random-telegraph calibration report",
) -> Path:
    """Write a concise markdown summary for backend-anchored RTN calibration."""
    lines = [f"# {title}", ""]
    lines.extend(
        [
            f"- source backend: {calibration.get('source_backend_name', 'unknown')}",
            f"- source lane: {calibration.get('source_simulation_lane', 'unknown')}",
            f"- logical dimension: d={int(calibration['dimension'])}",
            f"- physical qubits: n={int(calibration['n_physical'])}",
            f"- source metric: {calibration['metric']}",
            f"- fit mode: {calibration['fit_mode']}",
            f"- baseline metric value: {float(calibration['baseline_metric_value']):.6f}",
            f"- calibration floor: {float(calibration['calibration_floor']):.6f}",
            (
                f"- fitted effective T2: {float(calibration['effective_t2_ns']):.3f} ns"
                if calibration.get("effective_t2_ns_ci_low") is None
                else (
                    f"- fitted effective T2: {float(calibration['effective_t2_ns']):.3f} ns "
                    f"[CI {float(calibration['effective_t2_ns_ci_low']):.3f}, "
                    f"{float(calibration['effective_t2_ns_ci_high']):.3f}]"
                )
            ),
            f"- assumed correlation time: tau_corr := T2_eff = {float(calibration['correlation_time_ns']):.3f} ns",
            (
                f"- recommended switching probability: {float(calibration['switching_probability']):.6f} per {float(calibration['dt_ns_per_step']):.3f} ns step"
                if calibration.get("switching_probability_ci_low") is None
                else (
                    f"- recommended switching probability: {float(calibration['switching_probability']):.6f} "
                    f"[CI {float(calibration['switching_probability_ci_low']):.6f}, "
                    f"{float(calibration['switching_probability_ci_high']):.6f}] "
                    f"per {float(calibration['dt_ns_per_step']):.3f} ns step"
                )
            ),
            f"- calibration formula: {calibration['calibration_formula']}",
            f"- calibration assumption: {calibration['calibration_assumption']}",
            "",
            "## Selected Delay Points",
            "",
        ]
    )

    for point in calibration.get("selected_points", []):
        ratio = float(point["normalized_decay_ratio"])
        if "normalized_decay_ratio_ci_low" in point and "normalized_decay_ratio_ci_high" in point:
            lines.append(
                f"- delay_dt={int(point['delay_dt'])}, delay={float(point['delay_ns']):.3f} ns, "
                f"normalized_ratio={ratio:.6f} "
                f"[CI {float(point['normalized_decay_ratio_ci_low']):.6f}, "
                f"{float(point['normalized_decay_ratio_ci_high']):.6f}]"
            )
        else:
            lines.append(
                f"- delay_dt={int(point['delay_dt'])}, delay={float(point['delay_ns']):.3f} ns, "
                f"normalized_ratio={ratio:.6f}"
            )

    output = _normalize_path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines).rstrip() + "\n")
    return output


__all__ = [
    "save_json",
    "save_csv",
    "load_json_records",
    "plot_metric_vs_delay",
    "plot_metric_vs_fill_ratio",
    "plot_blp_vs_memory_strength",
    "plot_blp_vs_switching_probability",
    "plot_hardware_theory_curves",
    "plot_hardware_theory_divergence",
    "merge_fixed_n_summary_rows",
    "load_fixed_n_summary_rows",
    "summarize_fixed_n_comparison",
    "summarize_backend_fixed_n_comparison",
    "merge_backend_fixed_n_summary_rows",
    "load_backend_fixed_n_summary_rows",
    "summarize_backend_fixed_n_table",
    "summarize_hardware_theory_divergence",
    "summarize_three_lane_fixed_n_table",
    "save_fixed_n_markdown_report",
    "save_backend_fixed_n_markdown_report",
    "save_hardware_theory_divergence_markdown_report",
    "save_three_lane_fixed_n_markdown_report",
    "save_blp_markdown_report",
    "save_random_telegraph_calibration_markdown_report",
]
