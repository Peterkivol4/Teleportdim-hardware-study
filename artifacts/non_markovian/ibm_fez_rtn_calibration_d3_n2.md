# Random-telegraph calibration report

- source backend: ibm_fez
- source lane: ibm_runtime_process_tomography
- logical dimension: d=3
- physical qubits: n=2
- source metric: process_fidelity
- fit mode: first_nonzero
- baseline metric value: 0.742090
- calibration floor: 0.111111
- fitted effective T2: 2008.584 ns [CI 1089.623, 15373.067]
- assumed correlation time: tau_corr := T2_eff = 2008.584 ns
- recommended switching probability: 0.001989 [CI 0.000260, 0.003664] per 4.000 ns step
- calibration formula: p_switch = 1 - exp(-dt_step / tau_corr)
- calibration assumption: tau_corr := fitted effective T2 from delay data

## Selected Delay Points

- delay_dt=64, delay=256.000 ns, normalized_ratio=0.880335 [CI 0.790615, 0.983485]
