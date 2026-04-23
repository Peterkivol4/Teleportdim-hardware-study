# Fixed-Physical-Qubit Logical Teleportation in Partially Filled Hilbert Spaces:
# Leakage, Channel Fidelity, and Delay Dependence across Effective Models, Aer, and IBM Heron Hardware

**Author:** Hirresh Sundra  
**Project:** TeleportDim v0.3.1  
**Format:** Thesis-style research manuscript / arXiv-ready draft  
**Primary repository artifact:** `src/teleportdim/__init__.py`  

## Abstract

Quantum teleportation is usually benchmarked by varying the logical dimension and the physical resource count simultaneously, which obscures whether performance changes originate from larger Hilbert spaces, deeper circuits, or altered leakage structure. This work reformulates the problem in a fixed-physical-qubit setting: for constant physical register size \(n\), how do logical teleportation fidelity, subspace leakage, and channel fidelity depend on the logical dimension \(d\) and the fill ratio \(\phi = d / 2^n\)? The resulting control variable isolates whether operating in a partially occupied codespace is itself a source of performance variation. The implementation, TeleportDim, realizes this question in three coupled lanes: an effective Markovian baseline, a circuit-faithful Aer lane with noisy teleportation and logical process tomography, and a live IBM Quantum hardware lane executed on the 156-qubit `ibm_fez` backend, a Heron r2 processor with support for `delay` and dynamic feed-forward [22]–[24].

The central experiment fixes \(n=2\) and compares \(d \in \{2,3,4\}\). The baseline theory lane predicts monotone degradation with delay but does **not** separate \(d=3\) and \(d=4\) in state fidelity: the consolidated report finds significant \(d=4-d=3\) state-fidelity separation at \(0/4\) delays [Table 2]. By contrast, the circuit-faithful Aer lane separates these dimensions at every tested delay: \(d=4\) underperforms \(d=3\) in state fidelity at \(4/4\) delays and in process fidelity at \(4/4\) delays [Table 4]. The hardware lane confirms the same qualitative conclusion. Canonical-probe state tomography on `ibm_fez` yields zero-delay fidelities \(F_{d=2}=0.8864\), \(F_{d=3}=0.8697\), and \(F_{d=4}=0.8688\), all above the classical measure-and-prepare limits \(2/(d+1)\), while fixed-\(n\) process tomography gives zero-delay process fidelities \(F_{\mathrm{proc}}=0.8790\), \(0.7421\), and \(0.6277\) for \(d=2,3,4\), respectively [Tables 5 and 6]. The full-occupancy case \(d=4\) exhibits exactly zero leakage by definition, yet it is the worst channel in both Aer and hardware. Therefore, leakage suppression alone does not characterize logical teleportation quality; the principal penalty at \(\phi=1\) is within-subspace channel distortion rather than population escape. This is the manuscript’s main scientific conclusion.

## I. Introduction

### A. Motivation

Quantum teleportation is a foundational primitive for quantum communication, modular quantum computing, and measurement-assisted circuit synthesis [1], [14]. In most experimental and software studies, however, the logical information content and the physical hardware budget are varied together. A qubit teleportation protocol and a qutrit or ququart protocol are then compared under different encodings, different physical register sizes, or different optical resources [15]–[18]. That comparison is useful for demonstrating protocol generality, but it is not a controlled test of how the *logical dimension itself* affects execution quality on a fixed physical platform.

The TeleportDim project reframes the question. Let the physical register size \(n\) be fixed. The full physical Hilbert space then has dimension \(2^n\), but the logical subspace may be any \(d \le 2^n\). The quantity

$$
\phi \equiv \frac{d}{2^n}
\tag{1}
$$

measures how fully the available Hilbert space is occupied by the encoding. At fixed \(n\), changing \(d\) changes both the logical alphabet size and the codimension of the unused subspace, thereby changing the *possibility* of leakage without changing the underlying qubit count. This is the organizing variable of the present work.

The most informative setting is \(n=2\), where \(d=3\) and \(d=4\) use the same number of physical qubits but different fill ratios, \(\phi=0.75\) and \(\phi=1\), respectively. The case \(d=4\) occupies the full four-dimensional Hilbert space, so there is no remaining leakage subspace. Any reported leakage must therefore vanish structurally. The case \(d=3\) leaves one basis state outside the code space, making leakage measurable and physically interpretable. This pair yields a clean, fixed-resource comparison between partial and full Hilbert-space occupancy.

### B. Problem Statement

The thesis question is:

> For fixed physical qubit count \(n\), how does logical teleportation fidelity depend on logical dimension \(d\), and how does leakage change with the fill ratio \(\phi=d/2^n\) under delay and noise?

The formulation is intentionally two-layered. First, it asks whether higher logical dimension changes teleportation quality even when the physical register is held constant. Second, it asks whether any such change is mediated by leakage, by within-subspace distortion, or by both.

### C. Gap in the Literature

Three gaps motivate this work.

First, the high-dimensional teleportation literature has established genuine qudit teleportation experimentally, including qutrit teleportation and process-matrix certification in photonic platforms [16], [17], but it has not targeted the fixed-\(n\) superconducting setting addressed here. Second, software studies often report end-state fidelity without channel-level diagnostics, even though teleportation is naturally a quantum channel and should be analyzed through process fidelity and average gate fidelity [4], [7], [8]. Third, NISQ-era dynamic-circuit capabilities now make real-time feed-forward and delay insertion practical on superconducting hardware [27]–[30], so a controlled fixed-\(n\) teleportation study can now be executed on live IBM hardware rather than only in simplified theory or post-selected optical experiments.

### D. Contributions

This manuscript makes the following contributions.

- It formalizes fixed-\(n\) teleportation as a fill-ratio study, with \(\phi=d/2^n\) as the central experimental control variable.
- It defines a three-lane evaluation stack: an effective Markovian baseline, a circuit-faithful Aer lane, and a live IBM hardware lane.
- It extends the repository from state fidelity and leakage to full logical process tomography, including process fidelity and average gate fidelity.
- It applies multinomial bootstrap resampling to tomography counts so that point estimates and confidence intervals are derived from the same dataset [Listing 2], avoiding the internal inconsistency that occurs when point estimates and intervals are computed from independent noisy runs.
- It reports the first repository-wide three-lane fixed-\(n\) comparison artifact joining theory, Aer, and hardware results for \(d=2,3,4\) at \(n=2\) [Table 2].
- It identifies the central physical result: full Hilbert-space occupancy (\(d=4\), \(\phi=1\)) removes leakage by definition but does not improve the logical teleportation channel; instead, \(d=4\) is consistently worse than \(d=3\) in circuit-faithful Aer and in hardware process tomography [Tables 3 and 5].

### E. Paper Outline

Section II reviews the relevant literature on teleportation, high-dimensional encoding, process tomography, and dynamic superconducting hardware. Section III develops the mathematical framework. Section IV explains the software and experimental methodology. Section V documents the implementation and cites the governing code paths. Section VI specifies the experimental setup. Section VII reports the numerical and hardware results. Section VIII interprets the findings, including negative and null results. Sections IX and X discuss future work and conclude. Appendices provide notation, code excerpts, reproduction instructions, and raw tables.

## II. Background and Related Work

### A. Teleportation as a Quantum Channel

The modern teleportation protocol was introduced by Bennett *et al.* in 1993 [1]. In its standard form, teleportation transfers an unknown quantum state using pre-shared entanglement, Bell-basis measurement, and classical communication. Teleportation is now understood not merely as a communication primitive but as a channel-construction primitive for distributed quantum computation, gate teleportation, and measurement-based architectures [14], [32].

The channel perspective is especially important here. For a teleportation device, the relevant question is not only whether a single probe state survives transmission, but whether the induced channel approximates the identity over the full logical state space. Horodecki *et al.* gave a direct relation between teleportation fidelity and singlet fraction in arbitrary dimension [4], while Nielsen derived the standard relation between process fidelity and average gate fidelity [7]. These results supply the correct channel-level metrics for the present work.

### B. High-Dimensional Teleportation and Qudit Information

High-dimensional teleportation is valuable because qudits can encode larger alphabets, exploit larger entangled state spaces, and potentially reduce some overheads relative to qubit-only protocols [15], [18]. Theoretical and optical advances have demonstrated qutrit teleportation and general high-dimensional schemes [15]–[17]. Luo *et al.* reported qutrit teleportation with fidelity \(0.75(1)\), exceeding both the qutrit state-estimation limit \(1/2\) and the maximal qubit–qutrit overlap \(2/3\) [16]. Hu *et al.* subsequently reported experimental high-dimensional teleportation with a qutrit process matrix and process fidelity \(0.596 \pm 0.037\) [17].

These studies establish that high-dimensional teleportation is experimentally meaningful. However, they do not isolate the fixed-resource question considered here: what happens when the number of physical qubits is held constant and only the occupied logical subspace changes?

### C. High-Dimensional Hardware beyond Photonics

High-dimensional quantum information is no longer restricted to photonic spatial modes. Reviews by Erhard, Krenn, and Zeilinger [18] and by Hu *et al.* [14] document the broader emergence of high-dimensional entanglement and teleportation. Recent solid-state work demonstrates native qudit control in superconducting and donor-spin systems. Fernández de Fuentes *et al.* navigated a 16-dimensional donor-spin qudit Hilbert space [19], and Nguyen *et al.* demonstrated a qudit-based superconducting processor exploiting bosonic ladder structure [20]. These studies motivate the present software-and-hardware question: if high-dimensional logical structure is physically relevant, how does it behave in an explicitly teleported superconducting protocol executed on qubit hardware?

