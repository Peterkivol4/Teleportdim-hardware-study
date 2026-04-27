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


OUT = Path('results/fixed_n2')
OUT.mkdir(parents=True, exist_ok=True)

configs = fixed_n_sweep_configs([2], delay_dt_values=[0, 32, 64, 128], state_family='haar', random_seed=7)
records = run_markovian_fixed_n_sweep(configs, t1=120.0, t2=80.0, t_dep=160.0)

save_json(records, OUT / 'markovian_n2.json')
save_csv(records, OUT / 'markovian_n2.csv')
plot_metric_vs_delay(records, metric='fidelity', path=OUT / 'markovian_n2_fidelity.png')
plot_metric_vs_delay(records, metric='leakage', path=OUT / 'markovian_n2_leakage.png')

summary = summarize_fixed_n_comparison(
    records,
    n_physical=2,
    metric_keys=('avg_probe_fidelity', 'avg_probe_leakage', 'avg_probe_in_subspace_fidelity'),
)
save_json(summary, OUT / 'n2_compare.json')
save_csv(summary, OUT / 'n2_compare.csv')
save_fixed_n_markdown_report(summary, path=OUT / 'n2_compare.md', title='n=2 fixed-hardware comparison')
