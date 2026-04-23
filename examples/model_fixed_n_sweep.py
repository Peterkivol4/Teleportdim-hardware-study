from __future__ import annotations

from pathlib import Path

from teleportdim.reports import plot_metric_vs_delay, plot_metric_vs_fill_ratio, save_csv, save_json
from teleportdim.sweeps import fixed_n_sweep_configs, run_markovian_fixed_n_sweep


def main() -> None:
    configs = fixed_n_sweep_configs([1, 2, 3], delay_dt_values=[0, 32, 64, 128], state_family="fourier")
    records = run_markovian_fixed_n_sweep(configs, t1=120.0, t2=80.0, t_dep=160.0)

    out_dir = Path('artifacts')
    out_dir.mkdir(exist_ok=True)
    save_json(records, out_dir / 'markovian_fixed_n.json')
    save_csv(records, out_dir / 'markovian_fixed_n.csv')
    plot_metric_vs_delay(records, metric='fidelity', path=out_dir / 'fidelity_vs_delay.png')
    plot_metric_vs_delay(records, metric='leakage', path=out_dir / 'leakage_vs_delay.png')
    plot_metric_vs_fill_ratio(
        records,
        metric='fidelity',
        delay_dt=128,
        path=out_dir / 'fidelity_vs_fill_ratio_delay128.png',
    )


if __name__ == '__main__':
    main()