### D. Process Tomography and Statistical Treatment

Quantum process tomography reconstructs a channel from input-output density-matrix pairs, typically by combining a tomographically complete input ensemble with informationally complete measurements on the output [8]. The channel can then be represented through a superoperator or its Choi state using the Jamiołkowski isomorphism [5], [6]. O’Brien *et al.* demonstrated the usefulness of process tomography for entangling gates in 2004 [8]. Recent work continues to improve robustness and scalability [31], but the exponential cost remains substantial.

The present repository adopts a direct superoperator reconstruction from a \(d^2\)-element logical probe ensemble [Listing 2]. Because finite-shot tomography is statistically noisy and nonlinear estimators can be biased [13], all process metrics in the Aer and hardware lanes are accompanied by multinomial-bootstrap confidence intervals derived from the same counts used for the point estimate [Listing 2]. This design is methodologically conservative and directly addresses a common failure mode in small-shot tomography studies.

### E. Dynamic Circuits and IBM Quantum Hardware

Real-time classical feed-forward is now a practical feature of IBM superconducting hardware and software interfaces [22]–[30]. Córcoles *et al.* demonstrated dynamic-circuit algorithms with superconducting qubits in 2021 [27]. More recent work has shown that dynamic circuits can enable long-range entanglement, efficient quantum Fourier transform implementations, and real-time classical coupling between separate processors [28]–[30]. These capabilities are directly relevant to teleportation, because standard teleportation requires mid-circuit measurement and conditional Pauli correction.

The present experiments run on `ibm_fez`, which IBM documents as a 156-qubit Heron r2 backend [22], [23]. The Heron family supports `delay` and `if_else` as native operations [24], which makes it suitable for delay-dependent dynamic teleportation on real hardware.

## III. Theoretical Framework

### A. Logical and Physical Hilbert Spaces

Let \(n\) denote the number of physical qubits. The physical Hilbert space is

$$
\mathcal{H}_{\mathrm{phys}} = (\mathbb{C}^2)^{\otimes n},
\qquad
\dim \mathcal{H}_{\mathrm{phys}} = 2^n.
\tag{2}
$$

Let \(d \le 2^n\) denote the logical dimension. The logical Hilbert space is

$$
\mathcal{H}_d \cong \mathbb{C}^d.
\tag{3}
$$

The repository uses a prefix embedding

$$
\mathcal{E}_d : \mathcal{H}_d \rightarrow \mathcal{H}_{\mathrm{phys}},
\qquad
\mathcal{E}_d \lvert j \rangle = \lvert j \rangle_{\mathrm{comp}},
\quad
0 \le j \le d-1,
\tag{4}
$$

where \(\lvert j \rangle_{\mathrm{comp}}\) is the computational basis state of the \(n\)-qubit register indexed by integer \(j\). For a pure logical state

$$
\lvert \psi_d \rangle = \sum_{j=0}^{d-1} \alpha_j \lvert j \rangle,
\qquad
\sum_{j=0}^{d-1} |\alpha_j|^2 = 1,
\tag{5}
$$

the embedded physical state is

$$
\lvert \psi_{\mathrm{emb}} \rangle = \mathcal{E}_d \lvert \psi_d \rangle.
\tag{6}
$$

The code projector and leakage projector are

$$
P_{\mathrm{code}} = \sum_{j=0}^{d-1} \lvert j \rangle \langle j \rvert,
\qquad
P_{\mathrm{leak}} = I_{2^n} - P_{\mathrm{code}}.
\tag{7}
$$

The fill ratio is repeated here for convenience:

$$
\phi = \frac{d}{2^n}.
\tag{8}
$$

### B. Structural Leakage Result

**Lemma 1.** If \(d = 2^n\), then \(P_{\mathrm{leak}} = 0\), and the leakage observable is identically zero for every physical density operator supported on \(\mathcal{H}_{\mathrm{phys}}\).

**Proof.** If \(d=2^n\), then the logical prefix basis spans the full physical computational basis. Hence \(P_{\mathrm{code}} = I_{2^n}\), and therefore \(P_{\mathrm{leak}} = I_{2^n} - I_{2^n} = 0\). For any physical density operator \(\rho\),

$$
L(\rho) = \mathrm{Tr}(P_{\mathrm{leak}} \rho) = \mathrm{Tr}(0 \cdot \rho) = 0.
\tag{9}
$$

\(\square\)

This elementary observation matters experimentally. Any reported \(L=0\) for \(d=4\), \(n=2\) must be interpreted as a definitional consequence of the encoding rather than as evidence of unusually benign hardware behavior.

### C. Teleportation Channel and Observables

For fixed \(d\), \(n\), and delay parameter \(\tau\), define the teleportation channel

$$
\mathcal{T}_{d,n,\tau} : \mathcal{D}(\mathcal{H}_d) \rightarrow \mathcal{D}(\mathcal{H}_{\mathrm{phys}}),
\tag{10}
$$

where \(\mathcal{D}(\cdot)\) denotes density operators over the relevant Hilbert space. The channel need not preserve the logical code space, because noisy circuit execution may populate states outside the embedding subspace.

For a pure logical input \(\rho_{\mathrm{in}} = \lvert \psi_d \rangle \langle \psi_d \rvert\) and physical output \(\rho_{\mathrm{out}}\), the embedded-state fidelity is

$$
F(\rho_{\mathrm{in}}, \rho_{\mathrm{out}})
=
\langle \psi_{\mathrm{emb}} \rvert \rho_{\mathrm{out}} \lvert \psi_{\mathrm{emb}} \rangle.
\tag{11}
$$

Leakage is

$$
L(\rho_{\mathrm{out}}) = \mathrm{Tr}(P_{\mathrm{leak}} \rho_{\mathrm{out}}).
\tag{12}
$$

The renormalized logical output state is

$$
\tilde{\rho}_{\mathrm{log}}
=
\frac{P_{\mathrm{code}} \rho_{\mathrm{out}} P_{\mathrm{code}}}{1 - L(\rho_{\mathrm{out}})},
\qquad
\text{for } L(\rho_{\mathrm{out}}) < 1.
\tag{13}
$$

The in-subspace fidelity is then

$$
F_{\mathrm{sub}}(\rho_{\mathrm{in}}, \rho_{\mathrm{out}})
=
\langle \psi_d \rvert \tilde{\rho}_{\mathrm{log}} \lvert \psi_d \rangle.
\tag{14}
$$

Equation (14) separates logical corruption within the encoded subspace from actual codespace escape. This distinction is the conceptual center of the thesis.

### D. Process Fidelity and Average Gate Fidelity

Let

$$
\lvert \Phi_d \rangle
=
\frac{1}{\sqrt{d}}
\sum_{j=0}^{d-1}
\lvert j \rangle \otimes \lvert j \rangle
\tag{15}
$$

denote the maximally entangled logical state. The Choi state of the logical channel restricted to the code space is

$$
J(\mathcal{T}_{d,n,\tau})
=
(I \otimes \mathcal{T}_{d,n,\tau})(\lvert \Phi_d \rangle \langle \Phi_d \rvert).
\tag{16}
$$

The process fidelity with respect to the identity channel is

$$
F_{\mathrm{proc}}
=
\langle \Phi_d \rvert J(\mathcal{T}_{d,n,\tau}) \lvert \Phi_d \rangle.
\tag{17}
$$

The repository converts this quantity into average gate fidelity via the standard relation [7],

$$
F_{\mathrm{avg}}
=
\frac{d F_{\mathrm{proc}} + 1}{d+1},
\tag{18}
$$

implemented directly in [Listing 1: `average_gate_fidelity_from_process_fidelity()`].

### E. Probe-Set and Measurement Complexity

The canonical state-tomography lane uses the probe ensemble

$$
\mathcal{P}_{\mathrm{can}}(d)
=
\{\lvert 0 \rangle,\ldots,\lvert d-1 \rangle,\lvert \widetilde{0} \rangle_F\},
\tag{19}
$$

where \(\lvert \widetilde{0} \rangle_F\) is the \(k=0\) Fourier state used by the repository's canonical probe-state generator. Therefore,

$$
|\mathcal{P}_{\mathrm{can}}(d)| = d+1.
\tag{20}
$$

The process-tomography probe ensemble constructed in [Listing 2] contains the \(d\) computational basis states plus the real and imaginary two-level superpositions for every unordered pair \((i,j)\), giving

$$
|\mathcal{P}_{\mathrm{proc}}(d)|
=
d + 2\binom{d}{2}
=
d^2.
\tag{21}
$$

Output-state tomography on \(n\) physical Bob qubits uses every Pauli-basis string in \(\{X,Y,Z\}^n\), so the number of measurement settings is

$$
N_{\mathrm{bases}}(n) = 3^n.
\tag{22}
$$

Hence the total number of circuits per delay point is

$$
N_{\mathrm{state}}(d,n) = (d+1)3^n,
\qquad
N_{\mathrm{proc}}(d,n) = d^2 3^n.
\tag{23}
$$

For the core experiment \(n=2\), one obtains:

- \(N_{\mathrm{state}}(2,2)=27\),
- \(N_{\mathrm{state}}(3,2)=36\),
- \(N_{\mathrm{state}}(4,2)=45\),
- \(N_{\mathrm{proc}}(2,2)=36\),
- \(N_{\mathrm{proc}}(3,2)=81\),
- \(N_{\mathrm{proc}}(4,2)=144\).

