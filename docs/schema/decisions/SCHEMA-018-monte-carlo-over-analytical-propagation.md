---
id: SCHEMA-018
title: Monte Carlo over analytical propagation
status: SETTLED
source: schema_decisions.md
---

### SCHEMA-018: Monte Carlo over analytical propagation

**Phenomenon:** Confidence propagates through the graph from source nodes to terminal
nodes via typed edges. We need a method that handles the mixed edge types (noisy-OR,
weakest-link, discount) in a unified framework.

**Decision:** Monte Carlo simulation: 10,000 samples per run, each sample propagates
confidence from FACT nodes upward using edge-type-specific rules. The distribution
of outcomes gives mean, std, p5, p95.

**Alternatives:**
- Analytical propagation: derive exact formulas for each edge type combination.
  Possible for simple chains. Intractable for general DAGs with mixed edge types.
- Bayesian network: principled, but requires specifying conditional probability
  tables for all node combinations. Too much specification overhead for 389 nodes.
- Simple average of upstream confidence. Rejected: loses the structural information
  that DEPENDS_ON edges should use weakest-link semantics.

**Assumptions:**
1. 10,000 samples is sufficient for stable estimates. Verified: variance <1% across
   runs with seed=42. For p5/p95 stability, 10K is the minimum. Could reduce to 5K
   for speed without material accuracy loss.
2. The graph is approximately a DAG (directed acyclic graph). Verified: 4 cycles
   exist in the current graph. All cycles involve POSITION nodes (political positions
   referencing each other). The MC handles cycles by capping propagation depth.
3. 25 seconds runtime is acceptable. True for 389 nodes. At 5,000 nodes (legal layer
   added), runtime will scale roughly linearly to ~4 minutes. Scope-limited propagation
   (within domain only in steady state) will be required before Phase 4.

**Status:** SETTLED on approach. PROVISIONAL on runtime scaling.
