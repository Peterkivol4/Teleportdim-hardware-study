# TeleportDim: Channel-Body Deformation in Fixed-Qubit Logical Teleportation

**One-sentence thesis:** TeleportDim studies fixed-qubit quantum teleportation as a deformable logical channel.

TeleportDim treats teleportation failure as a physical channel-deformation problem. For fixed physical qubit count, it varies encoded dimension and structured noise bodies to identify whether observed teleportation failure is caused by dimension pressure, leakage, Markovian decay, non-Markovian memory, coherent channel drift, or hardware-specific distortion.

## Core Question

Given a fixed physical qubit budget, how do encoded dimension and structured environmental bodies deform the logical teleportation channel, and can those deformations be classified from leakage, process fidelity, state fidelity, and non-Markovian information-flow signatures?

![Fixed-n summary panel](docs/figures/fixed_n_summary_panel.svg)

**Headline result.** On `ibm_fez` at fixed `n=2`, zero-delay process fidelity falls from `0.7421` at `d=3` to `0.6277` at `d=4`, and the saved hardware process-tomography comparison keeps `d=4` below `d=3` at all measured delays (`results/hardware/ibm_fez_process_fixed_n2_delay0_64_128_compare.md`, `docs/teleportdim_fixed_n_paper.md`).

**Why this result matters.** This suggests that zero leakage at full occupancy does not automatically imply the best logical teleportation channel.

The flagship interpretation is therefore not only that `d=3` and `d=4` differ. It is that `d=4` fails differently: full occupancy removes unused-subspace leakage, while the reconstructed process channel still shows stronger within-subspace deformation than the partially occupied `d=3` channel.

## Bodies Studied

- **Dimension body:** the encoded logical dimension `d` inside a fixed physical Hilbert space `2^n`.
- **Leakage body:** unused Hilbert-space levels that can absorb probability.
- **Markovian environment body:** memoryless depolarizing, amplitude-damping, dephasing, and relaxation-style deformation.
- **Non-Markovian memory body:** correlated memory and random-telegraph information backflow.
- **Coherent hardware body:** coherent rotations, calibration drift, and cross-talk-like channel deformation.
- **Measurement body:** readout distortion and tomography bias.

## Primary Observables

- process fidelity,
- average gate fidelity,
- embedded-state fidelity,
- leakage,
- in-subspace fidelity,
- nonunitality,
- probe anisotropy and state-spread,
- BLP information-backflow score.

## Scope

**Demonstrated**

- fixed-`n` comparison across theory, Aer, and IBM hardware lanes,
- tomography pipeline for state fidelity, leakage, in-subspace fidelity, process fidelity, and average gate fidelity,
- channel-body deformation records and fingerprint reports for controlled body sweeps,
- saved `d=3` vs `d=4` reports on `ibm_fez`, including same-backend process tomography.

**Exploratory**

- broader leakage theory beyond the measured `n=2` setup,
- non-Markovian calibration as an interpretive lane rather than a fitted microscopic bath model,
- hardware body matching as a phenomenological similarity result, not a microscopic noise-source identification,
- generalization beyond the measured backend, delay grid, and shot budget.

## Reproducibility

- key comparison artifacts: `results/fixed_n2/three_lane_n2_compare.md`, `results/hardware/ibm_fez_process_fixed_n2_delay0_64_128_compare.md`, and `results/hardware/ibm_fez_vs_aer_process_d3_n2_compare.md`,
- full manuscript draft: `docs/teleportdim_fixed_n_paper.md`,
- reproducible entrypoints: `make theory`, `make aer`, `make hardware-live`, `make hardware-process-live`, `make three-lane-report`, and `make test`,
- hardware execution narrative: `docs/hardware_run_notes_ibm_fez.md`,
- source and validation surface: `src/teleportdim`, `results/`, `docs/`, `examples/`, and `tests/`.

### Channel-Body Sweep

Controlled deformation fingerprints can be generated before any additional hardware run:

```bash
teleportdim channel-body-sweep \
  --n-values 2 \
  --dimensions 2,3,4 \
  --bodies ideal,dephasing,amplitude_damping,leakage_mixing,random_telegraph,coherent_z_drift \
  --strengths 0,0.001,0.005,0.01 \
  --delays 0,64,128 \
  --shots 4096 \
  --samples 1024 \
  --output-stem results/channel_body/n2_body_sweep
```

