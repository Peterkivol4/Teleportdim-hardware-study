# Fixed-n comparison report

## Interpretation

- For the full-fill-ratio case (here d=4, phi=1.000), leakage is structurally zero because no unused Hilbert-space states remain. Treat any reported L=0.000 for that row as definitional rather than as an independently measured absence of noise.

## delay_dt = 0 (0.000 ns)

- d=2, phi=0.500
  - fidelity: 0.915326
  - in_subspace_fidelity: 0.970624
  - leakage: 0.056972
- d=3, phi=0.750
  - fidelity: 0.850992
  - in_subspace_fidelity: 0.871751
  - leakage: 0.023813
- d=4, phi=1.000
  - fidelity: 0.870924
  - in_subspace_fidelity: 0.870924
  - leakage: 0.000000
- differences
  - delta fidelity (d=4 - d=2): -0.044402
  - delta in_subspace_fidelity (d=4 - d=2): -0.099700
  - delta leakage (d=4 - d=2): -0.056972
  - delta fidelity (d=4 - d=3): +0.019932
  - delta in_subspace_fidelity (d=4 - d=3): -0.000827
  - delta leakage (d=4 - d=3): -0.023813
