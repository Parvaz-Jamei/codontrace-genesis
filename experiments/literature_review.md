# Literature Review and Theoretical Foundations for CodonTrace Genesis Long Board Experiments (T01–T12)

**Design Date**: October 2026  
**Reference Document**: `Genesis_Long_Board_Experiments_FA.md`  
**Execution Target**: Orange Pi Zero 3 (Allwinner H618 Quad Cortex-A53, 2GB RAM, Linux arm64)  
**Repository**: `https://github.com/Parvaz-Jamei/codontrace-genesis`

---

## 1. Executive Summary & Epistemic Boundaries

This literature review establishes the formal theoretical, mathematical, and algorithmic foundations for the 12 scientific experiments (T01–T12) defined in `Genesis_Long_Board_Experiments_FA.md`.

### Core Epistemic Invariants:
1. `red_queen_proved = False`: No claims of proven Red Queen dynamics or open-ended intelligence are fabricated; negative or null results are valid scientific outcomes.
2. `major_transition_proved = False`: Damage reduction is strictly distinguished from mutual benefit and higher-level evolutionary individuality.
3. **Strict Separation of Tracks**:
   - `REFERENCE`: Standalone mathematical models validating metrics and theoretical bounds.
   - `ENGINE`: Full virtual machine execution with codon dispatch, organism state, energy accounting, and real reproduction.
   - `INTEGRATED`: Bidirectional causal loops coupling engine execution, ledger mechanisms, and adaptive behaviors.

---

## 2. Foundations by Experiment (T01–T12)

### T01: Open-Ended Evolution (OEE) & Functional Novelty
- **Foundational Works**:
  - Dolson, E. L., Vostinar, A. E., Wiser, M. J., & Ofria, C. (2019). *The MODES Toolbox: Measurements of Open-Ended Dynamics in Evolving Systems*. Artificial Life, 25(1), 50–73. DOI: `10.1162/artl_a_00282`.
  - Bedau, M. A., Snyder, E., & Packard, N. H. (1998). *A Classification of Long-Term Evolutionary Dynamics*. Artificial Life VI, 228–237.
  - de Pinho, B., & Sinapayen, L. (2026). *A speciation simulation that partly passes open-endedness tests*. arXiv: `2603.01701`.
  - Hedayatian, S., & Nikolaidis, S. (2026). *AutoQD: Automatic Discovery of Diverse Behaviors with Quality-Diversity Optimization*. arXiv: `2506.05634v2` (ICLR 2026).
- **Mathematical / Formal Definition**:
  - Component activity $A_i(t) = \sum_{\tau=0}^t a_i(\tau)$ where $a_i(\tau) = 1$ if component $i$ is present and actively selected at time $\tau$.
  - Normalized cumulative activity $\bar{A}_{\text{norm}}(t)$ evaluated against a neutral shadow run (null model).
  - Novelty metric: Functional phenotype discovery on held-out tasks $\mathcal{T}_{\text{held-out}}$, ensuring recurrence of old genotypes is not counted as evolutionary innovation.
- **Flaws Remediated from Legacy Reference**:
  - `_match_count` is now directly coupled to organism survival and reproductive fitness.
  - RNG mutation event ($p_{\text{mut}}$) and mutation locus selection are decoupled, ensuring uniform probability across all loci.
  - Zero-control synthetic loops verify that pure neutral drift or cyclic recurrence produces $\Delta A_{\text{novel}} = 0$.

---

### T02: Multilevel Selection (MLS) & Real Price Equation Accounting
- **Foundational Works**:
  - Price, G. R. (1970). *Selection and covariance*. Nature, 227(5257), 520–521. DOI: `10.1038/227520a0`.
  - Price, G. R. (1972). *Extension of covariance selection mathematics*. Annals of Human Genetics, 35(4), 485–490. DOI: `10.1111/j.1469-1809.1972.tb00608.x`.
  - Okasha, S. (2006). *Evolution and the Levels of Selection*. Oxford University Press. DOI: `10.1093/acprof:oso/9780199267972.001.0001`.
  - Gardner, A. (2015). *The Price equation*. Current Biology, 25(17), R729–R732. DOI: `10.1016/j.cub.2015.07.005`.
