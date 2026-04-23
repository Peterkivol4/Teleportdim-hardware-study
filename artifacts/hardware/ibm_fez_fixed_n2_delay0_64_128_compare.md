# Fixed-n comparison report

## Interpretation

- For the full-fill-ratio case (here d=4, phi=1.000), leakage is structurally zero because no unused Hilbert-space states remain. Treat any reported L=0.000 for that row as definitional rather than as an independently measured absence of noise.

## delay_dt = 0 (0.000 ns)

- d=2, phi=0.500
  - fidelity: 0.886399 [CI 0.866303, 0.904854]
  - in_subspace_fidelity: 0.948800 [CI 0.935792, 0.962916]
  - leakage: 0.065773 [CI 0.051938, 0.079102]
- d=3, phi=0.750
  - fidelity: 0.869690 [CI 0.849457, 0.882736]
  - in_subspace_fidelity: 0.900911 [CI 0.885373, 0.916072]
  - leakage: 0.034730 [CI 0.024845, 0.043638]
- d=4, phi=1.000
  - fidelity: 0.868848 [CI 0.853227, 0.883141]
  - in_subspace_fidelity: 0.868848 [CI 0.853227, 0.883141]
  - leakage: 0.000000 [CI 0.000000, 0.000000]
- differences
  - delta fidelity (d=4 - d=2): -0.017551; CIs overlap
  - delta in_subspace_fidelity (d=4 - d=2): -0.079952; statistically distinguishable
  - delta leakage (d=4 - d=2): -0.065773; statistically distinguishable
  - delta fidelity (d=4 - d=3): -0.000843; CIs overlap
  - delta in_subspace_fidelity (d=4 - d=3): -0.032063; statistically distinguishable
  - delta leakage (d=4 - d=3): -0.034730; statistically distinguishable

## delay_dt = 64 (256.000 ns)

- d=2, phi=0.500
  - fidelity: 0.836736 [CI 0.816735, 0.856971]
  - in_subspace_fidelity: 0.886390 [CI 0.868540, 0.908341]
  - leakage: 0.057680 [CI 0.046906, 0.067694]
- d=3, phi=0.750
  - fidelity: 0.828133 [CI 0.810960, 0.847927]
  - in_subspace_fidelity: 0.854519 [CI 0.836791, 0.872471]
  - leakage: 0.030717 [CI 0.023949, 0.037722]
- d=4, phi=1.000
  - fidelity: 0.834597 [CI 0.817870, 0.849261]
  - in_subspace_fidelity: 0.834597 [CI 0.817870, 0.849261]
  - leakage: 0.000000 [CI 0.000000, 0.000000]
- differences
  - delta fidelity (d=4 - d=2): -0.002139; CIs overlap
  - delta in_subspace_fidelity (d=4 - d=2): -0.051793; statistically distinguishable
  - delta leakage (d=4 - d=2): -0.057680; statistically distinguishable
  - delta fidelity (d=4 - d=3): +0.006464; CIs overlap
  - delta in_subspace_fidelity (d=4 - d=3): -0.019923; CIs overlap
  - delta leakage (d=4 - d=3): -0.030717; statistically distinguishable

## delay_dt = 128 (512.000 ns)

- d=2, phi=0.500
  - fidelity: 0.822027 [CI 0.803188, 0.848147]
  - in_subspace_fidelity: 0.878583 [CI 0.858081, 0.899850]
  - leakage: 0.064111 [CI 0.049532, 0.081549]
- d=3, phi=0.750
  - fidelity: 0.809725 [CI 0.787369, 0.829511]
  - in_subspace_fidelity: 0.848510 [CI 0.832301, 0.865072]
  - leakage: 0.044195 [CI 0.033551, 0.055769]
- d=4, phi=1.000
  - fidelity: 0.852900 [CI 0.839285, 0.867179]
  - in_subspace_fidelity: 0.852900 [CI 0.839285, 0.867179]
  - leakage: 0.000000 [CI 0.000000, 0.000000]
- differences
  - delta fidelity (d=4 - d=2): +0.030873; CIs overlap
  - delta in_subspace_fidelity (d=4 - d=2): -0.025683; CIs overlap
  - delta leakage (d=4 - d=2): -0.064111; statistically distinguishable
  - delta fidelity (d=4 - d=3): +0.043175; statistically distinguishable
  - delta in_subspace_fidelity (d=4 - d=3): +0.004390; CIs overlap
  - delta leakage (d=4 - d=3): -0.044195; statistically distinguishable
