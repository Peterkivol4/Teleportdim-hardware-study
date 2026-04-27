# Fixed-n comparison report

## Interpretation

- For the full-fill-ratio case (here d=4, phi=1.000), leakage is structurally zero because no unused Hilbert-space states remain. Treat any reported L=0.000 for that row as definitional rather than as an independently measured absence of noise.

## delay_dt = 0 (0.000 ns)

- d=2, phi=0.500
  - average_gate_fidelity: 0.963634 [CI 0.958205, 0.967495]
  - fidelity: 0.950162 [CI 0.948042, 0.952273]
  - in_subspace_fidelity: 0.969606 [CI 0.967718, 0.971565]
  - leakage: 0.020064 [CI 0.018575, 0.021399]
  - process_fidelity: 0.945451 [CI 0.937308, 0.951242]
- d=3, phi=0.750
  - average_gate_fidelity: 0.934587 [CI 0.929938, 0.938744]
  - fidelity: 0.939667 [CI 0.938064, 0.941225]
  - in_subspace_fidelity: 0.952198 [CI 0.950685, 0.953717]
  - leakage: 0.013213 [CI 0.012257, 0.014114]
  - process_fidelity: 0.912783 [CI 0.906584, 0.918325]
- d=4, phi=1.000
  - average_gate_fidelity: 0.897234 [CI 0.891420, 0.901925]
  - fidelity: 0.933544 [CI 0.932468, 0.934689]
  - in_subspace_fidelity: 0.933544 [CI 0.932468, 0.934689]
  - leakage: 0.000000 [CI 0.000000, 0.000000]
  - process_fidelity: 0.871542 [CI 0.864275, 0.877407]
- differences
  - delta average_gate_fidelity (d=4 - d=2): -0.066400; statistically distinguishable
  - delta fidelity (d=4 - d=2): -0.016617; statistically distinguishable
  - delta in_subspace_fidelity (d=4 - d=2): -0.036061; statistically distinguishable
  - delta leakage (d=4 - d=2): -0.020064; statistically distinguishable
  - delta process_fidelity (d=4 - d=2): -0.073909; statistically distinguishable
  - delta average_gate_fidelity (d=4 - d=3): -0.037354; statistically distinguishable
  - delta fidelity (d=4 - d=3): -0.006122; statistically distinguishable
  - delta in_subspace_fidelity (d=4 - d=3): -0.018653; statistically distinguishable
  - delta leakage (d=4 - d=3): -0.013213; statistically distinguishable
  - delta process_fidelity (d=4 - d=3): -0.041241; statistically distinguishable

## delay_dt = 2048 (455.111 ns)

- d=2, phi=0.500
  - average_gate_fidelity: 0.961268 [CI 0.955645, 0.965700]
  - fidelity: 0.942209 [CI 0.939736, 0.944646]
  - in_subspace_fidelity: 0.964817 [CI 0.962868, 0.966900]
  - leakage: 0.023450 [CI 0.021820, 0.025262]
  - process_fidelity: 0.941902 [CI 0.933468, 0.948549]
- d=3, phi=0.750
  - average_gate_fidelity: 0.927916 [CI 0.923053, 0.932724]
  - fidelity: 0.932259 [CI 0.930642, 0.933706]
  - in_subspace_fidelity: 0.946407 [CI 0.944871, 0.947693]
  - leakage: 0.015011 [CI 0.014173, 0.015931]
  - process_fidelity: 0.903888 [CI 0.897404, 0.910299]
- d=4, phi=1.000
  - average_gate_fidelity: 0.888922 [CI 0.883825, 0.894440]
  - fidelity: 0.926476 [CI 0.925253, 0.927660]
  - in_subspace_fidelity: 0.926476 [CI 0.925253, 0.927660]
  - leakage: 0.000000 [CI 0.000000, 0.000000]
  - process_fidelity: 0.861153 [CI 0.854781, 0.868050]
- differences
  - delta average_gate_fidelity (d=4 - d=2): -0.072346; statistically distinguishable
  - delta fidelity (d=4 - d=2): -0.015733; statistically distinguishable
  - delta in_subspace_fidelity (d=4 - d=2): -0.038341; statistically distinguishable
  - delta leakage (d=4 - d=2): -0.023450; statistically distinguishable
  - delta process_fidelity (d=4 - d=2): -0.080749; statistically distinguishable
  - delta average_gate_fidelity (d=4 - d=3): -0.038994; statistically distinguishable
  - delta fidelity (d=4 - d=3): -0.005784; statistically distinguishable
  - delta in_subspace_fidelity (d=4 - d=3): -0.019931; statistically distinguishable
  - delta leakage (d=4 - d=3): -0.015011; statistically distinguishable
  - delta process_fidelity (d=4 - d=3): -0.042735; statistically distinguishable