The process-tomography cost therefore scales quadratically in \(d\) at fixed \(n\), while the measurement-basis count depends only on the physical register size.

## IV. Methodology and System Design

### A. Three-Lane Experimental Architecture

The repository executes the same scientific question through three complementary lanes.

1. **Theory baseline / effective-model lane.**  
   This lane evolves the embedded logical density matrix directly under phenomenological \(T_1\), \(T_2\), and optional depolarizing mixing through `markovian_delay_density()`. It is intentionally cheap and analytically transparent, but it does **not** execute the teleportation circuit. It is therefore a baseline model rather than a circuit-faithful predictor.

2. **Aer circuit lane.**  
   This lane constructs the full teleportation circuit, inserts explicit `delay` instructions after Bell-pair generation, performs output-state tomography over all Pauli bases, and reconstructs process fidelity and average gate fidelity [Listing 3]. This is the primary local validation path before hardware.

3. **IBM hardware lane.**  
   This lane executes the same protocol through IBM Runtime primitives on `ibm_fez`, including dynamic correction via mid-circuit measurement and feed-forward, and reconstructs both state and process observables from live counts [Listing 4].

This layered design is scientifically useful because each lane can fail differently. The theory lane can miss circuit-induced distortion; the Aer lane can underestimate hardware drift; the hardware lane can be shot-limited and calibration-sensitive. Agreement across lanes is therefore informative, and disagreement is often more informative still.

### B. Algorithmic Flow

The core workflow is summarized in Algorithm 1.

```latex
\begin{algorithm}[t]
\caption{Fixed-\(n\) logical teleportation sweep}
\KwIn{Logical dimensions \(D\), fixed physical-qubit count \(n\), delay grid \(\Tau\), backend mode \(m \in \{\mathrm{theory},\mathrm{Aer},\mathrm{hardware}\}\)}
\KwOut{Records containing \(F\), \(L\), \(F_{\mathrm{sub}}\), and when available \(F_{\mathrm{proc}}, F_{\mathrm{avg}}\)}
\ForEach{\(d \in D\)}{
  resolve \(n=\lceil \log_2 d \rceil\) unless provided\;
  construct canonical probe set \(\mathcal{P}_{\mathrm{can}}(d)\) or process probe set \(\mathcal{P}_{\mathrm{proc}}(d)\)\;
  \ForEach{\(\tau \in \Tau\)}{
    build teleportation circuit with Bell-pair generation, delay block, Bell measurement, and dynamic or deferred correction\;
    append every Pauli-basis measurement string in \(\{X,Y,Z\}^n\)\;
    execute all tomography circuits on the selected lane\;
    reconstruct output density matrices\;
    compute \(F\), \(L\), and \(F_{\mathrm{sub}}\)\;
    \If{process tomography}{
      reconstruct the logical superoperator and compute \(F_{\mathrm{proc}}\) and \(F_{\mathrm{avg}}\)\;
    }
    bootstrap the observed counts to obtain confidence intervals\;
  }
}
\end{algorithm}
```

### C. Delay Placement and Correction Model

The delay block is inserted *after* Bell-pair generation and *before* Bell-state measurement. This choice isolates storage-like decoherence of the entanglement resource rather than delaying the state-preparation stage. In the dynamic-correction configuration, Bell outcomes are measured into classical bits and used immediately to apply \(X\) and \(Z\) corrections to Bob’s qubits [Listing 3]. In the deferred-correction configuration, the Bell frame is corrected in post-processing rather than physically enacted on the device.

### D. Statistical Procedure

For each fixed-\(d\), fixed-delay record, the pipeline computes an “observed” estimate from the collected counts and then bootstraps the same counts multinomially to estimate confidence intervals [Listing 2]. This design prevents a subtle but serious error: if point estimates and confidence intervals are derived from different stochastic runs, the point estimate can lie outside its own confidence interval. The current implementation avoids that pathology by construction.

### E. Figures and Artifact Model

The repository exports PNG, JSON, CSV, and Markdown artifacts for every major sweep. This manuscript uses the saved figures directly as figure artifacts and the saved JSON/Markdown summaries as the authoritative numerical record.

![Figure 1](../artifacts/fixed_n2/markovian_n2_leakage.png)

**Figure 1.** Theory-lane leakage versus delay for the fixed-\(n=2\) Markovian baseline. The effective model produces leakage for \(d<2^n\) only because an explicit depolarizing/codespace-mixing term is added; the \(d=4\) curve is structurally pinned to zero because no leakage subspace exists.

![Figure 2](../artifacts/fixed_n2/aer_fixed_n2_fidelity.png)

**Figure 2.** Aer circuit-lane fidelity versus delay for \(d=2,3,4\) at fixed \(n=2\). The circuit-faithful lane shows a clear and monotone dimension ordering \(d=2 > d=3 > d=4\) across the full \(0\)–\(8192\) dt grid.

![Figure 3](../artifacts/hardware/ibm_fez_fixed_n2_delay0_64_128_live_fidelity.png)

**Figure 3.** Live hardware state-fidelity sweep on `ibm_fez` for fixed \(n=2\), delays \(0,64,128\) dt. The short hardware grid is visibly noisier than the Aer grid because the experiment uses only \(256\) shots per circuit and only three delay points.

![Figure 4](../artifacts/non_markovian/random_telegraph_blp_n2_blp.png)

**Figure 4.** Random-telegraph BLP scan at fixed \(n=2\). For all \(d \in \{2,3,4\}\), the BLP measure decreases monotonically with switching probability, as expected for progressively shorter correlation time.

## V. Implementation

### A. Software Stack

The repository is implemented in Python and distributed as the `teleportdim` package [Listing 1]. The package metadata requires Python \(\ge 3.11\), while the validated environment used for the final repository pass employed Python 3.13 and the package versions archived in `requirements-lock.txt`: Qiskit 2.3.0, Qiskit Aer 0.17.2, Qiskit IBM Runtime 0.46.1, NumPy 2.3.5, Matplotlib 3.10.6, and PyTest 8.4.2 [33]–[35]. A final repository validation executed the complete test suite with result `69 passed, 1 skipped`, establishing that the draft is paired with a functioning and reproducible codebase.

Although the current build is monolithic, conceptual module boundaries are preserved internally as `config`, `encoding`, `states`, `metrics`, `process`, `statistics`, `simulation`, `tomography`, `circuits`, `hardware`, `aer`, `reports`, `sweeps`, and `cli`. That structure is sufficient for code citation even before physical file extraction.

### B. Listing 1: Metric Conversion

**Listing 1.** `average_gate_fidelity_from_process_fidelity()` in `src/teleportdim/__init__.py`, lines 404–412. This function implements Eq. (18) exactly.

```python
def average_gate_fidelity_from_process_fidelity(process_fidelity: float, dimension: int) -> float:
    """Convert entanglement/process fidelity into average gate fidelity.

    The formula used is ``F_avg = (d * F_process + 1) / (d + 1)`` for a ``d``-dimensional
    logical channel.
    """
    fp = float(process_fidelity)
    d = float(dimension)
    return (d * fp + 1.0) / (d + 1.0)
```

**Annotation.**

- Line 1 takes the logical dimension \(d\), not the physical dimension \(2^n\); this is the correct normalization for a logical channel.
- Line 6 is a direct software realization of Eq. (18).

### C. Listing 2: Process Probe Set and Bootstrap

**Listing 2.** `process_tomography_probe_states()` and `bootstrap_process_tomography_metrics()`, lines 651–668 and 890–936. These routines determine the tomography identifiability and the uncertainty quantification.

```python
def process_tomography_probe_states(dimension: int) -> list[np.ndarray]:
    states = [computational_basis_state(dimension, index) for index in range(dimension)]
    for left in range(dimension):
        for right in range(left + 1, dimension):
            plus = np.zeros(dimension, dtype=complex)
            plus[left] = 1.0
            plus[right] = 1.0
            states.append(normalize_logical_state(plus, dimension))

            plus_i = np.zeros(dimension, dtype=complex)
            plus_i[left] = 1.0
            plus_i[right] = 1.0j
            states.append(normalize_logical_state(plus_i, dimension))
    return states
```

```python
def bootstrap_process_tomography_metrics(
    dimension: int,
    input_states: Sequence[np.ndarray],
    setting_counts_by_target: Sequence[dict[str, dict[str, int]]],
    *,
    n_physical: int | None = None,
    bootstrap_samples: int = 200,
    confidence_level: float = 0.95,
    seed: int | None = None,
) -> dict[str, float]:
    rng = np.random.default_rng(seed)
    process_values: list[float] = []
    gate_values: list[float] = []
    input_densities = [pure_state_density(state) for state in input_states]
    for _ in range(bootstrap_samples):
        output_densities: list[np.ndarray] = []
        for setting_counts in setting_counts_by_target:
            resampled_setting_counts = {
                basis: resample_counts_multinomial(counts, rng=rng)
                for basis, counts in setting_counts.items()
            }
            rho = reconstruct_density_matrix(resampled_setting_counts)
            output_densities.append(
                renormalized_logical_subspace_density(rho, dimension, n_physical)
            )
        superoperator = reconstruct_superoperator(input_densities, output_densities)
        process_fidelity = process_fidelity_to_identity(superoperator, dimension)
        process_values.append(process_fidelity)
        gate_values.append(
            average_gate_fidelity_from_process_fidelity(process_fidelity, dimension)
        )
```

