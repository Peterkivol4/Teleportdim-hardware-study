# TeleportDim

**Short description:** Fixed-qubit quantum teleportation study comparing encoded logical dimension, leakage, and channel distortion across theory, Aer, and IBM hardware lanes.

![Fixed-n hardware fidelity comparison](artifacts/hardware/ibm_fez_fixed_n2_delay0_64_128_live_fidelity.png)

**Headline result.** On `ibm_fez` at fixed `n=2`, zero-delay process fidelity falls from `0.7421` at `d=3` to `0.6277` at `d=4`, showing that zero leakage at full occupancy does not imply the best logical teleportation channel (`docs/teleportdim_fixed_n_paper.md`).

Research repository for:

**For fixed physical qubit count `n`, how does logical teleportation fidelity depend on the encoded dimension `d`, and how does subspace leakage change with the fill ratio `φ = d / 2^n` under delay and noise?**

This build hardens the package into a cleaner experiment repo:

- fixed-`n` and leakage-centered thesis framing,
- IBM-hardware lane,
- theory/model lane,
- optional Aer lane,
- process-tomography and channel-fidelity analysis,
- bootstrap statistics for tomography-derived confidence intervals,
- clean comparison reports for `d=3` vs `d=4` at fixed `n=2`,
- optional dependency extras so non-hardware users do not have to install the full IBM/Qiskit stack.

## Snapshot

**Headline result:** At fixed `n=2`, the fully occupied `d=4` encoding has structurally zero leakage yet still yields the worst process fidelity on both Aer and `ibm_fez`; the saved hardware process-tomography comparison separates `d=4` from `d=3` at all measured delays.

![Fixed-n Aer fidelity comparison](artifacts/fixed_n2/aer_fixed_n2_fidelity.png)


## Monolith build

This version collapses the source tree into **one package file**: `src/teleportdim/__init__.py`.

Why:

- keeps the implementation in a single audit surface while the algorithm is still evolving,
- preserves the old import paths through compatibility aliases,
- avoids splitting thesis logic across many files before the design is final.

The conceptual module boundaries are still present inside the monolith via section markers:
`config`, `encoding`, `states`, `metrics`, `process`, `statistics`, `simulation`,
`tomography`, `circuits`, `hardware`, `aer`, `reports`, `sweeps`, and `cli`.

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
teleportdim aer-delay-sweep   --dimension 3   --delays 0,2048,4096,8192   --shots 8192   --correction-mode deferred   --depolarizing-1q 0.001   --depolarizing-2q 0.01   --output-stem artifacts/aer_d3
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
  --output-stem artifacts/aer_fixed_n
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
  --output-stem artifacts/aer_process_d3
```

### 4. Fixed-`n` comparison reports

New report flow for same-hardware comparisons:

```bash
teleportdim compare-fixed-n \
  --input-json artifacts/fixed_n2/aer_fixed_n2.json,artifacts/fixed_n2/aer_process_d2.json,artifacts/fixed_n2/aer_process_d3.json,artifacts/fixed_n2/aer_process_d4.json \
  --n-physical 2 \
  --output-stem artifacts/fixed_n2/aer_n2_compare
```

This generates:

- JSON summary
- CSV summary
- Markdown comparison report

The summary is designed to make the `d=3` vs `d=4` result readable at each delay.

## Example workflows

### Markovian baseline fixed-`n` sweep

```bash
teleportdim markovian-fixed-n-sweep   --n-values 2   --delays 0,2048,4096,8192   --t1 540540   --t2 360360   --t-dep 360360   --bootstrap-samples 200   --confidence-level 0.95   --output-stem artifacts/markovian_n2
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
teleportdim compare-fixed-n   --input-json artifacts/markovian_n2.json   --n-physical 2   --output-stem artifacts/n2_compare
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
  --output-stem artifacts/non_markovian/random_telegraph_blp_n2
```

### Backend-anchored random-telegraph calibration

```bash
teleportdim calibrate-random-telegraph \
  --input-json artifacts/hardware/ibm_fez_process_d3_n2_delay0_64_128.json \
  --dimension 3 \
  --n-physical 2 \
  --metric process_fidelity \
  --dt-ns-per-step 4.0 \
  --fit-mode first_nonzero \
  --output-stem artifacts/non_markovian/ibm_fez_rtn_calibration_d3_n2
```

The random-telegraph lane still uses the relation
`switching_probability = 1 - exp(-dt / τ_corr)`, but the repository no longer needs
to justify `τ_corr` with a purely hand-picked number. Using the live `ibm_fez`
`d=3`, `n=2` process-fidelity decay, the saved calibration artifact
`artifacts/non_markovian/ibm_fez_rtn_calibration_d3_n2.{json,md}` estimates
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
  --output-stem artifacts/hardware/ibm_fez_fixed_n2_delay0_64_128_live
```