Then compare a hardware artifact against the modeled body fingerprints:

```bash
teleportdim compare-body-fingerprints \
  --input-json results/channel_body/n2_body_sweep.json \
  --hardware-json results/hardware/ibm_fez_process_fixed_n2_delay0_64_128_compare.json \
  --metrics process_fidelity,average_gate_fidelity,leakage,in_subspace_fidelity,anisotropy,nonunitality \
  --output-stem results/channel_body/ibm_fez_body_match
```

The comparison is intentionally phenomenological: it reports which modeled deformation body is closest to the observed hardware channel, not which microscopic noise source the hardware definitely contains.

## Implementation notes

The package now uses physical modules under `src/teleportdim/` that mirror the
original section boundaries: `config`, `encoding`, `states`, `metrics`,
`postprocess`, `tomography`, `process`, `statistics`, `simulation`, `circuits`,
`hardware`, `aer`, `reports`, `sweeps`, and `cli`.

`src/teleportdim/__init__.py` is now a compatibility re-export surface for
existing notebooks, tests, and CLI entrypoints rather than the implementation
host.

This build hardens the package into a cleaner experiment repo:

- fixed-`n` and leakage-centered thesis framing,
- IBM-hardware lane,
- theory/model lane,
- optional Aer lane,
- process-tomography and channel-fidelity analysis,
- bootstrap statistics for tomography-derived confidence intervals,
- clean comparison reports for `d=3` vs `d=4` at fixed `n=2`,
- optional dependency extras so non-hardware users do not have to install the full IBM/Qiskit stack.

## Main thesis design

The controlled question is no longer just “does fidelity change with dimension?”

Instead:

- hold **physical qubit count `n` fixed**,
- vary **logical dimension `d`** inside that same `n`-qubit Hilbert space,
- track whether performance changes because of **subspace structure and leakage**.

The cleanest test case remains:

- `d=3` on `n=2`
- `d=4` on `n=2`

Same hardware, same qubit count, different fill ratio.

## Primary observables

The repo treats these as first-class outputs:

1. embedded-state fidelity,
2. leakage,
3. in-subspace fidelity,
4. process fidelity,
5. average gate fidelity.

This separates:

- logical damage **inside** the code subspace,
- from population **escaping** into unused Hilbert-space states.

## Lanes

### Lane A — IBM hardware lane

- Runtime-oriented sampler execution
- dynamic or deferred correction
- ISA transpilation helpers
- tomography-based reconstruction

### Lane B — theory baseline / effective-model lane

- Markovian delay sweeps
- correlated-memory trajectories
- BLP non-Markovianity scans
- fixed-`n` grouped sweeps
- plotting and export
- intended as a baseline-only interpretive lane, not as a circuit-faithful leakage model

### Lane C — optional Aer lane

- local simulator entrypoint
- fixed-`n` full-circuit noisy sweeps
- logical process tomography / average gate fidelity
- simple depolarizing / relaxation noise model builder
- dynamic/deferred tomography aggregation
- intended as the primary local execution path before hardware, with the theory lane as a baseline

## New in this build

### 1. Optional dependency extras

The base package no longer forces the full quantum stack.

- `pip install -e .`
- `pip install -e .[aer]`
- `pip install -e .[ibm]`
- `pip install -e .[full]`

This keeps the theory/reporting lane usable in lighter environments.

### 2. Circuit-layer import guard

The circuit module now raises a clear error if someone tries to use the Qiskit circuit builders without installing the quantum stack.

### 3. Aer CLI entrypoint

New command:

```bash
teleportdim aer-delay-sweep   --dimension 3   --delays 0,2048,4096,8192   --shots 8192   --correction-mode deferred   --depolarizing-1q 0.001   --depolarizing-2q 0.01   --output-stem results/aer_d3
```

The Aer CLI exports `dt_ns` for every record using the configured `dt` calibration.
For the default `0.222222... ns / dt` scale, `0,32,64,128 dt` spans only `0-28.4 ns`,
which is too small for a stable relaxation trend at ordinary tomography shot counts.
The wider `0,2048,4096,8192 dt` schedule above is the recommended fixed-`n` Aer regime.

### 3b. Aer fixed-`n` circuit sweep