## delay_dt = 4096 (910.222 ns)

- d=2, phi=0.500
  - average_gate_fidelity: 0.954804 [CI 0.950177, 0.959475]
  - fidelity: 0.932981 [CI 0.930029, 0.935491]
  - in_subspace_fidelity: 0.959280 [CI 0.956831, 0.961701]
  - leakage: 0.027432 [CI 0.025755, 0.029229]
  - process_fidelity: 0.932206 [CI 0.925265, 0.939212]
- d=3, phi=0.750
  - average_gate_fidelity: 0.920904 [CI 0.916376, 0.925483]
  - fidelity: 0.922176 [CI 0.920523, 0.923820]
  - in_subspace_fidelity: 0.938296 [CI 0.936864, 0.939753]
  - leakage: 0.017244 [CI 0.016199, 0.018234]
  - process_fidelity: 0.894539 [CI 0.888502, 0.900644]
- d=4, phi=1.000
  - average_gate_fidelity: 0.880324 [CI 0.875088, 0.884111]
  - fidelity: 0.916205 [CI 0.914795, 0.917460]
  - in_subspace_fidelity: 0.916205 [CI 0.914795, 0.917460]
  - leakage: 0.000000 [CI 0.000000, 0.000000]
  - process_fidelity: 0.850405 [CI 0.843860, 0.855139]
- differences
  - delta average_gate_fidelity (d=4 - d=2): -0.074480; statistically distinguishable
  - delta fidelity (d=4 - d=2): -0.016777; statistically distinguishable
  - delta in_subspace_fidelity (d=4 - d=2): -0.043075; statistically distinguishable
  - delta leakage (d=4 - d=2): -0.027432; statistically distinguishable
  - delta process_fidelity (d=4 - d=2): -0.081801; statistically distinguishable
  - delta average_gate_fidelity (d=4 - d=3): -0.040580; statistically distinguishable
  - delta fidelity (d=4 - d=3): -0.005971; statistically distinguishable
  - delta in_subspace_fidelity (d=4 - d=3): -0.022091; statistically distinguishable
  - delta leakage (d=4 - d=3): -0.017244; statistically distinguishable
  - delta process_fidelity (d=4 - d=3): -0.044134; statistically distinguishable

## delay_dt = 8192 (1820.444 ns)

- d=2, phi=0.500
  - average_gate_fidelity: 0.947331 [CI 0.942974, 0.952063]
  - fidelity: 0.919745 [CI 0.916727, 0.922488]
  - in_subspace_fidelity: 0.952137 [CI 0.949577, 0.954750]
  - leakage: 0.034036 [CI 0.032102, 0.035859]
  - process_fidelity: 0.920997 [CI 0.914461, 0.928095]
- d=3, phi=0.750
  - average_gate_fidelity: 0.908587 [CI 0.903850, 0.912822]
  - fidelity: 0.905679 [CI 0.903970, 0.907616]
  - in_subspace_fidelity: 0.925851 [CI 0.924230, 0.927584]
  - leakage: 0.021871 [CI 0.020847, 0.023072]
  - process_fidelity: 0.878116 [CI 0.871800, 0.883763]
- d=4, phi=1.000
  - average_gate_fidelity: 0.863836 [CI 0.859858, 0.867614]
  - fidelity: 0.899341 [CI 0.897936, 0.900714]
  - in_subspace_fidelity: 0.899341 [CI 0.897936, 0.900714]
  - leakage: 0.000000 [CI 0.000000, 0.000000]
  - process_fidelity: 0.829795 [CI 0.824822, 0.834517]
- differences
  - delta average_gate_fidelity (d=4 - d=2): -0.083495; statistically distinguishable
  - delta fidelity (d=4 - d=2): -0.020403; statistically distinguishable
  - delta in_subspace_fidelity (d=4 - d=2): -0.052796; statistically distinguishable
  - delta leakage (d=4 - d=2): -0.034036; statistically distinguishable
  - delta process_fidelity (d=4 - d=2): -0.091202; statistically distinguishable
  - delta average_gate_fidelity (d=4 - d=3): -0.044751; statistically distinguishable
  - delta fidelity (d=4 - d=3): -0.006338; statistically distinguishable
  - delta in_subspace_fidelity (d=4 - d=3): -0.026510; statistically distinguishable
  - delta leakage (d=4 - d=3): -0.021871; statistically distinguishable
  - delta process_fidelity (d=4 - d=3): -0.048320; statistically distinguishable