**Annotation.**

- The probe-set construction produces \(d + 2\binom{d}{2}=d^2\) states, proving Eq. (21).
- The `plus` and `plus_i` states are the real and imaginary coherence probes needed to span the off-diagonal operator space.
- The bootstrap loop resamples counts *per basis setting*, preserving the multinomial shot model for each tomographic measurement setting.
- The physical output density is projected back into the logical code space before superoperator reconstruction, ensuring that process fidelity measures channel quality within the intended logical subspace rather than total-state fidelity in the full \(2^n\)-dimensional space.

### D. Listing 3: Teleportation Circuit Construction

**Listing 3.** `build_block_teleportation_circuit()` and `append_output_measurements()`, lines 1900–1985.

```python
def build_block_teleportation_circuit(
    logical_state: Sequence[complex],
    dimension: int,
    *,
    n_physical: int | None = None,
    delay_after_entanglement_dt: int = 0,
    correction_mode: str = "dynamic",
    add_barriers: bool = True,
) -> TeleportationProgram:
    n = resolved_n_physical(dimension, n_physical)
    q = QuantumRegister(3 * n, "q")
    bell_bits = ClassicalRegister(2 * n, "bell")
    qc = QuantumCircuit(q, bell_bits)

    source = tuple(range(0, n))
    alice = tuple(range(n, 2 * n))
    bob = tuple(range(2 * n, 3 * n))

    prepare_embedded_logical_state(qc, source, logical_state, dimension, n)
    for a, b in zip(alice, bob):
        _add_bell_pair(qc, a, b)

    if delay_after_entanglement_dt > 0:
        for qb in (*alice, *bob):
            qc.delay(delay_after_entanglement_dt, qb, unit="dt")

    for i, (s, a, b) in enumerate(zip(source, alice, bob)):
        qc.cx(s, a)
        qc.h(s)
        qc.measure(s, bell_bits[2 * i])
        qc.measure(a, bell_bits[2 * i + 1])
        if correction_mode == "dynamic":
            with qc.if_test((bell_bits[2 * i + 1], 1)):
                qc.x(b)
            with qc.if_test((bell_bits[2 * i], 1)):
                qc.z(b)
```

**Annotation.**

- The circuit allocates \(3n\) qubits: source, Alice’s Bell-half, and Bob’s Bell-half.
- The Bell-pair block is built before the delay, so the delay degrades the entanglement resource rather than the input-state preparation.
- The two measured classical bits per logical qubit implement the standard teleportation frame.
- The `if_test` blocks are the software manifestation of dynamic circuits and require backend support for `if_else` [24], [27]–[30].

### E. Listing 4: Hardware Lane Process Tomography

**Listing 4.** Excerpt from `run_hardware_fixed_n_process_tomography()`, lines 4527–4656.

```python
for sweep in configs:
    n_physical = resolved_n_physical(sweep.dimension, sweep.n_physical)
    input_states = process_tomography_probe_states(sweep.dimension)
    input_densities = [pure_state_density(state) for state in input_states]
    for delay_dt in sweep.delay_dt_values:
        setting_counts_by_probe = _collect_hardware_setting_counts_for_states(
            input_states,
            sweep.dimension,
            n_physical=n_physical,
            delay_dt=int(delay_dt),
            backend_config=backend_config,
            backend=backend,
            execution_dependencies=execution_dependencies,
        )
        probe_records: list[dict[str, Any]] = []
        logical_outputs: list[np.ndarray] = []
        for logical_state, setting_counts in zip(input_states, setting_counts_by_probe):
            state_record, rho = _hardware_state_metrics_from_setting_counts(
                logical_state,
                sweep.dimension,
                setting_counts,
                n_physical=n_physical,
                delay_dt=int(delay_dt),
                dt_seconds=dt_seconds,
                backend_name=backend.name,
                backend_config=backend_config,
                state_family="process_tomography_probe",
                simulation_lane="ibm_runtime_process_tomography",
            )
            probe_records.append(state_record)
            logical_outputs.append(
                renormalized_logical_subspace_density(rho, sweep.dimension, n_physical)
            )
        superoperator = reconstruct_superoperator(input_densities, logical_outputs)
        process_fidelity = process_fidelity_to_identity(superoperator, sweep.dimension)
```

**Annotation.**

- Hardware process tomography is implemented as a direct extension of the state-tomography lane rather than as a separate experimental stack.
- The `simulation_lane="ibm_runtime_process_tomography"` tag is propagated into the saved JSON artifacts, which makes the downstream reporting reproducible and unambiguous.
- The same live counts drive both state observables and process observables, which is essential for coherent uncertainty reporting.

## VI. Experimental Setup

### A. Core Fixed-\(n\) Design

All principal experiments fix \(n=2\) physical qubits per logical block and compare \(d=2,3,4\). The corresponding fill ratios are:

- \(d=2\): \(\phi=0.5\),
- \(d=3\): \(\phi=0.75\),
- \(d=4\): \(\phi=1\).

The logical output block always occupies the Bob register of an encoded teleportation circuit built from \(3n=6\) physical qubits. Consequently, backend validation requires at least six available qubits for the \(n=2\) experiment.

### B. Theory Baseline

The effective-model lane uses the delay grid

$$
\Tau_{\mathrm{theory}} = \{0, 2048, 4096, 8192\}\ \mathrm{dt},
\tag{24}
$$

mapped through the Aer calibration \(0.222222\ldots\ \mathrm{ns}/\mathrm{dt}\), yielding delays \(0\), \(455.111\), \(910.222\), and \(1820.444\ \mathrm{ns}\) [Table 3]. The baseline parameters are archived in the JSON records:

- \(T_1 = 540540\ \mathrm{dt}\),
- \(T_2 = 360360\ \mathrm{dt}\),
- \(T_{\mathrm{dep}} = 360360\ \mathrm{dt}\),
- canonical-probe bootstrap samples \(=200\),
- confidence level \(=0.95\).

The README states explicitly that the depolarizing/codespace-mixing term is intentional because pure \(T_1/T_2\) evolution preserves the low-index embedding and therefore cannot generate leakage for \(d<2^n\) in this model.

### C. Aer Circuit Lane

The Aer fixed-\(n\) sweep uses the same long delay grid as Eq. (24), plus the following settings:

- shots \(=8192\),
- correction mode `dynamic`,
- one-qubit depolarizing rate \(p_{1q}=0.001\),
- two-qubit depolarizing rate \(p_{2q}=0.01\),
- bootstrap samples \(=200\),
- confidence level \(=0.95\),
- seed base \(=17\).

The short-grid cross-check for the hardware-matched qutrit process comparison uses delays \(\{0,64,128\}\ \mathrm{dt}\) with \(4.0\ \mathrm{ns}/\mathrm{dt}\), \(8192\) shots, and \(200\) bootstrap samples, producing the monotone Aer process-fidelity sequence \(0.912783 \rightarrow 0.907736 \rightarrow 0.903990\) [Table 7].

### D. IBM Hardware Lane

The live backend is `ibm_fez`. IBM Quantum documentation identifies this backend as a 156-qubit Heron r2 processor [22], [23]. The processor-type documentation reports support for the native operations

`cz, id, delay, measure, reset, rz, sx, x, if_else, for_loop, switch_case`

for the Heron family [24]. These capabilities are necessary for the dynamic teleportation path and for explicit delay insertion.

The saved live experiments use:

- backend: `ibm_fez`,
- delays \(\Tau_{\mathrm{hw}} = \{0,64,128\}\ \mathrm{dt}\),
- inferred \(dt = 4.0\ \mathrm{ns}\) per backend cycle from the saved records,
- shots \(=256\),
- bootstrap samples \(=100\),
- confidence level \(=0.95\),
- correction mode `dynamic`.

The hardware delay grid therefore corresponds to \(0\), \(256\), and \(512\ \mathrm{ns}\). The saved artifacts do not archive a complete per-qubit calibration snapshot from the exact execution time, so this manuscript reports only the backend metadata preserved in the output records and the effective coherence-scale estimate extracted from the process-fidelity calibration artifact in Section VII-E.

### E. Reproducibility and Validation

The repository includes a `Makefile` with targets `theory`, `aer`, `hardware-live`, `hardware-process-live`, `three-lane-report`, `nonmarkovian`, and `test`. A final repository validation after cleanup reported:

- full test suite: `69 passed, 1 skipped`,
- CLI help resolved correctly from source,
- no residual cache directories remained in the repository tree.

The exact pinned package set is archived in `requirements-lock.txt`, and the package metadata is defined in `pyproject.toml`.

## VII. Results and Analysis

### A. High-Level Summary

Table 1 consolidates the lane structure and the dominant result.

**Table 1.** Fixed-\(n\) lane summary for the core \(n=2\) experiment.

| Lane | Delay grid | Primary observables | Principal finding |
| --- | --- | --- | --- |
| Theory baseline | \(0, 2048, 4096, 8192\) dt | \(F\), \(L\), \(F_{\mathrm{sub}}\) | Predicts monotone degradation but does not significantly separate \(d=3\) and \(d=4\) in state fidelity |
| Aer circuit lane | \(0, 2048, 4096, 8192\) dt | \(F\), \(L\), \(F_{\mathrm{sub}}\), \(F_{\mathrm{proc}}\), \(F_{\mathrm{avg}}\) | Separates \(d=4\) from \(d=3\) at every delay in both state and process metrics |
| IBM hardware lane | \(0, 64, 128\) dt | state tomography and process tomography | Confirms large channel penalty for \(d=4\); process fidelity separates \(d=4\) from \(d=3\) at all measured delays |