Full-circuit fixed-`n` comparison on the noisy Aer teleportation circuit:

```bash
teleportdim aer-fixed-n-sweep \
  --n-values 2 \
  --delays 0,2048,4096,8192 \
  --shots 8192 \
  --correction-mode dynamic \
  --depolarizing-1q 0.001 \
  --depolarizing-2q 0.01 \
  --bootstrap-samples 200 \
  --confidence-level 0.95 \
  --output-stem results/aer_fixed_n
```

### 3c. Aer process tomography

Logical process fidelity / average gate fidelity from a tomographically complete probe set:

```bash
teleportdim aer-process-tomography \
  --dimension 3 \
  --n-physical 2 \
  --delays 0,2048,4096,8192 \
  --shots 8192 \
  --correction-mode dynamic \
  --depolarizing-1q 0.001 \
  --depolarizing-2q 0.01 \
  --bootstrap-samples 200 \
  --confidence-level 0.95 \
  --output-stem results/aer_process_d3
```

### 4. Fixed-`n` comparison reports

New report flow for same-hardware comparisons:

```bash
teleportdim compare-fixed-n \
  --input-json results/fixed_n2/aer_fixed_n2.json,results/fixed_n2/aer_process_d2.json,results/fixed_n2/aer_process_d3.json,results/fixed_n2/aer_process_d4.json \
  --n-physical 2 \
  --output-stem results/fixed_n2/aer_n2_compare
```

This generates:

- JSON summary
- CSV summary
- Markdown comparison report

The summary is designed to make the `d=3` vs `d=4` result readable at each delay.

## Example workflows

### Markovian baseline fixed-`n` sweep

```bash
teleportdim markovian-fixed-n-sweep   --n-values 2   --delays 0,2048,4096,8192   --t1 540540   --t2 360360   --t-dep 360360   --bootstrap-samples 200   --confidence-level 0.95   --output-stem results/markovian_n2
```

This baseline theory-lane configuration is calibrated onto the same `dt` grid as the Aer lane
using `0.222222... ns / dt`, so `T1 = 120 us` maps to about `540540 dt` and
`T2 = 80 us` maps to about `360360 dt`.

The extra `t_dep` term is intentional. With only `T1/T2`, the effective Markovian lane
preserves the low-index logical prefix subspace used by the embedding, so `d=2` and `d=3`
show identically zero leakage even though `phi < 1`. To study leakage as a fill-ratio
observable, the theory lane needs an explicit codespace-mixing term.

That also means the theory-lane leakage is not caused by the same mechanism as the circuit
lanes. In Aer and hardware, leakage comes from the teleportation circuit, transpilation, and
device noise acting on the full execution path. In the Markovian baseline, leakage only appears
after adding an explicit mixing term. Side-by-side plots are still useful, but the theory lane
should be read as a baseline-only trend model rather than as a parallel leakage study.

### Compare `d=3` vs `d=4` at `n=2`

```bash
teleportdim compare-fixed-n   --input-json results/markovian_n2.json   --n-physical 2   --output-stem results/n2_compare
```

### Random-telegraph BLP scan at fixed `n=2`

```bash
teleportdim blp-random-telegraph-scan \
  --dimensions 2,3,4 \
  --n-physical 2 \
  --switching-probabilities 0.005,0.0125,0.025,0.05,0.1,0.2 \
  --coupling-strength 0.4 \
  --steps 16 \
  --samples 2048 \
  --output-stem results/non_markovian/random_telegraph_blp_n2
```

### Backend-anchored random-telegraph calibration

```bash
teleportdim calibrate-random-telegraph \
  --input-json results/hardware/ibm_fez_process_d3_n2_delay0_64_128.json \
  --dimension 3 \
  --n-physical 2 \
  --metric process_fidelity \
  --dt-ns-per-step 4.0 \
  --fit-mode first_nonzero \
  --output-stem results/non_markovian/ibm_fez_rtn_calibration_d3_n2
```

