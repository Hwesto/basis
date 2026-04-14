"""
mc_engine.py — Monte Carlo confidence propagation engine.

SCHEMA-018: 10,000 samples, source-type-aware priors, edge-type-specific rules.
SCHEMA-019: Alpha values from source_models.py (provisional).
SCHEMA-020: Assumption contestability discount.

Edge semantics:
    SUPPORTS      -> noisy-OR (with independence flag, SCHEMA-015)
    CONTRADICTS   -> discount (symmetric)
    DEPENDS_ON    -> weakest-link (transitive)
    ENABLES       -> pass-through (deontic, not epistemic)
    COMPETES      -> no confidence effect (normative)
    SUPERSEDES    -> marks earlier as deprecated
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from source_models import (
    ASSUMPTION_DISCOUNT,
    VERIFIED_MULTIPLIER,
    get_documentary_alpha,
    get_structural_alpha,
    get_structured_data_alpha,
    get_testimony_alpha,
)
from base_schema import ConfidenceLevel


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_SAMPLES = 10_000
MAX_PROPAGATION_DEPTH = 20  # cycle breaker


@dataclass
class MCNode:
    """Internal representation for MC propagation."""
    id: str
    node_type: str
    confidence: str | None = None  # extraction-time: HIGH/MEDIUM/LOW
    verified: bool = False
    source_type: str | None = None
    source_tier: str | None = None
    citation_count: int | None = None
    influential_citation_count: int | None = None
    registry: str | None = None  # for STRUCTURAL sources
    provider_tier: str | None = None  # for STRUCTURED_DATA
    alpha: float | None = None  # resolved prior


@dataclass
class MCEdge:
    """Internal representation for MC edges."""
    from_id: str
    to_id: str
    edge_type: str
    strength: str | None = None
    evidence_independent: bool = True


@dataclass
class MCResult:
    """MC output for a single node."""
    node_id: str
    mean: float
    std: float
    p5: float
    p95: float
    label: str  # HIGH/MEDIUM/LOW

    def to_dict(self) -> dict:
        return {
            "mean": round(self.mean, 4),
            "std": round(self.std, 4),
            "p5": round(self.p5, 4),
            "p95": round(self.p95, 4),
            "label": self.label,
        }


# ---------------------------------------------------------------------------
# Alpha resolution
# ---------------------------------------------------------------------------

def resolve_alpha(node: MCNode) -> float:
    """
    Resolve the MC alpha prior for a node based on its source type.
    SCHEMA-019: These are design choices, not measurements.
    """
    if node.alpha is not None:
        return node.alpha

    st = node.source_type
    if st == "DOCUMENTARY":
        return get_documentary_alpha(
            tier=node.source_tier or "T4",
            verified=node.verified,
            citation_count=node.citation_count,
            influential_citation_count=node.influential_citation_count,
        )
    elif st == "STRUCTURED_DATA":
        return get_structured_data_alpha(node.provider_tier or "T3")
    elif st == "STRUCTURAL":
        return get_structural_alpha(node.registry or "unknown")
    elif st == "TESTIMONY":
        return get_testimony_alpha(node.source_tier or "T5")
    elif st == "DERIVED":
        return 0.0  # propagated from inputs, no independent alpha
    else:
        # Default: conservative
        return 0.50


def label_from_mean(mean: float) -> str:
    """Convert MC mean to categorical label."""
    if mean >= 0.70:
        return "HIGH"
    elif mean >= 0.45:
        return "MEDIUM"
    else:
        return "LOW"


# ---------------------------------------------------------------------------
# MC Propagation
# ---------------------------------------------------------------------------

class MCEngine:
    """
    Monte Carlo confidence propagation over the evidence graph.

    Usage:
        engine = MCEngine(nodes, edges, seed=42)
        results = engine.run(n_samples=10000)
    """

    def __init__(
        self,
        nodes: list[MCNode],
        edges: list[MCEdge],
        seed: int = 42,
    ):
        self.nodes = {n.id: n for n in nodes}
        self.edges = edges
        self.rng = np.random.default_rng(seed)

        # Build adjacency: target_id -> list of incoming edges
        self.incoming: dict[str, list[MCEdge]] = {}
        for edge in edges:
            self.incoming.setdefault(edge.to_id, []).append(edge)

        # Resolve alphas
        for node in self.nodes.values():
            node.alpha = resolve_alpha(node)

    def _sample_node(
        self,
        node_id: str,
        cache: dict[str, float],
        depth: int = 0,
    ) -> float:
        """Sample confidence for a single node, propagating from sources."""
        if node_id in cache:
            return cache[node_id]

        if depth > MAX_PROPAGATION_DEPTH:
            cache[node_id] = 0.5
            return 0.5

        node = self.nodes.get(node_id)
        if node is None:
            cache[node_id] = 0.5
            return 0.5

        # Base alpha (from source type)
        alpha = node.alpha or 0.5

        # Sample from Beta distribution around alpha
        # Tighter distribution for higher-quality sources
        concentration = 20.0  # controls spread
        a_param = alpha * concentration
        b_param = (1 - alpha) * concentration
        base_sample = self.rng.beta(max(a_param, 0.1), max(b_param, 0.1))

        # Propagate from incoming edges
        incoming = self.incoming.get(node_id, [])
        if not incoming:
            result = base_sample
        else:
            supports = []
            contradicts_discount = 1.0
            depends_on_min = 1.0
            has_depends = False

            for edge in incoming:
                upstream = self._sample_node(edge.from_id, cache, depth + 1)

                if edge.edge_type == "SUPPORTS":
                    supports.append((upstream, edge.evidence_independent))
                elif edge.edge_type == "CONTRADICTS":
                    contradicts_discount *= (1.0 - 0.3 * upstream)
                elif edge.edge_type == "DEPENDS_ON":
                    has_depends = True
                    depends_on_min = min(depends_on_min, upstream)
                elif edge.edge_type == "SUPERSEDES":
                    # Earlier node is deprecated; this node takes over
                    pass
                # ENABLES and COMPETES don't affect confidence

            # Noisy-OR for SUPPORTS (SCHEMA-015)
            if supports:
                independent_supports = [s for s, ind in supports if ind]
                correlated_supports = [s for s, ind in supports if not ind]

                noisy_or = 1.0
                for s in independent_supports:
                    noisy_or *= (1.0 - s)
                noisy_or = 1.0 - noisy_or

                # Correlated: take max (additive, conservative)
                corr_max = max(correlated_supports) if correlated_supports else 0.0

                # Combine: independent noisy-OR with correlated max
                if independent_supports and correlated_supports:
                    combined = 1.0 - (1.0 - noisy_or) * (1.0 - corr_max)
                elif independent_supports:
                    combined = noisy_or
                else:
                    combined = corr_max

                result = base_sample * combined
            else:
                result = base_sample

            # Weakest-link for DEPENDS_ON
            if has_depends:
                result = min(result, depends_on_min)

            # Contradiction discount
            result *= contradicts_discount

        # SCHEMA-020: Assumption contestability discount
        if node.node_type == "ASSUMPTION":
            cap = ASSUMPTION_DISCOUNT.get(node.confidence or "LOW", 0.50)
            result = min(result, cap)

        # SCHEMA-007: Verification boost (applied to base, not propagated)
        if node.verified and node.source_type == "DOCUMENTARY":
            result = min(result * 1.1, 1.0)  # modest boost, not full 1.5x at sample level

        result = max(0.0, min(1.0, result))
        cache[node_id] = result
        return result

    def run(self, n_samples: int = DEFAULT_SAMPLES) -> dict[str, MCResult]:
        """Run MC propagation. Returns results keyed by node_id."""
        all_samples: dict[str, list[float]] = {nid: [] for nid in self.nodes}

        for _ in range(n_samples):
            cache: dict[str, float] = {}
            for node_id in self.nodes:
                sample = self._sample_node(node_id, cache)
                all_samples[node_id].append(sample)

        results = {}
        for node_id, samples in all_samples.items():
            arr = np.array(samples)
            results[node_id] = MCResult(
                node_id=node_id,
                mean=float(np.mean(arr)),
                std=float(np.std(arr)),
                p5=float(np.percentile(arr, 5)),
                p95=float(np.percentile(arr, 95)),
                label=label_from_mean(float(np.mean(arr))),
            )

        return results


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def load_graph_from_json(data_dir: Path) -> tuple[list[MCNode], list[MCEdge]]:
    """Load nodes and edges from JSON files and convert to MC types."""
    nodes = []
    edges = []

    # Load nodes
    for f in data_dir.glob("**/*.json"):
        try:
            with open(f) as fh:
                data = json.load(fh)
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if "node_type" in item and "id" in item:
                        nodes.append(MCNode(
                            id=item["id"],
                            node_type=item.get("node_type", ""),
                            confidence=item.get("confidence"),
                            verified=item.get("verified", False),
                        ))
                    if "edge_type" in item and "from_id" in item:
                        edges.append(MCEdge(
                            from_id=item["from_id"],
                            to_id=item["to_id"],
                            edge_type=item.get("edge_type", "SUPPORTS"),
                            strength=item.get("strength"),
                            evidence_independent=item.get("evidence_independent", True),
                        ))
        except (json.JSONDecodeError, KeyError):
            continue

    return nodes, edges


def main():
    import argparse

    parser = argparse.ArgumentParser(description="MC confidence propagation")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--samples", type=int, default=DEFAULT_SAMPLES)
    parser.add_argument("--data-dir", type=str, default="data")
    parser.add_argument("--output", type=str, default="data/confidence_results.json")
    parser.add_argument("--sensitivity", action="store_true",
                        help="Run sensitivity analysis")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    nodes, edges = load_graph_from_json(data_dir)

    if not nodes:
        print("No nodes found. Nothing to propagate.")
        sys.exit(0)

    print(f"Running MC: {len(nodes)} nodes, {len(edges)} edges, "
          f"{args.samples} samples, seed={args.seed}")

    engine = MCEngine(nodes, edges, seed=args.seed)
    results = engine.run(n_samples=args.samples)

    # Write results
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output = {nid: r.to_dict() for nid, r in results.items()}
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    # Summary
    labels = [r.label for r in results.values()]
    print(f"\nResults: HIGH={labels.count('HIGH')}, "
          f"MEDIUM={labels.count('MEDIUM')}, "
          f"LOW={labels.count('LOW')}")
    print(f"Written to {output_path}")

    if args.sensitivity:
        print("\nSensitivity analysis: identifying highest-influence nodes...")
        # For each FACT node, zero it out and measure impact on downstream
        fact_nodes = [n for n in nodes if n.node_type == "FACT"]
        impacts = []
        baseline_means = {nid: r.mean for nid, r in results.items()}

        for fact in fact_nodes[:50]:  # limit to top 50 for speed
            # Create modified graph with this fact zeroed
            modified_nodes = []
            for n in nodes:
                mn = MCNode(**{k: getattr(n, k) for k in n.__dataclass_fields__})
                if mn.id == fact.id:
                    mn.alpha = 0.01  # effectively zero
                modified_nodes.append(mn)

            mod_engine = MCEngine(modified_nodes, edges, seed=args.seed)
            mod_results = mod_engine.run(n_samples=1000)  # fewer samples for speed

            total_impact = sum(
                abs(baseline_means[nid] - mod_results[nid].mean)
                for nid in baseline_means
                if nid in mod_results
            )
            impacts.append((fact.id, total_impact))

        impacts.sort(key=lambda x: x[1], reverse=True)
        print("\nTop 10 most influential FACT nodes:")
        for fid, impact in impacts[:10]:
            print(f"  {fid}: total downstream impact = {impact:.4f}")


if __name__ == "__main__":
    main()
