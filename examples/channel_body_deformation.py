from __future__ import annotations

from pathlib import Path

from teleportdim.body_sweeps import run_channel_body_sweep
from teleportdim.fingerprinting import save_channel_body_markdown_report
from teleportdim.reports import save_csv, save_json


def main() -> None:
    records = run_channel_body_sweep(
        [2],
        dimensions=[2, 3, 4],
        bodies=[
            "ideal",
            "dephasing",
            "amplitude_damping",
            "leakage_mixing",
            "coherent_z_drift",
        ],
        strengths=[0.0, 0.001, 0.005, 0.01],
        delays=[0, 64, 128],
        shots=4096,
        samples=512,
    )

    out_dir = Path("results/examples/channel_body")
    out_dir.mkdir(parents=True, exist_ok=True)
    save_json(records, out_dir / "n2_body_sweep.json")
    save_csv(records, out_dir / "n2_body_sweep.csv")
    save_channel_body_markdown_report(records, out_dir / "n2_body_sweep.md")


if __name__ == "__main__":
    main()