The random-telegraph lane still uses the relation
`switching_probability = 1 - exp(-dt / τ_corr)`, but the repository no longer needs
to justify `τ_corr` with a purely hand-picked number. Using the live `ibm_fez`
`d=3`, `n=2` process-fidelity decay, the saved calibration artifact
`results/non_markovian/ibm_fez_rtn_calibration_d3_n2.{json,md}` estimates
`T2_eff ≈ 2008.6 ns`, then sets `τ_corr := T2_eff` as a phenomenological matching rule.
At the backend's `dt = 4 ns`, that gives a recommended
`switching_probability ≈ 0.00199` per telegraph step, with a broad uncertainty band
reflecting the small amount of live delay data.

### Live hardware fixed-`n` delay sweep

```bash
teleportdim hardware-fixed-n-sweep \
  --n-values 2 \
  --backend-name ibm_fez \
  --shots 256 \
  --delays 0,64,128 \
  --bootstrap-samples 100 \
  --output-stem results/hardware/ibm_fez_fixed_n2_delay0_64_128_live
```

The repository now includes both the earlier zero-delay snapshots and a saved live fixed-`n`
delay sweep plus comparison report at the same backend and qubit count:
`results/hardware/ibm_fez_fixed_n2_delay0_64_128_live.{json,csv}` and
`results/hardware/ibm_fez_fixed_n2_delay0_64_128_compare.{json,csv,md}`.

### Same-backend fixed-`n` hardware process tomography (`d=2,3,4`, `n=2`)

```bash
teleportdim hardware-process-tomography \
  --dimension 2 \
  --n-physical 2 \
  --backend-name ibm_fez \
  --shots 256 \
  --delays 0,64,128 \
  --bootstrap-samples 100 \
  --output-stem results/hardware/ibm_fez_process_d2_n2_delay0_64_128

teleportdim hardware-process-tomography \
  --dimension 3 \
  --n-physical 2 \
  --backend-name ibm_fez \
  --shots 256 \
  --delays 0,64,128 \
  --bootstrap-samples 100 \
  --output-stem results/hardware/ibm_fez_process_d3_n2_delay0_64_128
teleportdim hardware-process-tomography \
  --dimension 4 \
  --n-physical 2 \
  --backend-name ibm_fez \
  --shots 256 \
  --delays 0,64,128 \
  --bootstrap-samples 100 \
  --output-stem results/hardware/ibm_fez_process_d4_n2_delay0_64_128

teleportdim compare-fixed-n \
  --input-json results/hardware/ibm_fez_process_d2_n2_delay0_64_128.json,results/hardware/ibm_fez_process_d3_n2_delay0_64_128.json,results/hardware/ibm_fez_process_d4_n2_delay0_64_128.json \
  --n-physical 2 \
  --output-stem results/hardware/ibm_fez_process_fixed_n2_delay0_64_128_compare
```

The repository now includes saved live same-backend hardware process-tomography artifacts for
all three logical dimensions at fixed `n=2`:
`results/hardware/ibm_fez_process_d2_n2_delay0_64_128.{json,csv}`,
`results/hardware/ibm_fez_process_d3_n2_delay0_64_128.{json,csv}`,
and `results/hardware/ibm_fez_process_d4_n2_delay0_64_128.{json,csv}`.

The compact fixed-`n` comparison table and detailed markdown report live at
`results/hardware/ibm_fez_process_fixed_n2_delay0_64_128_compare.{json,csv,md}`.
The repository also keeps the calibrated `d=3` hardware-vs-Aer process comparison artifact
`results/hardware/ibm_fez_vs_aer_process_d3_n2_compare.{json,md}` as a same-delay cross-check.
That saved Aer cross-check now uses `8192` shots and `200` bootstrap resamples rather than the
earlier `256`-shot setting, because over `0-128 dt` at `dt = 4 ns` the added delay noise is
small enough that low-shot tomography can produce a non-monotonic process-fidelity estimate.
The saved rerun restores the expected monotone Aer trend across `0,64,128 dt`.

### Multi-backend hardware sweep

```bash
teleportdim hardware-multi-backend-fixed-n-sweep \
  --n-values 2 \
  --backend-names ibm_fez,ibm_torino \
  --shots 256 \
  --delays 0,64,128 \
  --bootstrap-samples 100 \
  --output-stem results/hardware/multi_backend_fixed_n2_live

teleportdim hardware-multi-backend-fixed-n-process-tomography \
  --n-values 2 \
  --backend-names ibm_fez,ibm_torino \
  --shots 256 \
  --delays 0,64,128 \
  --bootstrap-samples 100 \
  --output-stem results/hardware/multi_backend_fixed_n2_process

teleportdim compare-hardware-backends \
  --input-json results/hardware/multi_backend_fixed_n2_live.json,results/hardware/multi_backend_fixed_n2_process.json \
  --n-physical 2 \
  --output-stem results/hardware/multi_backend_fixed_n2_compare
```

