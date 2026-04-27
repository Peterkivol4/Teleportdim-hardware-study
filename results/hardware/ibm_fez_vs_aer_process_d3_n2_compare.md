# IBM Fez vs Aer Process Comparison (d=3, n=2)

- hardware backend: `ibm_fez`
- Aer comparison: calibrated with `dt_ns_per_dt = 4.0` to match the hardware backend `dt`
- saved Aer cross-check rerun: `8192` shots and `200` bootstrap samples
- note: the earlier `256`-shot short-delay Aer run could look non-monotone because the added `0 -> 128 dt` relaxation signal is small relative to tomography variance; the saved rerun restores monotone Aer process fidelity `0.912783 -> 0.907736 -> 0.903990`
- metrics shown below compare the same logical dimension and the same `delay_dt` grid

## delay_dt = 0 (0.000 ns)

- process fidelity: hardware 0.742090 [CI 0.706547, 0.774033] vs Aer 0.912783 [CI 0.906584, 0.918325] (delta -0.170693; CIs are separated)
- average gate fidelity: hardware 0.806567 [CI 0.779910, 0.830524] vs Aer 0.934587 [CI 0.929938, 0.938744] (delta -0.128020; CIs are separated)
- state fidelity / leakage: hardware F=0.859595, L=0.038774; Aer F=0.939667, L=0.013213

## delay_dt = 64 (256.000 ns)

- process fidelity: hardware 0.666584 [CI 0.635227, 0.696713] vs Aer 0.907736 [CI 0.901438, 0.915140] (delta -0.241153; CIs are separated)
- average gate fidelity: hardware 0.749938 [CI 0.726420, 0.772535] vs Aer 0.930802 [CI 0.926078, 0.936355] (delta -0.180865; CIs are separated)
- state fidelity / leakage: hardware F=0.824983, L=0.038302; Aer F=0.936180, L=0.014024

## delay_dt = 128 (512.000 ns)

- process fidelity: hardware 0.692762 [CI 0.658691, 0.724198] vs Aer 0.903990 [CI 0.896716, 0.910320] (delta -0.211228; CIs are separated)
- average gate fidelity: hardware 0.769571 [CI 0.744019, 0.793148] vs Aer 0.927992 [CI 0.922537, 0.932740] (delta -0.158421; CIs are separated)
- state fidelity / leakage: hardware F=0.824887, L=0.033822; Aer F=0.931152, L=0.015132