The most important empirical fact is that the fully occupied encoding \(d=4\), \(\phi=1\) has zero leakage but the *worst* process fidelity on both Aer and hardware. That observation immediately rules out leakage as the sole explanation for logical failure.

The repository also exports a merged three-lane significance summary. Table 2 reproduces the highest-level result from `artifacts/fixed_n2/three_lane_n2_compare.md`.

**Table 2.** Repository-wide three-lane significance summary for fixed \(n=2\).

| Lane | Delay grid | Metrics | \(d=4-d=3\) state-fidelity significance | \(d=4-d=3\) process-fidelity significance |
| --- | --- | --- | --- | --- |
| Theory baseline | \(0, 2048, 4096, 8192\) dt | \(F\), \(L\), \(F_{\mathrm{sub}}\) | \(0/4\) delays | — |
| Aer circuit lane | \(0, 2048, 4096, 8192\) dt | \(F\), \(L\), \(F_{\mathrm{sub}}\), \(F_{\mathrm{proc}}\), \(F_{\mathrm{avg}}\) | \(4/4\) delays | \(4/4\) delays |
| IBM hardware lane | \(0, 64, 128\) dt | \(F\), \(L\), \(F_{\mathrm{sub}}\), \(F_{\mathrm{proc}}\), \(F_{\mathrm{avg}}\) | \(2/3\) delays | \(3/3\) delays |

In the combined report, the hardware state-fidelity significance count is taken from the merged hardware-lane summary in `three_lane_n2_compare.md`; the standalone canonical-probe hardware state-tomography sweep is reported separately in Table 5.

### B. Theory-Baseline Results

The theory lane provides a controlled monotone baseline. For \(d=2\), fidelity decreases from \(1.000000\) at zero delay to \(0.960711\) at \(8192\) dt, while leakage rises from \(0.000000\) to \(0.014984\) [Table 3]. For \(d=3\), fidelity decreases from \(1.000000\) to \(0.955223\), with leakage increasing from \(0.000000\) to \(0.009769\) [Table 3]. For \(d=4\), fidelity decreases from \(1.000000\) to \(0.953138\), while leakage remains exactly zero by Lemma 1 [Table 3].

**Table 3.** Theory-lane raw state-fidelity and leakage values for fixed \(n=2\) [artifact: `artifacts/fixed_n2/n2_compare.md` and `artifacts/fixed_n2/markovian_n2.json`].

| delay (dt) | delay (ns) | \(F_{d=2}\) | \(L_{d=2}\) | \(F_{d=3}\) | \(L_{d=3}\) | \(F_{d=4}\) | \(L_{d=4}\) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 0.000 | 1.000000 | 0.000000 | 1.000000 | 0.000000 | 1.000000 | 0.000000 |
| 2048 | 455.111 | 0.989968 | 0.003778 | 0.988521 | 0.002504 | 0.987980 | 0.000000 |
| 4096 | 910.222 | 0.980077 | 0.007535 | 0.977234 | 0.004967 | 0.976166 | 0.000000 |
| 8192 | 1820.444 | 0.960711 | 0.014984 | 0.955223 | 0.009769 | 0.953138 | 0.000000 |

The important negative result is the \(d=4\) versus \(d=3\) comparison in state fidelity. The fixed-\(n\) theory report finds overlapping confidence intervals at all four delays:

- \(0\) dt: \(\Delta F_{4-3} \approx 0\), overlap,
- \(2048\) dt: \(\Delta F_{4-3} = -0.000541\), overlap,
- \(4096\) dt: \(\Delta F_{4-3} = -0.001068\), overlap,
- \(8192\) dt: \(\Delta F_{4-3} = -0.002085\), overlap.

Hence the effective embedded-state baseline does not support a claim that \(\phi=1\) is materially worse than \(\phi=0.75\) in state fidelity. This null result is not a failure; it establishes that the main experimental effect is absent in the simplified lane and therefore likely arises from circuit execution rather than from storage-like decoherence alone.

### C. Aer Circuit-Lane Results

The Aer lane is the primary local benchmark because it executes the actual teleportation circuit and its tomography stack. Table 4 summarizes the fixed-\(n\) comparison.

**Table 4.** Consolidated Aer fixed-\(n\) comparison for \(n=2\) [artifact: `artifacts/fixed_n2/aer_n2_compare.md`].

| delay (dt) | \(F_{d=2}\) | \(F_{d=3}\) | \(F_{d=4}\) | \(\Delta F_{4-3}\) | \(F_{\mathrm{proc},d=3}\) | \(F_{\mathrm{proc},d=4}\) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 0.950162 | 0.939667 | 0.933544 | -0.006122 | 0.912783 | 0.871542 |
| 2048 | 0.942209 | 0.932259 | 0.926476 | -0.005784 | 0.903888 | 0.861153 |
| 4096 | 0.932981 | 0.922176 | 0.916205 | -0.005971 | 0.894539 | 0.850405 |
| 8192 | 0.919745 | 0.905679 | 0.899341 | -0.006338 | 0.878116 | 0.829795 |

Every \(d=4-d=3\) state-fidelity comparison in Table 4 is statistically distinguishable in the saved report, and so is every process-fidelity comparison. The corresponding leakage values are also fully separated:

- \(d=2\): \(0.020064 \rightarrow 0.034036\),
- \(d=3\): \(0.013213 \rightarrow 0.021871\),
- \(d=4\): \(0\) identically.

Two conclusions follow.

First, partially filled codespaces do leak, and the lower-fill-ratio code \(d=2\) leaks more than \(d=3\) at every Aer delay. Second, the nonleaking full-space code \(d=4\) still suffers the worst logical channel, so the dominant penalty at \(\phi=1\) is not leakage but within-subspace distortion. This can be seen directly in the in-subspace fidelity, where \(d=4\) falls from \(0.933544\) at zero delay to \(0.899341\) at \(8192\) dt, always below \(d=3\) and \(d=2\) [Table 4].

The process metrics sharpen the conclusion. At zero delay, \(d=3\) achieves \(F_{\mathrm{proc}}=0.912783\) and \(F_{\mathrm{avg}}=0.934587\), while \(d=4\) reaches only \(0.871542\) and \(0.897234\) [artifact: `aer_n2_compare.md`]. By \(8192\) dt, the gap widens to \(0.878116\) versus \(0.829795\) in process fidelity and \(0.908587\) versus \(0.863836\) in average gate fidelity. The Aer lane therefore establishes a robust, monotone ordering

$$
d=2 \; > \; d=3 \; > \; d=4
\tag{25}
$$

in channel quality at fixed \(n=2\).

### D. Hardware State-Tomography Results

The live hardware state-tomography sweep averages over the canonical probe ensembles \(|\mathcal{P}_{\mathrm{can}}(d)|=d+1\). Table 5 reports the key values.

**Table 5.** Live fixed-\(n\) hardware state-tomography results on `ibm_fez` [artifact: `artifacts/hardware/ibm_fez_fixed_n2_delay0_64_128_compare.md`].

| delay (dt) | \(F_{d=2}\) | \(L_{d=2}\) | \(F_{d=3}\) | \(L_{d=3}\) | \(F_{d=4}\) | \(L_{d=4}\) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 0.886399 | 0.065773 | 0.869690 | 0.034730 | 0.868848 | 0.000000 |
| 64 | 0.836736 | 0.057680 | 0.828133 | 0.030717 | 0.834597 | 0.000000 |
| 128 | 0.822027 | 0.064111 | 0.809725 | 0.044195 | 0.852900 | 0.000000 |

At zero delay, every dimension exceeds the corresponding classical measure-and-prepare fidelity bound \(2/(d+1)\) [36], [37]:

- \(d=2\): bound \(= 2/3 \approx 0.6667\), observed \(0.8864\),
- \(d=3\): bound \(= 1/2 = 0.5000\), observed \(0.8697\),
- \(d=4\): bound \(= 2/5 = 0.4000\), observed \(0.8688\).

Thus the live hardware results are not only nontrivial; they are well within the nonclassical teleportation regime at zero delay.

However, the short hardware delay grid is visibly noisier than the Aer grid. The most obvious anomaly is the \(d=4\) state fidelity at \(128\) dt, which rises to \(0.852900\) after dropping to \(0.834597\) at \(64\) dt. The saved comparison report labels \(d=4-d=2\) as overlapping at \(128\) dt but \(d=4-d=3\) as statistically distinguishable. Because the delay grid is short and each circuit uses only \(256\) shots, this nonmonotonicity is best interpreted as a finite-sample fluctuation rather than as evidence of coherence recovery. It must therefore be reported, but it cannot support a physical claim by itself.

The more stable observation in Table 5 is leakage. Both partially filled codespaces show nonzero leakage at every hardware delay, while \(d=4\) remains identically zero for structural reasons. At zero delay, \(d=2\) leaks nearly twice as much as \(d=3\): \(0.065773\) versus \(0.034730\). This confirms that lower fill ratio correlates with a larger leakage opportunity on real hardware, even though leakage alone does not determine which logical channel is best.

### E. Hardware Process-Tomography Results

Channel-level comparison on hardware is the manuscript’s highest-value experimental result. Table 6 reports the live process-tomography metrics, reconstructed from \(d^2\) logical probe states per dimension.

