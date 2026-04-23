"""Example hardware sweep.

This script assumes your IBM Quantum account is already initialized for Qiskit Runtime.
"""

from teleportdim.config import BackendConfig, SweepConfig
from teleportdim.sweeps import run_hardware_delay_sweep, summarize_results


if __name__ == "__main__":
    sweep = SweepConfig(dimension=3, delay_dt_values=[0, 64, 128], shots=2048)
    backend = BackendConfig(backend_name=None, shots=2048, correction_mode="dynamic")
    records = run_hardware_delay_sweep(sweep, backend)
    print(summarize_results(records))
