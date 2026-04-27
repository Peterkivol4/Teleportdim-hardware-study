# IBM Fez Hardware Metadata

- metadata manifest date: `2026-04-24`
- backend: `ibm_fez`
- topology: IBM Heron r2, 156 physical qubits
- selected coupling map / physical qubits: not archived in the original saved result records
- IBM calibration date: not archived in the original saved result records

## Shot Counts By File

| File | Records | Dimensions | Delays dt | Shot counts | Bootstrap samples |
| --- | ---: | --- | --- | --- | --- |
| results/hardware/ibm_fez_d2_n2_delay0.json | 1 | 2 | 0 | 256 | - |
| results/hardware/ibm_fez_d3_n2_delay0.json | 1 | 3 | 0 | 256 | - |
| results/hardware/ibm_fez_d4_n2_delay0.json | 1 | 4 | 0 | 256 | - |
| results/hardware/ibm_fez_fixed_n2_delay0_64_128_compare.json | 3 | - | 0,64,128 | - | - |
| results/hardware/ibm_fez_fixed_n2_delay0_64_128_live.json | 9 | 2,3,4 | 0,64,128 | 256 | 100 |
| results/hardware/ibm_fez_fixed_n2_delay0_compare.json | 1 | - | 0 | - | - |
| results/hardware/ibm_fez_process_d2_n2_delay0_64_128.json | 3 | 2 | 0,64,128 | 256 | 100 |
| results/hardware/ibm_fez_process_d3_n2_delay0_64_128.json | 3 | 3 | 0,64,128 | 256 | 100 |
| results/hardware/ibm_fez_process_d4_n2_delay0_64_128.json | 3 | 4 | 0,64,128 | 256 | 100 |
| results/hardware/ibm_fez_process_fixed_n2_delay0_64_128_compare.json | 3 | - | 0,64,128 | - | - |
| results/hardware/ibm_fez_vs_aer_process_d3_n2_compare.json | 3 | 3 | 0,64,128 | - | - |

## Calibration Caveat

The saved hardware records preserve backend name, delay grid, shot counts, and reconstructed metrics, but not the exact IBM calibration timestamp or selected coupling topology. Those fields must be captured during the next live IBM run before using the data as a final hardware-calibrated claim.