**Table 6.** Live fixed-\(n\) hardware process-tomography results on `ibm_fez` [artifact: `artifacts/hardware/ibm_fez_process_fixed_n2_delay0_64_128_compare.md`].

| delay (dt) | \(F_{\mathrm{proc},d=2}\) | \(F_{\mathrm{proc},d=3}\) | \(F_{\mathrm{proc},d=4}\) | \(F_{\mathrm{avg},d=2}\) | \(F_{\mathrm{avg},d=3}\) | \(F_{\mathrm{avg},d=4}\) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 0.878970 | 0.742090 | 0.627743 | 0.919314 | 0.806567 | 0.702194 |
| 64 | 0.729112 | 0.666584 | 0.493899 | 0.819408 | 0.749938 | 0.595119 |
| 128 | 0.729815 | 0.692762 | 0.505262 | 0.819877 | 0.769571 | 0.604210 |

The channel ordering of Eq. (25) persists on live hardware and is much stronger than in state fidelity. In the saved comparison report:

- \(d=4-d=3\) process fidelity is statistically distinguishable at all three delays,
- \(d=4-d=2\) process fidelity is statistically distinguishable at all three delays,
- the corresponding average-gate-fidelity gaps are also statistically distinguishable at all three delays.

At zero delay, the hardware qutrit process fidelity \(0.742090\) exceeds the \(0.596 \pm 0.037\) qutrit process reported by Hu *et al.* for photonic high-dimensional teleportation [17], although the platforms, probe ensembles, and reconstruction details differ. Likewise, the zero-delay hardware qutrit state fidelity \(0.869690\) exceeds the qutrit teleportation fidelity \(0.75(1)\) reported by Luo *et al.* [16]. These comparisons must be interpreted cautiously because they are not like-for-like experiments, but they place the present result at a credible scale relative to prior high-dimensional teleportation benchmarks.

The slight increase in \(d=3\) and \(d=4\) process fidelity from \(64\) to \(128\) dt is a real artifact in the saved data and must be addressed explicitly. For \(d=3\), the increase is \(0.666584 \rightarrow 0.692762\); for \(d=4\), it is \(0.493899 \rightarrow 0.505262\). In both cases the confidence intervals overlap substantially, and the run used only \(256\) shots per tomographic circuit. This is therefore an unresolved finite-shot effect rather than evidence against decoherence. The correct scientific stance is that the hardware process-fidelity decay is strongly downward from \(0\) to \(64\) dt, while the \(64\)-to-\(128\) increment is statistically inconclusive.

### F. Aer–Hardware Qutrit Process Cross-Check

The repository includes a dedicated qutrit cross-check between hardware and a hardware-matched Aer rerun on the short delay grid \(0,64,128\) dt. The saved Markdown artifact reports monotone Aer process fidelity

$$
0.912783 \rightarrow 0.907736 \rightarrow 0.903990,
\tag{26}
$$

while hardware gives

$$
0.742090 \rightarrow 0.666584 \rightarrow 0.692762.
\tag{27}
$$

**Table 7.** Hardware-versus-Aer qutrit process cross-check on the matched short delay grid [artifact: `artifacts/hardware/ibm_fez_vs_aer_process_d3_n2_compare.md`].

| delay (dt) | delay (ns) | Hardware \(F_{\mathrm{proc}}\) | Aer \(F_{\mathrm{proc}}\) | delta | CI relation |
| ---: | ---: | ---: | ---: | ---: | --- |
| 0 | 0.000 | 0.742090 | 0.912783 | -0.170693 | separated |
| 64 | 256.000 | 0.666584 | 0.907736 | -0.241153 | separated |
| 128 | 512.000 | 0.692762 | 0.903990 | -0.211228 | separated |

At every delay, the Aer and hardware confidence intervals are separated for both process fidelity and average gate fidelity [Table 7]. This result is informative in two ways.

First, it confirms that the earlier nonmonotonic short-delay Aer artifact was statistical rather than structural: after increasing the shot budget to \(8192\) and the bootstrap count to \(200\), the Aer qutrit process decay becomes monotone. Second, it quantifies the hardware penalty relative to a circuit-faithful noisy simulator: hardware is worse by \(-0.170693\), \(-0.241153\), and \(-0.211228\) in qutrit process fidelity at \(0\), \(64\), and \(128\) dt, respectively [Table 7].

### G. Non-Markovian Calibration and BLP Scan

The non-Markovian lane is deliberately secondary in this manuscript, but the repository now contains two nontrivial artifacts: a random-telegraph BLP sweep and a backend-anchored calibration. The BLP scan shows a monotone decrease of the BLP measure with increasing switching probability for every tested dimension [artifact: `random_telegraph_blp_n2.md`]. For example:

- \(d=2\): \(1.787267 \rightarrow 0.074441\) as \(p_{\mathrm{switch}}\) increases from \(0.005\) to \(0.2\),
- \(d=3\): \(1.735645 \rightarrow 0.036728\),
- \(d=4\): \(1.754433 \rightarrow 0.038524\).

This confirms that the implemented BLP pipeline is sensitive to the intended memory parameter. However, the ordering across \(d\) is weak and not monotone in dimension, so the current scan does **not** support a strong claim that higher fill ratio produces stronger non-Markovianity.

The calibration artifact uses hardware qutrit process-fidelity decay to fit an effective coherence timescale:

$$
T_{2,\mathrm{eff}} = 2008.584\ \mathrm{ns}
\quad
[1089.623,\ 15373.067]\ \mathrm{ns},
\tag{28}
$$

then identifies the random-telegraph correlation time with this estimate,

$$
\tau_{\mathrm{corr}} := T_{2,\mathrm{eff}},
\tag{29}
$$

yielding the stepwise switching probability

$$
p_{\mathrm{switch}}
=
1 - e^{-\Delta t/\tau_{\mathrm{corr}}}
=
0.001989
\quad
[0.000260,\ 0.003664]
\tag{30}
$$

for \(\Delta t = 4\ \mathrm{ns}\) [artifact: `ibm_fez_rtn_calibration_d3_n2.json`]. This calibration is still phenomenological, but it is no longer an arbitrary hand-tuned parameter choice.

## VIII. Discussion

### A. What the Results Actually Show

The manuscript’s principal scientific result is straightforward:

1. The full-space encoding \(d=4\), \(n=2\) eliminates leakage by construction.
2. Despite that, \(d=4\) is the *worst* channel in the Aer lane and in the hardware process-tomography lane.
3. Therefore, under fixed physical resource count, the dominant penalty at \(\phi=1\) is not leakage but logical distortion inside the occupied subspace.

This is precisely why both leakage and in-subspace fidelity are required. If one reported only leakage, \(d=4\) would appear ideal. If one reported only state fidelity, the interpretation would be incomplete. The combined observable set reveals that leakage and within-subspace damage are distinct failure modes and can move in opposite directions as \(d\) changes.

### B. Why the Theory Lane Misses the Main Effect

The effective Markovian lane does not significantly separate \(d=3\) and \(d=4\) in state fidelity. This is expected in hindsight. The theory lane applies Kraus noise directly to the embedded output block through `markovian_delay_density()`, bypassing Bell-pair generation, measurement backaction, classical feed-forward latency, transpilation overhead, and readout corruption. Moreover, its leakage is introduced only by an explicit depolarizing term. Consequently, the theory lane is best understood as a storage-noise baseline and not as a physically faithful teleportation model.

This is not a defect of the repository once it is described honestly. It simply means that the theoretical lane cannot carry the paper’s main empirical claim by itself. The heavy evidentiary burden therefore falls on the Aer and hardware lanes, where the full circuit is actually run.

### C. Comparison against Classical and Quantum Benchmarks

Against the classical measure-and-prepare baseline \(2/(d+1)\), the zero-delay hardware state-fidelity results are decisively nonclassical for every tested dimension [36], [37]. Against prior high-dimensional teleportation experiments, the present hardware qutrit process fidelity is competitive and, on its face, stronger than the six-photon qutrit process result reported in Ref. [17]. The Aer qutrit channel is stronger still. These cross-platform comparisons should not be overinterpreted because the platforms, encodings, and tomographic conventions differ, but they demonstrate that the reported values are not marginal or purely simulation artifacts.

### D. Negative Results and Null Findings

Several null or weak findings are scientifically important.

- The theory baseline does not separate \(d=3\) and \(d=4\) in state fidelity.
- The non-Markovian BLP sweep shows monotone dependence on the memory parameter but does not show a strong monotone dependence on \(d\) or \(\phi\).
- The short-grid hardware process decay is not strictly monotone between \(64\) and \(128\) dt at the current shot budget.

These findings reduce, rather than increase, the scope of the manuscript’s claims. The defensible thesis is therefore not “higher fill ratio always improves or worsens teleportation” in an abstract sense. The defensible thesis is narrower and stronger: *for this encoded teleportation workflow at fixed \(n=2\), circuit-faithful simulation and hardware both show that the full-space encoding \(d=4\) underperforms the partially filled qutrit encoding \(d=3\) at the channel level, even though the full-space encoding has zero leakage by definition.*

### E. Limitations

The work has five principal limitations.

