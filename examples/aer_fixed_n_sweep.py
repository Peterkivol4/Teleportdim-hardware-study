from __future__ import annotations

from pathlib import Path

from teleportdim.reports import plot_metric_vs_delay, plot_metric_vs_fill_ratio, save_csv, save_json
from teleportdim.sweeps import fixed_n_sweep_configs, run_aer_fixed_n_sweep


def main() -> None:
    configs = fixed_n_sweep_configs([2], delay_dt_values=[0, 32, 64, 128], state_family="fourier")
    records = run_aer_fixed_n_sweep(
        configs,
        correction_mode="dynamic",
        depolarizing_1q=0.001,
        depolarizing_2q=0.01,
        bootstrap_samples=64,
    )

    out_dir = Path("results/aer_fixed_n")
    out_dir.mkdir(parents=True, exist_ok=True)
    save_json(records, out_dir / "aer_fixed_n.json")
    save_csv(records, out_dir / "aer_fixed_n.csv")
    plot_metric_vs_delay(records, metric="fidelity", path=out_dir / "fidelity_vs_delay.png")
    plot_metric_vs_delay(records, metric="leakage", path=out_dir / "leakage_vs_delay.png")
    plot_metric_vs_fill_ratio(
        records,
        metric="fidelity",
        delay_dt=128,
        path=out_dir / "fidelity_vs_fill_ratio_delay128.png",
    )


if __name__ == "__main__":
    main()