This workflow keeps the fixed-`n` comparison backend-specific instead of collapsing every live
run into a single hardware lane. The resulting backend report shows whether the `d=3` versus
`d=4` ordering survives across multiple IBM devices rather than only on `ibm_fez`.

### Theory curve versus hardware divergence

```bash
teleportdim compare-hardware-theory \
  --theory-json results/fixed_n2/n2_compare.json \
  --hardware-json results/hardware/multi_backend_fixed_n2_live.json \
  --n-physical 2 \
  --metrics fidelity,leakage,in_subspace_fidelity \
  --dimensions 2,3,4 \
  --output-stem results/hardware/multi_backend_vs_theory
```

This comparison keeps the theory lane as a baseline prediction and then writes one backend-aware
divergence report plus per-dimension figures showing the theory curve and the signed
`hardware - theory` gap on the shared delay grid.

### Three-lane fixed-`n` thesis table

```bash
teleportdim compare-three-lanes \
  --theory-json results/fixed_n2/n2_compare.json \
  --aer-json results/fixed_n2/aer_n2_compare.json \
  --hardware-json results/hardware/ibm_fez_fixed_n2_delay0_64_128_compare.json,results/hardware/ibm_fez_process_fixed_n2_delay0_64_128_compare.json \
  --n-physical 2 \
  --output-stem results/fixed_n2/three_lane_n2_compare
```

This report is the thesis-facing join point for the three result lanes. It keeps each lane on
its native delay grid, merges the hardware state and hardware process summaries into one
hardware lane, and writes a single markdown/JSON/CSV artifact where the `d=3` vs `d=4`
comparison can be read without assembling multiple files by hand.

## Current limitations

1. **The theory lane is now best treated as a baseline, not the primary result path.**
   The circuit-level Aer lane is the more defensible local result because it includes Bell-pair generation,
   entangling gates, measurements, and feed-forward structure.

   In particular, a pure `T1/T2` theory sweep is not a leakage study: it preserves the
   lowest-basis embedding used for `d < 2^n`. Leakage only becomes visible in the theory lane
   after adding an explicit mixing term such as `t_dep` or `depolarizing_probability`.
   That makes the theory-lane leakage mechanism different from the circuit-lane leakage mechanism,
   so the clean interpretation is "baseline-only comparison" rather than "same-physics parallel lane."

2. **Hardware process tomography now spans the full fixed-`n` comparison set for `n=2`, but it is still preliminary.**
   The repository now includes live same-backend `ibm_fez` process-tomography artifacts for
   `d=2`, `d=3`, and `d=4`, plus a combined fixed-`n` comparison report under
   `results/hardware/ibm_fez_process_fixed_n2_delay0_64_128_compare.{json,csv,md}`.
   The remaining hardware gaps are broader delay sweeps, more shots, repeated runs, and
   validation on more than one backend.

3. **The Markovian lane remains an effective model, not a full noisy circuit simulation.**

4. **The non-Markovian lane is still phenomenological, even though the switching rate is now hardware-anchored.**
   The repository now includes a backend-derived random-telegraph calibration from live
   `ibm_fez` process-fidelity decay, so `switching_probability` no longer has to be chosen
   by hand. But the model is still not a microscopic spectral-density fit; it remains an
   effective fluctuator model matched to a measured coherence timescale.

5. **The marker-defined module split is complete.**
   The package root now re-exports the public API while implementation code lives in
   dedicated files such as `metrics.py`, `simulation.py`, `circuits.py`, `hardware.py`,
   `aer.py`, `reports.py`, `sweeps.py`, and `cli.py`.

## Remaining high-impact work

The most valuable next steps are:

1. extend the hardware process-tomography lane from the current `d=3`, `n=2` cross-check to the full fixed-`n` comparison set,
2. compare circuit-level Aer, theory baseline, and hardware side by side with confidence intervals,
3. replace the remaining compatibility-only facade modules with direct imports in downstream notebooks once consumers have migrated.