1. **Backend coverage.** All live results are on a single backend, `ibm_fez`, although that backend is a modern Heron r2 system [22]–[24].
2. **Shot budget.** The hardware lane uses only \(256\) shots per circuit, which is adequate for a first channel-level comparison but not for high-confidence monotonic decay inference over short delays.
3. **Delay range mismatch.** The long Aer grid extends to \(8192\) dt while the hardware grid stops at \(128\) dt. This is a pragmatic limitation of live queue and shot cost rather than a conceptual limitation.
4. **Monolithic implementation.** The software is still carried in a single package file, which is acceptable for auditability but suboptimal for thesis readability.
5. **Phenomenological non-Markovian model.** The random-telegraph lane is now backend-anchored, but it is still not a microscopic spectral-density fit.

None of these limitations invalidate the central fixed-\(n\) result, but each constrains how far the present manuscript can generalize beyond the measured setting.

## IX. Future Work

The most important next steps are concrete and technically justified.

### A. Increase Hardware Shot Count and Delay Range

The hardware process-tomography lane should be rerun with larger shot budgets and a longer delay grid, for example \(\{0,64,128,256,512\}\) dt or beyond. This would distinguish genuine short-delay plateaus from shot-noise fluctuations and enable a more stable fit of effective coherence parameters.

### B. Archive Backend Calibration Snapshots

The current artifacts preserve `dt_ns`, backend name, and reconstructed metrics, but not the full backend calibration record at execution time. A stronger publication version should archive qubit-wise \(T_1\), \(T_2\), readout error, and gate-error summaries for the selected qubits. This would strengthen hardware-methodology reproducibility and support more targeted error-budget analysis.

### C. Extend Deferred-Correction Hardware Comparisons

The software stack already supports deferred correction. Running matched hardware sweeps with both dynamic and deferred correction would directly test whether the observed penalty is dominated by feed-forward execution or by logical post-processing and state reconstruction.

### D. Broaden Fixed-\(n\) Beyond \(n=2\)

The next natural experiment is \(n=3\), which allows \(d \in \{2,\ldots,8\}\). That setting would test whether the observed penalty at \(\phi=1\) is specific to the \(n=2\) geometry or persists as the code space and leakage subspace both expand.

### E. Replace the Baseline Theory Lane with a Circuit-Level Effective Model

A more faithful baseline would inject noise at the circuit level while still remaining analytically lighter than full Aer. For example, one could construct a simplified Pauli-transfer or Lindblad model acting on the compiled teleportation circuit rather than on the embedded density matrix alone.

### F. Extract the Monolith

For long-term maintainability and thesis readability, the code should be split into the already planned modules `config.py`, `encoding.py`, `states.py`, `metrics.py`, `process.py`, `statistics.py`, `simulation.py`, `tomography.py`, `circuits.py`, `hardware.py`, `aer.py`, `reports.py`, `sweeps.py`, and `cli.py`.

## X. Conclusion

This work studies logical teleportation in a fixed-physical-qubit regime and shows that the fill ratio \(\phi=d/2^n\) is a useful organizing variable for disentangling leakage from within-subspace logical distortion. The fixed-\(n=2\) comparison demonstrates that the full-space encoding \(d=4\) has structurally zero leakage, yet nevertheless yields the worst process fidelity and average gate fidelity on both a circuit-faithful noisy simulator and live IBM hardware. The partially filled qutrit encoding \(d=3\) outperforms \(d=4\) at the channel level across all tested Aer delays and across all tested hardware process-tomography delays. Therefore, the principal logical penalty at \(\phi=1\) is not codespace escape but degradation of the channel acting *within* the occupied subspace.

The paper also establishes a methodological point. A theory lane that bypasses circuit execution can provide a useful baseline, but it cannot substitute for circuit-faithful simulation or hardware measurements when the scientific question is ultimately about compiled teleportation circuits under real noise. The Aer and hardware lanes carry the decisive evidence, and their agreement on the \(d=4\) penalty is the strongest result of the study.

In that sense, the fixed-\(n\) framing succeeds: it turns what might otherwise be a vague statement about “dimension” into a precise and falsifiable statement about leakage geometry, channel quality, and delay-dependent degradation on actual quantum software and hardware.

## References

[1] C. H. Bennett, G. Brassard, C. Crépeau, R. Jozsa, A. Peres, and W. K. Wootters, “Teleporting an unknown quantum state via dual classical and Einstein-Podolsky-Rosen channels,” *Phys. Rev. Lett.*, vol. 70, pp. 1895–1899, 1993, doi: 10.1103/PhysRevLett.70.1895.

[2] M. A. Nielsen and I. L. Chuang, *Quantum Computation and Quantum Information*, 10th anniversary ed. Cambridge, U.K.: Cambridge Univ. Press, 2010.

[3] J. Preskill, “Quantum computing in the NISQ era and beyond,” *Quantum*, vol. 2, p. 79, 2018, doi: 10.22331/q-2018-08-06-79.

[4] M. Horodecki, P. Horodecki, and R. Horodecki, “General teleportation channel, singlet fraction, and quasidistillation,” *Phys. Rev. A*, vol. 60, pp. 1888–1898, 1999, doi: 10.1103/PhysRevA.60.1888.

[5] A. Jamiołkowski, “Linear transformations which preserve trace and positive semidefiniteness of operators,” *Rep. Math. Phys.*, vol. 3, no. 4, pp. 275–278, 1972, doi: 10.1016/0034-4877(72)90011-0.

[6] M.-D. Choi, “Completely positive linear maps on complex matrices,” *Linear Algebra Appl.*, vol. 10, no. 3, pp. 285–290, 1975, doi: 10.1016/0024-3795(75)90075-0.

[7] M. A. Nielsen, “A simple formula for the average gate fidelity of a quantum dynamical operation,” *Phys. Lett. A*, vol. 303, no. 4, pp. 249–252, 2002, doi: 10.1016/S0375-9601(02)01272-0.

[8] J. L. O’Brien, G. J. Pryde, A. Gilchrist, D. F. V. James, N. K. Langford, T. C. Ralph, and A. G. White, “Quantum process tomography of a controlled-NOT gate,” *Phys. Rev. Lett.*, vol. 93, p. 080502, 2004, doi: 10.1103/PhysRevLett.93.080502.

[9] H.-P. Breuer, E.-M. Laine, and J. Piilo, “Measure for the degree of non-Markovian behavior of quantum processes in open systems,” *Phys. Rev. Lett.*, vol. 103, p. 210401, 2009, doi: 10.1103/PhysRevLett.103.210401.

[10] H.-P. Breuer, E.-M. Laine, J. Piilo, and B. Vacchini, “Colloquium: Non-Markovian dynamics in open quantum systems,” *Rev. Mod. Phys.*, vol. 88, p. 021002, 2016, doi: 10.1103/RevModPhys.88.021002.

[11] I. de Vega and D. Alonso, “Dynamics of non-Markovian open quantum systems,” *Rev. Mod. Phys.*, vol. 89, p. 015001, 2017, doi: 10.1103/RevModPhys.89.015001.

[12] B. Efron and R. J. Tibshirani, *An Introduction to the Bootstrap*. New York, NY, USA: Chapman and Hall, 1993.

[13] G. B. Silva, S. Glancy, and H. M. Vasconcelos, “Investigating bias in maximum-likelihood quantum-state tomography,” *Phys. Rev. A*, vol. 95, p. 022107, 2017, doi: 10.1103/PhysRevA.95.022107.

[14] X.-M. Hu, Y. Guo, B.-H. Liu, C.-F. Li, and G.-C. Guo, “Progress in quantum teleportation,” *Nat. Rev. Phys.*, vol. 5, pp. 339–353, 2023, doi: 10.1038/s42254-023-00588-x.

[15] S. K. Goyal, P. Boukama-Dzoussi, S. Ghosh, F. S. Roux, and T. Konrad, “Qudit-Teleportation for photons with linear optics,” *Sci. Rep.*, vol. 4, p. 4543, 2014, doi: 10.1038/srep04543.

[16] Y.-H. Luo *et al.*, “Quantum teleportation in high dimensions,” *Phys. Rev. Lett.*, vol. 123, p. 070505, 2019, doi: 10.1103/PhysRevLett.123.070505.

[17] X.-M. Hu *et al.*, “Experimental high-dimensional quantum teleportation,” *Phys. Rev. Lett.*, vol. 125, p. 230501, 2020, doi: 10.1103/PhysRevLett.125.230501.

[18] M. Erhard, M. Krenn, and A. Zeilinger, “Advances in high-dimensional quantum entanglement,” *Nat. Rev. Phys.*, vol. 2, pp. 365–381, 2020, doi: 10.1038/s42254-020-0193-5.

[19] I. Fernández de Fuentes *et al.*, “Navigating the 16-dimensional Hilbert space of a high-spin donor qudit with electric and magnetic fields,” *Nat. Commun.*, vol. 15, p. 1380, 2024, doi: 10.1038/s41467-024-45368-y.

[20] L. B. Nguyen *et al.*, “Empowering a qudit-based quantum processor by traversing the dual bosonic ladder,” *Nat. Commun.*, vol. 15, p. 7117, 2024, doi: 10.1038/s41467-024-51434-2.

[21] Y. Kim *et al.*, “Evidence for the utility of quantum computing before fault tolerance,” *Nature*, 2023. IBM Research publication page: https://research.ibm.com/publications/evidence-for-the-utility-of-quantum-computing-before-fault-tolerance

[22] IBM Quantum Documentation, “View backend details,” IBM Quantum Platform, accessed Apr. 21, 2026. [Online]. Available: https://quantum.cloud.ibm.com/docs/en/guides/qpu-information

