# Channel-Body Deformation in Fixed-Qubit Logical Teleportation

**Author:** Hirresh Sundra  
**Project:** TeleportDim v0.3.1  
**Status:** Channel-deformation reframing draft  
**Primary code artifacts:** `src/teleportdim/noise_bodies.py`, `src/teleportdim/deformation.py`, `src/teleportdim/body_sweeps.py`, `src/teleportdim/fingerprinting.py`

## Abstract

Teleportation fidelity is often reported as a single endpoint number, but a teleported
state is the output of a physical channel. TeleportDim therefore studies fixed-qubit
teleportation as a deformation problem: for fixed physical qubit count \(n\), encoded
dimension \(d\), and environment/body class \(B\), what physical signature separates
leakage, within-subspace damage, coherent drift, Markovian decay, and non-Markovian
memory? The observed logical channel is modeled as

\[
\mathcal{E}_{\mathrm{obs}}^{(d,n,B)}(\rho),
\]

with the ideal teleportation target

\[
\mathcal{E}_{\mathrm{ideal}}^{(d)}(\rho)=\rho.
\]

The central artifact is a deformation vector

\[
\Delta(d,n,B)=
\left[
1-F_{\mathrm{proc}},
1-F_{\mathrm{avg}},
L,
1-F_{\mathrm{sub}},
D_{\mathrm{BLP}},
A_{\mathrm{coh}},
A_{\mathrm{nonunital}}
\right],
\]

where \(F_{\mathrm{proc}}\) is process fidelity, \(F_{\mathrm{avg}}\) is average gate
fidelity, \(L\) is leakage outside the encoded logical subspace, \(F_{\mathrm{sub}}\)
is fidelity conditioned back into the subspace, \(D_{\mathrm{BLP}}\) is a trace-distance
backflow score, \(A_{\mathrm{coh}}\) is probe-state anisotropy, and
\(A_{\mathrm{nonunital}}\) is displacement of the maximally mixed state. This reframing
preserves the existing fixed-\(n\) hardware result: on `ibm_fez`, the full-occupancy
case \(d=4,n=2\) has structurally zero computational-basis leakage but lower process
fidelity than \(d=3,n=2\) at all measured delays. The result is therefore not merely
"which dimension wins"; it is evidence that zero leakage does not imply low channel
deformation.

## I. Research Question

Given a fixed physical qubit budget, how do encoded dimension and structured
environmental bodies deform the logical teleportation channel, and can those
deformations be classified from leakage, process fidelity, state fidelity, and
non-Markovian information-flow signatures?

This question replaces a scalar fidelity comparison with a causal physics map. The
dimension body changes the fill ratio \(\phi=d/2^n\). The leakage body controls whether
unused Hilbert-space levels can absorb probability. The Markovian body tests memoryless
dephasing, amplitude damping, depolarizing, and relaxation-like decay. The
non-Markovian body tests whether information backflow produces trace-distance revivals.
The coherent body tests state-dependent rotations and anisotropic process deformation.
The hardware body provides a real-device fingerprint that can be compared against the
modeled bodies without overclaiming microscopic causality.

## II. Channel Model

Let \(\mathcal{H}_d\cong\mathbb{C}^d\) be the logical Hilbert space and
\(\mathcal{H}_{2^n}\cong(\mathbb{C}^2)^{\otimes n}\) be the fixed physical Hilbert
space. TeleportDim uses the prefix embedding

\[
V_{d,n}|j\rangle = |j\rangle_{\mathrm{comp}},\qquad 0\le j<d.
\]

The code projector is

\[
P_{\mathrm{code}}=\sum_{j=0}^{d-1}|j\rangle\langle j|,
\]

and the leakage projector is

\[
P_{\mathrm{leak}}=I_{2^n}-P_{\mathrm{code}}.
\]

For an output density matrix \(\rho_{\mathrm{out}}\), leakage is

\[
L=\mathrm{Tr}(P_{\mathrm{leak}}\rho_{\mathrm{out}}).
\]

When \(d=2^n\), \(P_{\mathrm{leak}}=0\), so leakage is structurally zero. This is why
the `d=4,n=2` hardware leakage result must be interpreted as definitional rather than
as evidence of unusually clean hardware.

## III. Deformation Vector

The deformation vector implemented in `compute_channel_deformation_vector()` converts
raw records into channel-error coordinates:

| Coordinate | Meaning |
| --- | --- |
| \(1-F_{\mathrm{proc}}\) | process-level channel deformation |
| \(1-F_{\mathrm{avg}}\) | average operational channel error |
| \(L\) | probability outside the encoded subspace |
| \(1-F_{\mathrm{sub}}\) | logical damage after conditioning into the code subspace |
| \(D_{\mathrm{BLP}}\) | non-Markovian information-backflow score |
| \(A_{\mathrm{coh}}\) | probe-state anisotropy / coherent state-dependence |
| \(A_{\mathrm{nonunital}}\) | displacement of the maximally mixed state |

This vector is intentionally metric-level and reproducible. It does not infer a unique
microscopic Hamiltonian from hardware data. Hardware matching is reported only as
phenomenological closeness to a modeled body fingerprint.

## IV. First Supported Claim

The present artifacts support the following conservative claim:

> At fixed \(n=2\), full occupancy \(d=4\) eliminates computational leakage by definition
> but does not minimize logical channel deformation. In the saved `ibm_fez` process
> tomography comparison, \(d=4\) has lower process fidelity than \(d=3\) at all measured
> delays.

This claim is stronger than a simple fidelity race because it separates two mechanisms:
population escape and within-subspace channel deformation.

## V. New Reproducible Entry Points

```bash
teleportdim channel-body-sweep \
  --n-values 2 \
  --dimensions 2,3,4 \
  --bodies ideal,dephasing,amplitude_damping,leakage_mixing,random_telegraph,coherent_z_drift \
  --strengths 0,0.001,0.005,0.01 \
  --delays 0,64,128 \
  --output-stem results/channel_body/n2_body_sweep
```

```bash
teleportdim compare-body-fingerprints \
  --input-json results/channel_body/n2_body_sweep.json \
  --hardware-json results/hardware/ibm_fez_process_fixed_n2_delay0_64_128_compare.json \
  --metrics process_fidelity,average_gate_fidelity,leakage,in_subspace_fidelity,anisotropy,nonunitality \
  --output-stem results/channel_body/ibm_fez_body_match
```

## VI. Limitations

The body models are phenomenological. The random-telegraph lane uses a calibrated
switching-probability interpretation, but it is not yet fitted to backend noise
spectroscopy. The coherent-body lane tests channel anisotropy, not a microscopic
cross-talk Hamiltonian. IBM hardware results should therefore be described as closest
to a modeled deformation fingerprint, not as proof of a unique physical noise source.
