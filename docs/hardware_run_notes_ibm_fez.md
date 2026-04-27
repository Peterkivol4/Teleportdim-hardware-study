# IBM Fez Hardware Run Notes

This note records the practical path that produced the saved `ibm_fez` artifacts. It is not a polished thesis chapter; it is the short operational narrative that explains what actually ran, what looked wrong at first, and what changed the interpretation.

## What ran

- Live state-tomography fixed-`n` sweep on `ibm_fez` with `n=2`, `d in {2,3,4}`, `delay_dt in {0,64,128}`, `256` shots, and `100` bootstrap resamples.
  - output stems: `results/hardware/ibm_fez_fixed_n2_delay0_64_128_live` and `results/hardware/ibm_fez_fixed_n2_delay0_64_128_compare`
- Live process tomography on the same backend and delay grid, run dimension-by-dimension for `d=2`, `d=3`, and `d=4`.
  - output stems: `results/hardware/ibm_fez_process_d2_n2_delay0_64_128`, `results/hardware/ibm_fez_process_d3_n2_delay0_64_128`, `results/hardware/ibm_fez_process_d4_n2_delay0_64_128`, and `results/hardware/ibm_fez_process_fixed_n2_delay0_64_128_compare`
- Hardware-matched Aer qutrit cross-check with `dt_ns_per_dt = 4.0`, `8192` shots, and `200` bootstrap resamples.
  - output stems: `results/fixed_n2/aer_process_d3_delay0_64_128_fezdt` and `results/hardware/ibm_fez_vs_aer_process_d3_n2_compare`

The dynamic path was used throughout. `ibm_fez` was chosen because the backend advertises both `delay` and `if_else`, which are the two backend capabilities this protocol needs before a live delay-dependent teleportation run is even worth attempting.

## What looked strange

- The short hardware grid is noisy. In the saved state-tomography comparison, the `d=4` state fidelity rises from `0.834597` at `64 dt` to `0.852900` at `128 dt` after an earlier drop from zero delay.
- The saved hardware process-tomography comparison shows a similar short-grid wobble. `d=3` process fidelity goes `0.742090 -> 0.666584 -> 0.692762`, and `d=4` goes `0.627743 -> 0.493899 -> 0.505262`.
- Those upward ticks are real features of the saved artifacts, but the confidence intervals overlap and every tomographic circuit on hardware used only `256` shots. The right interpretation is "finite-shot fluctuation on a short delay grid," not "coherence recovery."

## What broke in interpretation

The first version of the matched short-grid Aer qutrit process comparison could look non-monotone as well. That was a warning sign, because the added `0 -> 128 dt` relaxation signal is small on a `4 ns / dt` calibration, and low-shot tomography can easily bury it under reconstruction variance. The problem was not that the circuit model was obviously wrong; the problem was that the short-grid statistic was not trustworthy enough to support a physical claim.

This is why the repo now treats the earlier short-grid Aer result as a diagnostic failure rather than as an experimental conclusion.

## What had to be rerun

- The qutrit Aer process comparison on the hardware-matched delay grid was rerun at `8192` shots and `200` bootstrap resamples.
- That rerun restored the expected monotone Aer sequence `0.912783 -> 0.907736 -> 0.903990` for process fidelity across `0,64,128 dt`.
- The saved comparison artifact `results/hardware/ibm_fez_vs_aer_process_d3_n2_compare.md` now documents the corrected same-grid cross-check used in the paper draft.

## What changed in the interpretation

- The main result is no longer framed as "higher occupancy means less leakage, therefore better teleportation." The hardware data do not support that simplification.
- `d=4` has structural `L=0` because `phi=1` leaves no leakage subspace, yet its hardware process fidelity is still lower than `d=3` at every measured delay.
- The more defensible claim is therefore channel-level: zero leakage at full occupancy does not guarantee the best logical teleportation channel.
- This also changed how the three lanes are read together. The theory lane remains useful as a baseline trend model, but the scientific weight of the repo now sits with the Aer and hardware tomography artifacts, especially the saved process-tomography comparison on `ibm_fez`.

## Practical takeaways

- Use the short hardware grid as evidence of channel separation between `d=3` and `d=4`, not as a precision decoherence fit.
- Use the matched Aer rerun to show that the short-grid non-monotonicity can be a statistical artifact.
- If this experiment is extended, the next live run should increase both the shot budget and the delay grid, for example beyond `0,64,128 dt`, before drawing any claim about fine-grained delay scaling.