[23] IBM Quantum Documentation, “Get backend information with Qiskit,” IBM Quantum Platform, accessed Apr. 21, 2026. [Online]. Available: https://quantum.cloud.ibm.com/docs/en/guides/get-qpu-information

[24] IBM Quantum Documentation, “Processor types,” IBM Quantum Platform, accessed Apr. 21, 2026. [Online]. Available: https://quantum.cloud.ibm.com/docs/en/guides/processor-types

[25] B. Johnson, “Qiskit runtime, a quantum-classical execution platform for cloud-accessible quantum computers,” *APS March Meeting 2022*, Mar. 2022. [Online]. Available: https://research.ibm.com/publications/qiskit-runtime-a-quantum-classical-execution-platform-for-cloud-accessible-quantum-computers

[26] T. Mittal, S. Thoß, and R. Mandelbaum, “Qiskit Runtime: A Cloud-Native, Pay-As-You-Go Service for Quantum Computing,” IBM Think, 2022. [Online]. Available: https://www.ibm.com/think/insights/how-to-make-quantum-a-pay-as-you-go-cloud-service

[27] A. D. Córcoles, M. Takita, K. Inoue, S. Lekuch, Z. K. Minev, J. M. Chow, and J. M. Gambetta, “Exploiting dynamic quantum circuits in a quantum algorithm with superconducting qubits,” *Phys. Rev. Lett.*, 2021. IBM Research publication page: https://research.ibm.com/publications/exploiting-dynamic-quantum-circuits-in-a-quantum-algorithm-with-superconducting-qubits

[28] E. Bäumer, V. Tripathi, A. Seif, D. Lidar, and D. S. Wang, “Quantum Fourier Transform Using Dynamic Circuits,” *Phys. Rev. Lett.*, 2024. IBM Research publication page: https://research.ibm.com/publications/quantum-fourier-transform-using-dynamic-circuits

[29] E. Bäumer *et al.*, “Efficient Long-Range Entanglement Using Dynamic Circuits,” *PRX Quantum*, 2024. IBM Research publication page: https://research.ibm.com/publications/efficient-long-range-entanglement-using-dynamic-circuits--2

[30] A. Carrera Vazquez *et al.*, “Combining quantum processors with real-time classical communication,” *Nature*, 2024. IBM Research publication page: https://research.ibm.com/publications/combining-quantum-processors-with-real-time-classical-communication

[31] C. Tornow, N. Kanazawa, W. E. Shanks, and D. J. Egger, “Minimum quantum run-time characterization and calibration via restless measurements with dynamic repetition rates,” 2024. [Online]. Available: https://arxiv.org/abs/2202.06981

[32] D. Gottesman and I. L. Chuang, “Demonstrating the viability of universal quantum computation using teleportation and single-qubit operations,” *Nature*, vol. 402, pp. 390–393, 1999.

[33] Qiskit Contributors, “Qiskit,” GitHub repository, version 2.3.0 used in this work, accessed Apr. 21, 2026. [Online]. Available: https://github.com/Qiskit/qiskit

[34] Qiskit Contributors, “Qiskit Aer,” GitHub repository, version 0.17.2 used in this work, accessed Apr. 21, 2026. [Online]. Available: https://github.com/Qiskit/qiskit-aer

[35] Qiskit Contributors, “qiskit-ibm-runtime,” GitHub repository, version 0.46.1 used in this work, accessed Apr. 21, 2026. [Online]. Available: https://github.com/Qiskit/qiskit-ibm-runtime

[36] S. Massar and S. Popescu, “Optimal extraction of information from finite quantum ensembles,” *Phys. Rev. Lett.*, vol. 74, p. 1259, 1995, doi: 10.1103/PhysRevLett.74.1259.

[37] D. Bruß and C. Macchiavello, “Optimal state estimation for d-dimensional quantum systems,” *Phys. Lett. A*, vol. 253, no. 5–6, pp. 249–251, 1999, doi: 10.1016/S0375-9601(99)00099-7.

[38] F. Yan, P. Krantz, Y. Sung, M. Kjaergaard, D. L. Campbell, T. P. Orlando, S. Gustavsson, and W. D. Oliver, “Tunable coupling scheme for implementing high-fidelity two-qubit gates,” *Phys. Rev. Applied*, vol. 10, p. 054062, 2018, doi: 10.1103/PhysRevApplied.10.054062.

## Appendix A. Notation

**Table A1.** Principal symbols.

| Symbol | Meaning |
| --- | --- |
| \(n\) | number of physical qubits in one logical block |
| \(d\) | logical Hilbert-space dimension |
| \(\phi=d/2^n\) | fill ratio of the physical Hilbert space |
| \(\mathcal{H}_{\mathrm{phys}}\) | physical Hilbert space \((\mathbb{C}^2)^{\otimes n}\) |
| \(\mathcal{H}_{d}\) | logical Hilbert space \(\mathbb{C}^d\) |
| \(P_{\mathrm{code}}\) | projector onto the embedded logical subspace |
| \(P_{\mathrm{leak}}\) | projector onto the complement of the logical subspace |
| \(F\) | embedded-state fidelity |
| \(L\) | leakage probability |
| \(F_{\mathrm{sub}}\) | in-subspace fidelity after logical renormalization |
| \(F_{\mathrm{proc}}\) | process fidelity of the reconstructed logical channel |
| \(F_{\mathrm{avg}}\) | average gate fidelity |
| \(\tau\) | delay parameter in backend `dt` units unless otherwise stated |
| \(\tau_{\mathrm{corr}}\) | correlation time of the random-telegraph model |

## Appendix B. Reproduction Commands

The repository contains the following reproduction entry points.

```bash
make theory
make aer
make hardware-live
make hardware-process-live
make three-lane-report
make nonmarkovian
make test
```

Equivalent direct CLI examples include:

```bash
teleportdim hardware-fixed-n-sweep \
  --n-values 2 \
  --backend-name ibm_fez \
  --shots 256 \
  --delays 0,64,128 \
  --bootstrap-samples 100 \
  --output-stem artifacts/hardware/ibm_fez_fixed_n2_delay0_64_128_live

teleportdim hardware-process-tomography \
  --dimension 3 \
  --n-physical 2 \
  --backend-name ibm_fez \
  --shots 256 \
  --delays 0,64,128 \
  --bootstrap-samples 100 \
  --confidence-level 0.95 \
  --output-stem artifacts/hardware/ibm_fez_process_d3_n2_delay0_64_128
```

## Appendix C. Environment Archive

The package metadata is stored in `pyproject.toml`. The exact environment used for the validated repository pass is archived in `requirements-lock.txt`. The principal versions are:

| Package | Version |
| --- | --- |
| Python | 3.13 (validated runtime) |
| qiskit | 2.3.0 |
| qiskit-aer | 0.17.2 |
| qiskit-ibm-runtime | 0.46.1 |
| numpy | 2.3.5 |
| matplotlib | 3.10.6 |
| pytest | 8.4.2 |

## Appendix D. Raw Comparison Tables

**Table D1.** Theory-lane fixed-\(n=2\) state-fidelity comparison.

| delay (dt) | \(F_{d=2}\) | \(F_{d=3}\) | \(F_{d=4}\) | significance \(d4-d3\) |
| ---: | ---: | ---: | ---: | --- |
| 0 | 1.000000 | 1.000000 | 1.000000 | overlap |
| 2048 | 0.989968 | 0.988521 | 0.987980 | overlap |
| 4096 | 0.980077 | 0.977234 | 0.976166 | overlap |
| 8192 | 0.960711 | 0.955223 | 0.953138 | overlap |

**Table D2.** Aer-lane fixed-\(n=2\) leakage comparison.

| delay (dt) | \(L_{d=2}\) | \(L_{d=3}\) | \(L_{d=4}\) |
| ---: | ---: | ---: | ---: |
| 0 | 0.020064 | 0.013213 | 0.000000 |
| 2048 | 0.023450 | 0.015011 | 0.000000 |
| 4096 | 0.027432 | 0.017244 | 0.000000 |
| 8192 | 0.034036 | 0.021871 | 0.000000 |

**Table D3.** Hardware qutrit Aer-vs-live process cross-check.

| delay (dt) | Hardware \(F_{\mathrm{proc}}\) | Aer \(F_{\mathrm{proc}}\) | delta |
| ---: | ---: | ---: | ---: |
| 0 | 0.742090 | 0.912783 | -0.170693 |
| 64 | 0.666584 | 0.907736 | -0.241153 |
| 128 | 0.692762 | 0.903990 | -0.211228 |

## Appendix E. Complete Source Pointer

The complete monolithic implementation used in this work is archived in:

- `src/teleportdim/__init__.py`

and the principal saved result artifacts cited in the manuscript are:

- `artifacts/fixed_n2/n2_compare.{json,csv,md}`
- `artifacts/fixed_n2/aer_n2_compare.{json,csv,md}`
- `artifacts/fixed_n2/three_lane_n2_compare.{json,csv,md}`
- `artifacts/hardware/ibm_fez_fixed_n2_delay0_64_128_compare.{json,csv,md}`
- `artifacts/hardware/ibm_fez_process_fixed_n2_delay0_64_128_compare.{json,csv,md}`
- `artifacts/hardware/ibm_fez_vs_aer_process_d3_n2_compare.{json,md}`
- `artifacts/non_markovian/random_telegraph_blp_n2.{json,csv,md}`
- `artifacts/non_markovian/ibm_fez_rtn_calibration_d3_n2.{json,md}`
