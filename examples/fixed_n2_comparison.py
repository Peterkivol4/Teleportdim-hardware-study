from __future__ import annotations

from pathlib import Path

from teleportdim.reports import (
    plot_metric_vs_delay,
    save_csv,
    save_fixed_n_markdown_report,
    save_json,
    summarize_fixed_n_comparison,
)
from teleportdim.sweeps import fixed_n_sweep_configs, run_markovian_fixed_n_sweep


def main() -> None:
    out = Path("results/examples/fixed_n2")
    out.mkdir(parents=True, exist_ok=True)

    configs = fixed_n_sweep_configs(
        [2],
        delay_dt_values=[0, 2048, 4096, 8192],
        state_family="haar",
        random_seed=7,
    )
    records = run_markovian_fixed_n_sweep(
        configs,
        t1=540540.0,
        t2=360360.0,
        t_dep=360360.0,
        bootstrap_samples=64,
    )

    save_json(records, out / "markovian_n2.json")
    save_csv(records, out / "markovian_n2.csv")
    plot_metric_vs_delay(records, metric="fidelity", path=out / "markovian_n2_fidelity.png")
    plot_metric_vs_delay(records, metric="leakage", path=out / "markovian_n2_leakage.png")

    summary = summarize_fixed_n_comparison(
        records,
        n_physical=2,
        metric_keys=("fidelity", "leakage", "in_subspace_fidelity"),
    )
    save_json(summary, out / "n2_compare.json")
    save_csv(summary, out / "n2_compare.csv")
    save_fixed_n_markdown_report(
        summary,
        path=out / "n2_compare.md",
        title="Example fixed-n channel-deformation comparison",
    )


if __name__ == "__main__":
    main()
