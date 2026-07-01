# Circuit corpus reference

All 17 circuits currently registered in `qloop/circuits/`. "Stages" lists which of the six pipeline stages actually run for that circuit (based on which optional `CircuitSpec` methods it implements) — everything not listed skips visibly rather than silently passing.

## Base circuits (pre-framework)

| Name | Qubits | Stages | Notes |
|------|--------|--------|-------|
| `bell` | 2 | 2, 3, 4, 5 | Bell state; the original minimal example |
| `grover` | 2 | 3, 4 | 2-qubit Grover search, `marked` bitstring swept via `param_space` |
| `vqe` | 2 | 2, 3, 4 | Hardware-efficient ansatz against a toy 2-qubit Hamiltonian |

## Tier 0 — seed benchmarks

Airtight closed-form oracles, chosen to validate all six stages end to end before later tiers remove that safety net.

| Name | Qubits | Stages | Source |
|------|--------|--------|--------|
| `ghz` | 12 | 2, 3, 4 | CNOT-ladder GHZ; textbook |
| `ghz-tree` | 12 | 2, 3, 4 | Log-depth CNOT-tree GHZ, contrasted against `ghz`; textbook |
| `qft` | 4 | 2, 3, 4 | Qiskit's `QFTGate`; round-trip-identity and add-1-in-Fourier-basis oracles |
| `tfim-trotter` | 4 | 2 (tolerance-band), 3, 4 | Trotterized transverse-field Ising evolution; textbook |
| `mermin-bell` | 3 | 2, 3, 4 | GHZ + Mermin operator, exact quantum violation of the classical bound |

## Tier 1 — Clifford QEC

| Name | Qubits | Stages | Source |
|------|--------|--------|--------|
| `bb-code-72` | 144 | 3b (Stim), 4 | Bravyi, Cross, Gambetta, Maslov, Rall, Yoder, *Nature* 627, 778 (2024), [arXiv:2308.07915](https://arxiv.org/abs/2308.07915) — [[72,12,6]] bivariate-bicycle code |

## Tier 2 — non-Clifford exact oracles

| Name | Qubits | Stages | Source |
|------|--------|--------|--------|
| `color-832-ccz` | 8 | 2, 3, 4 | [arXiv:2309.08663](https://arxiv.org/abs/2309.08663) — [[8,3,2]] color code transversal CCZ; logical operators derived from scratch via GF(2) linear algebra |
| `dicke` | 6 | 2, 3, 4 | Motivated by Yuan & Zhang, [arXiv:2505.15413](https://arxiv.org/abs/2505.15413) — implements a simpler, independently-verifiable hypergeometric-recursion construction rather than that paper's specific algorithm |
| `gqsp` | 1 | 3 (via `invariants_for`), 4 | Motivated by Motlagh & Wiebe GQSP, [arXiv:2308.01501](https://arxiv.org/abs/2308.01501) — implements classic single-qubit QSP (a strict special case) with phases derived numerically, not reproduced from the paper |

## Tier 3 — topology + statistics

| Name | Qubits | Stages | Source |
|------|--------|--------|--------|
| `qaoa-maxcut` | 6 | 2, 3, 4, 5 | Motivated by PHOENIX, [arXiv:2504.03529](https://arxiv.org/abs/2504.03529) — standard p=1 QAOA MaxCut on K₃,₃ (non-local graph) |
| `qaoa-ring` | 6 | 2, 3, 4, 5 | Motivated by [arXiv:2509.17296](https://arxiv.org/abs/2509.17296) — same ansatz on a 6-cycle (local graph), contrasted against `qaoa-maxcut` |
| `quantum-volume` | 4 | 3, 4, 5 | Cross et al., *Phys. Rev. A* 100, 032328 (2019) — fixed-seed random-circuit model; heavy-output criterion checked as an invariant, not against an external oracle |

## Tier 4 — hard tier

| Name | Qubits | Stages | Source |
|------|--------|--------|--------|
| `bb-code-144` | 288 | 3b (Stim), 4 | Same source as `bb-code-72`, scaled to the [[144,12,12]] gross code (l=12, m=6) |
| `magic-cultivation` | 3 | 3, 4 | Motivated by Gidney, Shutty & Jones, [arXiv:2409.17595](https://arxiv.org/abs/2409.17595) — implements a genuine (but much simpler) postselected stabilizer-based magic-state verification, not the paper's surface-code cultivation protocol |

## Where "stages" comes from

Read directly off which optional `CircuitSpec` methods each circuit implements — see [Architecture](architecture.html#the-six-pipeline-stages) for the mapping. To check any circuit's actual behavior yourself:

```python
from qloop.core.registry import registry

spec = registry.get("dicke")
print("exact tier:", spec.reference_state() is not None)
print("noisy tier:", spec.expected_distribution() is not None)
print("stim tier:", spec.stim_program() is not None)
```
