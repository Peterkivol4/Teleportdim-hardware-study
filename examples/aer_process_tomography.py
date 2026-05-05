from __future__ import annotations

from pathlib import Path

from teleportdim.aer import build_basic_noise_model, run_aer_process_tomography
from teleportdim.config import BackendConfig, SweepConfig
from teleportdim.reports import plot_metric_vs_delay, save_csv, save_json


def main() -> None:
    sweep = SweepConfig(dimension=3, n_physical=2, delay_dt_values=[0, 2048, 4096], shots=2048)
    backend = BackendConfig(shots=2048, correction_mode="dynamic")
    noise_model = build_basic_noise_model(depolarizing_1q=0.001, depolarizing_2q=0.01)
    records = run_aer_process_tomography(
        sweep,
        backend,
        noise_model=noise_model,
        bootstrap_samples=64,
    )

    out_dir = Path("results/examples/aer_process")
    out_dir.mkdir(parents=True, exist_ok=True)
    save_json(records, out_dir / "aer_process.json")
    save_csv(records, out_dir / "aer_process.csv")
    plot_metric_vs_delay(records, metric="process_fidelity", path=out_dir / "process_fidelity_vs_delay.png")
    plot_metric_vs_delay(
        records,
        metric="average_gate_fidelity",
        path=out_dir / "average_gate_fidelity_vs_delay.png",
    )


if __name__ == "__main__":
    main()
