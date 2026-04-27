from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path
from typing import Any


_SUMMARY_METRIC_RE = re.compile(r"^d(?P<dimension>\d+)\|metric\|(?P<metric>[A-Za-z0-9_]+)$")


def expand_dimension_summary_records(records: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Expand fixed-n comparison-summary rows into per-dimension metric records."""
    expanded: list[dict[str, Any]] = []
    for record in records:
        if "dimension" in record:
            expanded.append(dict(record))
            continue
        n_physical = record.get("n_physical")
        delay_dt = record.get("delay_dt")
        dt_ns = record.get("dt_ns")
        dimensions = sorted(
            {
                int(match.group("dimension"))
                for key in record
                if (match := _SUMMARY_METRIC_RE.match(key)) is not None
            }
        )
        for dimension in dimensions:
            output: dict[str, Any] = {
                "dimension": dimension,
                "n_physical": n_physical,
                "delay_dt": delay_dt,
                "dt_ns": dt_ns,
                "fill_ratio": record.get(f"d{dimension}|fill_ratio"),
            }
            for key, value in record.items():
                match = _SUMMARY_METRIC_RE.match(key)
                if match is not None and int(match.group("dimension")) == dimension:
                    output[match.group("metric")] = value
            if "source_simulation_lanes" in record:
                output["simulation_lane"] = record["source_simulation_lanes"]
            if "backend_name" in record:
                output["backend_name"] = record["backend_name"]
            expanded.append(output)
    return expanded


def _metric_feature(record: dict[str, Any], metric: str) -> float | None:
    """Convert raw metrics into comparable deformation features."""
    value = record.get(metric)
    if value is None:
        return None
    numeric = float(value)
    if metric in {"fidelity", "process_fidelity", "average_gate_fidelity", "in_subspace_fidelity"}:
        return 1.0 - numeric
    return numeric


def _candidate_key(record: dict[str, Any]) -> tuple[int, int, int]:
    """Return the dimension/backend-delay key used for body matching."""
    return (
        int(record.get("dimension", -1)),
        int(record.get("n_physical", -1)),
        int(record.get("delay_dt", 0)),
    )


def compare_body_fingerprints(
    body_records: Sequence[dict[str, Any]],
    hardware_records: Sequence[dict[str, Any]],
    *,
    metrics: Sequence[str],
) -> list[dict[str, Any]]:
    """Rank simulated body fingerprints by distance to hardware deformation records."""
    if not metrics:
        raise ValueError("metrics cannot be empty")
    expanded_hardware = expand_dimension_summary_records(hardware_records)
    by_key: dict[tuple[int, int, int], list[dict[str, Any]]] = defaultdict(list)
    for record in body_records:
        by_key[_candidate_key(record)].append(record)

    comparisons: list[dict[str, Any]] = []
    for hardware in expanded_hardware:
        key = _candidate_key(hardware)
        candidates = by_key.get(key, [])
        ranked: list[dict[str, Any]] = []
        for candidate in candidates:
            squared_distance = 0.0
            used_metrics: list[str] = []
            for metric in metrics:
                hardware_value = _metric_feature(hardware, metric)
                candidate_value = _metric_feature(candidate, metric)
                if hardware_value is None or candidate_value is None:
                    continue
                squared_distance += (hardware_value - candidate_value) ** 2
                used_metrics.append(metric)
            if not used_metrics:
                continue
            ranked.append(
                {
                    "dimension": key[0],
                    "n_physical": key[1],
                    "delay_dt": key[2],
                    "hardware_backend": hardware.get("backend_name", hardware.get("simulation_lane", "hardware")),
                    "candidate_body": candidate.get("body"),
                    "candidate_strength": candidate.get("body_strength"),
                    "distance": (squared_distance / float(len(used_metrics))) ** 0.5,
                    "metrics_used": ",".join(used_metrics),
                }
            )
        ranked.sort(key=lambda item: float(item["distance"]))
        for rank, item in enumerate(ranked, start=1):
            item["rank"] = rank
            comparisons.append(item)
    return comparisons


def save_channel_body_markdown_report(records: Sequence[dict[str, Any]], path: str | Path) -> Path:
    """Write a compact channel-body summary report."""
    output = Path(path).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[str(record.get("body", "unknown"))].append(record)
    lines = [
        "# Channel-Body Deformation Summary",
        "",
        "Each row averages one modeled body over the supplied dimension, delay, and strength grid.",
        "",
        "| Body | Mean process deformation | Mean leakage | Mean nonunitality | Mean anisotropy | BLP revival? |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for body, items in sorted(grouped.items()):
        delta_process = [
            1.0 - float(item["process_fidelity"])
            for item in items
            if item.get("process_fidelity") is not None
        ]
        leakage = [float(item.get("leakage", 0.0)) for item in items]
        nonunitality = [
            float(item["nonunitality"])
            for item in items
            if item.get("nonunitality") is not None
        ]
        anisotropy = [
            float(item["anisotropy"])
            for item in items
            if item.get("anisotropy") is not None
        ]
        blp_values = [
            float(item["blp_score"])
            for item in items
            if item.get("blp_score") is not None
        ]
        blp_label = "yes" if any(value > 0.0 for value in blp_values) else "no"
        lines.append(
            "| {body} | {delta:.6f} | {leakage:.6f} | {nonunitality:.6f} | {anisotropy:.6f} | {blp} |".format(
                body=body,
                delta=sum(delta_process) / len(delta_process) if delta_process else float("nan"),
                leakage=sum(leakage) / len(leakage) if leakage else float("nan"),
                nonunitality=sum(nonunitality) / len(nonunitality) if nonunitality else float("nan"),
                anisotropy=sum(anisotropy) / len(anisotropy) if anisotropy else float("nan"),
                blp=blp_label,
            )
        )
    output.write_text("\n".join(lines) + "\n")
    return output


def save_body_fingerprint_markdown_report(comparisons: Sequence[dict[str, Any]], path: str | Path) -> Path:
    """Write a ranked hardware-vs-body fingerprint report."""
    output = Path(path).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Body Fingerprint Comparison",
        "",
        "Distances are Euclidean distances over the requested normalized deformation metrics. Hardware matches are phenomenological, not microscopic noise-source claims.",
        "",
        "| d | n | delay_dt | rank | candidate body | strength | distance | metrics |",
        "| ---: | ---: | ---: | ---: | --- | ---: | ---: | --- |",
    ]
    for item in comparisons:
        lines.append(
            "| {dimension} | {n_physical} | {delay_dt} | {rank} | {candidate_body} | {candidate_strength} | {distance:.6f} | {metrics_used} |".format(
                **item
            )
        )
    output.write_text("\n".join(lines) + "\n")
    return output


__all__ = [
    "expand_dimension_summary_records",
    "compare_body_fingerprints",
    "save_channel_body_markdown_report",
    "save_body_fingerprint_markdown_report",
]
