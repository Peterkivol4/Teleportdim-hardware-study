# Fixed-n comparison report

## Interpretation

- For the full-fill-ratio case (here d=4, phi=1.000), leakage is structurally zero because no unused Hilbert-space states remain. Treat any reported L=0.000 for that row as definitional rather than as an independently measured absence of noise.

## delay_dt = 0 (0.000 ns)

- d=2, phi=0.500
  - average_gate_fidelity: 0.919314 [CI 0.895725, 0.944777]
  - fidelity: 0.878909 [CI 0.863525, 0.893308]
  - in_subspace_fidelity: 0.934606 [CI 0.921650, 0.948492]
  - leakage: 0.059763 [CI 0.048869, 0.070555]
  - process_fidelity: 0.878970 [CI 0.843587, 0.917165]
- d=3, phi=0.750
  - average_gate_fidelity: 0.806567 [CI 0.779910, 0.830524]
  - fidelity: 0.859595 [CI 0.849904, 0.870061]
  - in_subspace_fidelity: 0.894189 [CI 0.885860, 0.904122]
  - leakage: 0.038774 [CI 0.032833, 0.044315]
  - process_fidelity: 0.742090 [CI 0.706547, 0.774033]
- d=4, phi=1.000
  - average_gate_fidelity: 0.702194 [CI 0.684705, 0.722831]
  - fidelity: 0.851997 [CI 0.843385, 0.861072]
  - in_subspace_fidelity: 0.851997 [CI 0.843385, 0.861072]
  - leakage: 0.000000 [CI 0.000000, 0.000000]
  - process_fidelity: 0.627743 [CI 0.605881, 0.653538]
- differences
  - delta average_gate_fidelity (d=4 - d=2): -0.217119; statistically distinguishable
  - delta fidelity (d=4 - d=2): -0.026912; statistically distinguishable
  - delta in_subspace_fidelity (d=4 - d=2): -0.082609; statistically distinguishable
  - delta leakage (d=4 - d=2): -0.059763; statistically distinguishable
  - delta process_fidelity (d=4 - d=2): -0.251227; statistically distinguishable
  - delta average_gate_fidelity (d=4 - d=3): -0.104373; statistically distinguishable
  - delta fidelity (d=4 - d=3): -0.007598; CIs overlap
  - delta in_subspace_fidelity (d=4 - d=3): -0.042192; statistically distinguishable
  - delta leakage (d=4 - d=3): -0.038774; statistically distinguishable
  - delta process_fidelity (d=4 - d=3): -0.114347; statistically distinguishable

## delay_dt = 64 (256.000 ns)

- d=2, phi=0.500
  - average_gate_fidelity: 0.819408 [CI 0.778157, 0.849872]
  - fidelity: 0.807019 [CI 0.786115, 0.827978]
  - in_subspace_fidelity: 0.860122 [CI 0.836972, 0.881225]
  - leakage: 0.062632 [CI 0.051375, 0.076293]
  - process_fidelity: 0.729112 [CI 0.667236, 0.774808]
- d=3, phi=0.750
  - average_gate_fidelity: 0.749938 [CI 0.726420, 0.772535]
  - fidelity: 0.824983 [CI 0.813395, 0.836836]
  - in_subspace_fidelity: 0.857969 [CI 0.845457, 0.869677]
  - leakage: 0.038302 [CI 0.032098, 0.043912]
  - process_fidelity: 0.666584 [CI 0.635227, 0.696713]
- d=4, phi=1.000
  - average_gate_fidelity: 0.595119 [CI 0.573428, 0.611200]
  - fidelity: 0.765295 [CI 0.755490, 0.775248]
  - in_subspace_fidelity: 0.765295 [CI 0.755490, 0.775248]
  - leakage: 0.000000 [CI 0.000000, 0.000000]
  - process_fidelity: 0.493899 [CI 0.466785, 0.514000]
- differences
  - delta average_gate_fidelity (d=4 - d=2): -0.224289; statistically distinguishable
  - delta fidelity (d=4 - d=2): -0.041724; statistically distinguishable
  - delta in_subspace_fidelity (d=4 - d=2): -0.094827; statistically distinguishable
  - delta leakage (d=4 - d=2): -0.062632; statistically distinguishable
  - delta process_fidelity (d=4 - d=2): -0.235213; statistically distinguishable
  - delta average_gate_fidelity (d=4 - d=3): -0.154818; statistically distinguishable
  - delta fidelity (d=4 - d=3): -0.059688; statistically distinguishable
  - delta in_subspace_fidelity (d=4 - d=3): -0.092674; statistically distinguishable
  - delta leakage (d=4 - d=3): -0.038302; statistically distinguishable
  - delta process_fidelity (d=4 - d=3): -0.172684; statistically distinguishable

## delay_dt = 128 (512.000 ns)

- d=2, phi=0.500
  - average_gate_fidelity: 0.819877 [CI 0.784529, 0.851988]
  - fidelity: 0.809193 [CI 0.788212, 0.831194]
  - in_subspace_fidelity: 0.863268 [CI 0.841697, 0.882764]
  - leakage: 0.061863 [CI 0.050306, 0.075574]
  - process_fidelity: 0.729815 [CI 0.676793, 0.777982]
- d=3, phi=0.750
  - average_gate_fidelity: 0.769571 [CI 0.744019, 0.793148]
  - fidelity: 0.824887 [CI 0.815241, 0.837103]
  - in_subspace_fidelity: 0.853986 [CI 0.842943, 0.866204]
  - leakage: 0.033822 [CI 0.028262, 0.039254]
  - process_fidelity: 0.692762 [CI 0.658691, 0.724198]
- d=4, phi=1.000
  - average_gate_fidelity: 0.604210 [CI 0.587381, 0.623518]
  - fidelity: 0.765086 [CI 0.753917, 0.774799]
  - in_subspace_fidelity: 0.765086 [CI 0.753917, 0.774799]
  - leakage: 0.000000 [CI 0.000000, 0.000000]
  - process_fidelity: 0.505262 [CI 0.484227, 0.529397]
- differences
  - delta average_gate_fidelity (d=4 - d=2): -0.215667; statistically distinguishable
  - delta fidelity (d=4 - d=2): -0.044108; statistically distinguishable
  - delta in_subspace_fidelity (d=4 - d=2): -0.098182; statistically distinguishable
  - delta leakage (d=4 - d=2): -0.061863; statistically distinguishable
  - delta process_fidelity (d=4 - d=2): -0.224553; statistically distinguishable
  - delta average_gate_fidelity (d=4 - d=3): -0.165362; statistically distinguishable
  - delta fidelity (d=4 - d=3): -0.059801; statistically distinguishable
  - delta in_subspace_fidelity (d=4 - d=3): -0.088901; statistically distinguishable
  - delta leakage (d=4 - d=3): -0.033822; statistically distinguishable
  - delta process_fidelity (d=4 - d=3): -0.187500; statistically distinguishable