- **Mathematical / Formal Definition**:
  - Full Price equation across discrete generations:
    $$\Delta \bar{z} = \frac{\text{Cov}(w_i, z_i)}{\bar{w}} + \frac{\mathbb{E}[w_i(z'_i - z_i)]}{\bar{w}}$$
    where $w_i$ is realized offspring count of individual $i$, $z_i$ is parental trait, and $z'_i$ is the mean trait of the offspring of parent $i$.
  - Multilevel Price decomposition into between-group and within-group terms:
    $$\Delta \bar{z} = \frac{\text{Cov}(W_k, Z_k)}{\bar{W}} + \mathbb{E}\left[\frac{\text{Cov}(w_{ik}, z_{ik})}{\bar{w}_k}\right] + \text{transmission bias}$$
- **Flaws Remediated from Legacy Reference**:
  - Eliminates synthetic algebraic formula assignment; $w_i$ is recorded strictly from realized births.
  - Discrete lineage and deme RNG streams are isolated to prevent cross-deme deterministic entanglement.
  - Mathematical identity verified with residual $|\text{observed} - \text{predicted}| < 10^{-7}$.

---

### T03: Evolutionary Transitions in Individuality & Mutualism Assays
- **Foundational Works**:
  - Maynard Smith, J., & Szathmáry, E. (1995). *The Major Transitions in Evolution*. Oxford University Press.
  - Ratcliff, W. C., Denison, R. F., Borrello, M., & Travisano, M. (2012). *Experimental evolution of multicellularity*. PNAS, 109(5), 1595–1600. DOI: `10.1073/pnas.1115323109`.
  - West, S. A., Fisher, R. M., Gardner, A., & Kiers, E. T. (2015). *Major evolutionary transitions in individuality*. PNAS, 112(33), 10112–10119. DOI: `10.1073/pnas.1421402112`.
  - Michod, R. E. (2007). *Evolution of individuality during the transition from unicellular to multicellular life*. PNAS, 104(suppl_1), 8613–8618. DOI: `10.1073/pnas.0701489104`.
- **Mathematical / Formal Definition**:
  - Mutualism assays testing partner interaction across 4 standardized regimes:
    1. With native co-evolved partner ($\Pi_{\text{native}}$).
    2. Partner removal ($\Pi_{\text{removed}}$).
    3. Non-cooperative partner control ($\Pi_{\text{cheater}}$).
    4. Scrambled partner control ($\Pi_{\text{scrambled}}$).
  - Mutual benefit defined strictly as $\Pi_{\text{native}} > \Pi_{\text{removed}}$ for BOTH host and symbiont simultaneously, exceeding unassociated baseline $\Pi_{\text{baseline}}$.
- **Flaws Remediated from Legacy Reference**:
  - Eliminated the artifactual slope inversion at $v = 0.484848$ from $w_p = 1.2(1-v)u + 1.5v(1-0.85u)$.
  - Damage reduction is not conflated with positive mutualism.
  - Vertical transmission screening rates ($v \in \{0.0, 0.25, 0.5, 0.75, 1.0\}$) are pre-registered and locked.

---

### T04: Historical Contingency & Replay Experiments
- **Foundational Works**:
  - Gould, S. J. (1989). *Wonderful Life: The Burgess Shale and the Nature of History*. W. W. Norton & Company.
  - Blount, Z. D., Borland, C. Z., & Lenski, R. E. (2008). *Historical contingency and the evolution of a key innovation in an experimental population of Escherichia coli*. PNAS, 105(23), 7899–7906. DOI: `10.1073/pnas.0803151105`.
  - Travisano, M., Mongold, J. A., Bennett, A. F., & Lenski, R. E. (1995). *Experimental tests of the roles of adaptation, chance, and history in evolution*. Science, 267(5194), 87–90. DOI: `10.1126/science.7809610`.
- **Mathematical / Formal Definition**:
  - 12 independent historical founders evolved to generation $T \in \{0, 500, 1000\}$.
  - At each checkpoint, 8 replay forks launched with independent subsequent stochastic streams under identical future environmental challenges.
  - Deterministic replay invariant: Identical checkpoint state + identical seed yields 100% bitwise identical trajectory.
- **Flaws Remediated from Legacy Reference**:
  - Replaced $r < 0.18 \implies \text{int}(r \times 32)$ mutation bias (which only mutated bits 0–5) with uniform 32-bit PRNG sampling.
  - Real functional selection on held-out tasks replaces passive genetic drift.

---

### T05: Red Queen Dynamics & Time-Shift Assay Matrix
- **Foundational Works**:
  - Van Valen, L. (1973). *A new evolutionary law*. Evolutionary Theory, 1, 1–30.
  - Morran, K. E., Schmidt, O. G., Gelarden, I. A., Parrish, R. C., & Lively, C. M. (2011). *Running with the Red Queen: Host-Parasite Coevolution Selects for Biparental Sex*. Science, 333(6039), 216–218. DOI: `10.1126/science.1206360`.
  - Betts, A., Kaltz, O., & Hochberg, M. E. (2018). *High Parasite Diversity Accelerates Host Adaptation and Diversification*. Science, 360(6391), 907–911. DOI: `10.1126/science.aam9974`.
  - Decaestecker, E. et al. (2007). *Host-parasite 'Red Queen' dynamics archived in sediment*. Nature, 450(7171), 870–873. DOI: `10.1038/nature06291`.
- **Mathematical / Formal Definition**:
  - Time-shift interaction matrix $M(t_h, t_p)$: Host from generation $t_h$ exposed to parasite from generation $t_p$.
  - Lag offsets $\tau = t_p - t_h \in \{-80, -40, -20, 0, +20, +40, +80\}$.
  - Directional escalation vs fluctuating frequency-dependent selection (FDS) tests against fixed-host and fixed-parasite controls.

---

### T06: Causal Ledger & Intervention Integrity
- **Foundational Works**:
  - Pearl, J. (2009). *Causality: Models, Reasoning, and Inference* (2nd ed.). Cambridge University Press. DOI: `10.1017/CBO9780511803161`.
  - CausalEvolve (2026). *Towards Open-Ended Discovery with Causal Scratchpad*. arXiv: `2603.14575`.
- **Mathematical / Formal Definition**:
  - Intervention calculus $\text{do}(X = x)$ evaluating whether action policy relies on true causal edges versus observational confounders.
  - Ablation controls: Targeted causal edge ablation vs random edge ablation vs sham control (identical graph size and ATP cost).

---

### T07: Capsule-Mediated Skill Transfer
- **Foundational Works**:
  - Pan, S. J., & Yang, Q. (2010). *A Survey on Transfer Learning*. IEEE TKDE, 22(10), 1345–1359. DOI: `10.1109/TKDE.2009.191`.
  - Taylor, M. E., & Stone, P. (2009). *Transfer Learning for Reinforcement Learning Agents: A Survey*. JMLR, 10, 1633–1685.
- **Experimental Design**:
  - Capsule serialization containing compressed policy fragments passed horizontally or vertically across environmental task switches.
  - Sham control: Shuffled capsule payloads with identical byte size and ingestion ATP cost.

---

### T08: Automatically Defined Functions (ADF) & Energy Economy
- **Foundational Works**:
  - Koza, J. R. (1994). *Genetic Programming II: Automatic Discovery of Reusable Programs*. MIT Press.
  - Spector, L. (1996). *Simultaneous Evolution of Programs and their Control Structures*. In Advances in Genetic Programming.
- **Experimental Design**:
  - Macro compilation vs primitive instruction sequences.
  - True ATP accounting: Macro execution cost reflects underlying primitives; memory storage incurs continuous maintenance metabolic overhead.

---

### T09: Functional Information & Reference Sampling
- **Foundational Works**:
  - Hazen, R. M., Griffin, P. L., Carothers, J. M., & Szostak, J. W. (2007). *Functional information and the emergence of biocomplexity*. PNAS, 104(suppl_1), 8574–8581. DOI: `10.1073/pnas.0701744104`.
  - Szostak, J. W. (2003). *Functional information: Molecular messages*. Nature, 423(6941), 689. DOI: `10.1038/423689a`.
- **Mathematical / Formal Definition**:
  $$I(E) = -\log_2 \left(\frac{M(E)}{N}\right) = -\log_2 F(E)$$
  where $N$ is the total reference configuration space and $M(E)$ is the number of configurations satisfying functional criterion $E$.
  - Binomial confidence bounds applied when $M(E) = 0$ in $N$ samples ($p < 3/N$, Rule of Three).

---

### T10: Ecological Resilience & Perturbation Recovery
- **Foundational Works**:
  - Holling, C. S. (1973). *Resilience and stability of ecological systems*. Annual Review of Ecology and Systematics, 4(1), 1–23.
  - Lehman, C. L., & Tilman, D. (2000). *Biodiversity, stability, and productivity in competitive communities*. The American Naturalist, 156(5), 534–552. DOI: `10.1086/303402`.
- **Experimental Design**:
  - Two discrete shocks applied at generation 1000 (severe resource depletion) and generation 2000 (spatial resource reallocation).
  - Area Under the Curve (AUC) of functional degradation and recovery time measured.

---

### T11: Long-Horizon ARM Endurance & Equivalence
- **Foundational Works**:
  - ARM Architecture Reference Manual (ARMv8-A).
  - Deterministic Replay and State Verification in Distributed Systems (Lamport, 1978).
- **Engineering Objectives**:
  - 72-hour continuous multi-worker execution without memory leakage or state drift.
  - Canonical checkpoint digest verification: Bitwise identical state reconstruction after pause/resume and process restarts.

---

### T12: Collective Swarm Coordination
- **Foundational Works**:
  - Bonabeau, E., Dorigo, M., & Theraulaz, G. (1999). *Swarm Intelligence: From Natural to Artificial Systems*. Oxford University Press.
  - Rubenstein, M., Cornejo, A., & Nagpal, R. (2014). *Programmable self-assembly in a thousand-robot swarm*. Science, 345(6198), 795–799. DOI: `10.1126/science.1254295`.
- **Experimental Design**:
  - Collective resource harvesting with 8–16 agents under battery constraints, sensor noise, and communication dropouts.
  - Comparison of Genesis-evolved policy against deterministic A* and greedy baselines.