The repository now includes both the earlier zero-delay snapshots and a saved live fixed-`n`
delay sweep plus comparison report at the same backend and qubit count:
`artifacts/hardware/ibm_fez_fixed_n2_delay0_64_128_live.{json,csv}` and
`artifacts/hardware/ibm_fez_fixed_n2_delay0_64_128_compare.{json,csv,md}`.

### Same-backend fixed-`n` hardware process tomography (`d=2,3,4`, `n=2`)

```bash
teleportdim hardware-process-tomography \
  --dimension 2 \
  --n-physical 2 \
  --backend-name ibm_fez \
  --shots 256 \
  --delays 0,64,128 \
  --bootstrap-samples 100 \
  --output-stem artifacts/hardware/ibm_fez_process_d2_n2_delay0_64_128

teleportdim hardware-process-tomography \
  --dimension 3 \
  --n-physical 2 \
  --backend-name ibm_fez \
  --shots 256 \
  --delays 0,64,128 \
  --bootstrap-samples 100 \
  --output-stem artifacts/hardware/ibm_fez_process_d3_n2_delay0_64_128
teleportdim hardware-process-tomography \
  --dimension 4 \
  --n-physical 2 \
  --backend-name ibm_fez \
  --shots 256 \
  --delays 0,64,128 \
  --bootstrap-samples 100 \
  --output-stem artifacts/hardware/ibm_fez_process_d4_n2_delay0_64_128

teleportdim compare-fixed-n \
  --input-json artifacts/hardware/ibm_fez_process_d2_n2_delay0_64_128.json,artifacts/hardware/ibm_fez_process_d3_n2_delay0_64_128.json,artifacts/hardware/ibm_fez_process_d4_n2_delay0_64_128.json \
  --n-physical 2 \
  --output-stem artifacts/hardware/ibm_fez_process_fixed_n2_delay0_64_128_compare
```

The repository now includes saved live same-backend hardware process-tomography artifacts for
all three logical dimensions at fixed `n=2`:
`artifacts/hardware/ibm_fez_process_d2_n2_delay0_64_128.{json,csv}`,
`artifacts/hardware/ibm_fez_process_d3_n2_delay0_64_128.{json,csv}`,
and `artifacts/hardware/ibm_fez_process_d4_n2_delay0_64_128.{json,csv}`.

The compact fixed-`n` comparison table and detailed markdown report live at
`artifacts/hardware/ibm_fez_process_fixed_n2_delay0_64_128_compare.{json,csv,md}`.
The repository also keeps the calibrated `d=3` hardware-vs-Aer process comparison artifact
`artifacts/hardware/ibm_fez_vs_aer_process_d3_n2_compare.{json,md}` as a same-delay cross-check.
That saved Aer cross-check now uses `8192` shots and `200` bootstrap resamples rather than the
earlier `256`-shot setting, because over `0-128 dt` at `dt = 4 ns` the added delay noise is
small enough that low-shot tomography can produce a non-monotonic process-fidelity estimate.
The saved rerun restores the expected monotone Aer trend across `0,64,128 dt`.

### Three-lane fixed-`n` thesis table

```bash
teleportdim compare-three-lanes \
  --theory-json artifacts/fixed_n2/n2_compare.json \
  --aer-json artifacts/fixed_n2/aer_n2_compare.json \
  --hardware-json artifacts/hardware/ibm_fez_fixed_n2_delay0_64_128_compare.json,artifacts/hardware/ibm_fez_process_fixed_n2_delay0_64_128_compare.json \
  --n-physical 2 \
  --output-stem artifacts/fixed_n2/three_lane_n2_compare
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
   `artifacts/hardware/ibm_fez_process_fixed_n2_delay0_64_128_compare.{json,csv,md}`.
   The remaining hardware gaps are broader delay sweeps, more shots, repeated runs, and
   validation on more than one backend.

3. **The Markovian lane remains an effective model, not a full noisy circuit simulation.**

4. **The non-Markovian lane is still phenomenological, even though the switching rate is now hardware-anchored.**
   The repository now includes a backend-derived random-telegraph calibration from live
   `ibm_fez` process-fidelity decay, so `switching_probability` no longer has to be chosen
   by hand. But the model is still not a microscopic spectral-density fit; it remains an
   effective fluctuator model matched to a measured coherence timescale.

5. **The legacy monolith is still in place.**
   The planned extraction remains `config.py`, `encoding.py`, `states.py`, `metrics.py`,
   `process.py`, `statistics.py`, `simulation.py`, `tomography.py`, `circuits.py`,
   `hardware.py`, `aer.py`, `reports.py`, `sweeps.py`, and `cli.py`.

## Remaining high-impact work

The most valuable next steps are:

1. extend the hardware process-tomography lane from the current `d=3`, `n=2` cross-check to the full fixed-`n` comparison set,
2. compare circuit-level Aer, theory baseline, and hardware side by side with confidence intervals,
3. split the monolith into the planned submodules once the experiment surface is stable.
