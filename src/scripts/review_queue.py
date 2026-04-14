#!/usr/bin/env python3
"""
review_queue.py — minimal terminal CLI for the SCHEMA-024 Tier 3 queue.

Pulls tier=3 candidate-node entries from local jsonl persistence
(data/v2_graph/candidate_nodes.jsonl) and walks the operator through
them one at a time. Approve / reject / kickback / skip decisions are
written back to the file in place — atomic per-row, no partial writes.

Replaced by the v2 Next.js frontend admin page in Phase 2; this is
the operator-side equivalent for now.

Usage:
    python src/scripts/review_queue.py            # interactive
    python src/scripts/review_queue.py --count    # just count by tier
    python src/scripts/review_queue.py --tier 3   # filter (default 3)
    python src/scripts/review_queue.py --reason precedent_node
                                                  # filter by escalation
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

from ingest.persistence import LOCAL_NODES_PATH  # noqa: E402

# ANSI colours for the terminal — falls back to no-op in non-tty.
_RESET = "\033[0m" if sys.stdout.isatty() else ""
_BOLD = "\033[1m" if sys.stdout.isatty() else ""
_GREEN = "\033[32m" if sys.stdout.isatty() else ""
_YELLOW = "\033[33m" if sys.stdout.isatty() else ""
_RED = "\033[31m" if sys.stdout.isatty() else ""
_CYAN = "\033[36m" if sys.stdout.isatty() else ""


# ---------------------------------------------------------------------------
# Loading + filtering
# ---------------------------------------------------------------------------

def load_nodes() -> list[dict]:
    """Read every candidate-node row from the local jsonl store."""
    if not LOCAL_NODES_PATH.exists():
        return []
    nodes: list[dict] = []
    with LOCAL_NODES_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                nodes.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return nodes


def filter_nodes(
    nodes: list[dict], tier: int | None, reason: str | None,
    only_pending: bool,
) -> list[dict]:
    out = []
    for n in nodes:
        r = n.get("_routing") or {}
        if tier is not None and r.get("tier") != tier:
            continue
        if reason is not None and r.get("escalation_reason") != reason:
            continue
        if only_pending and n.get("curator_approved"):
            continue
        if only_pending and r.get("_review_decision"):
            continue
        out.append(n)
    return out


# ---------------------------------------------------------------------------
# Per-node review UX
# ---------------------------------------------------------------------------

def render_node(n: dict, idx: int, total: int) -> None:
    r = n.get("_routing") or {}
    print(f"\n{_BOLD}{'=' * 70}{_RESET}")
    print(f"{_BOLD}Node {idx + 1} of {total}{_RESET}  "
          f"id={n.get('id', '?')}  "
          f"type={n.get('node_type', '?')}  "
          f"domain={n.get('domain', '?')}")
    print(f"{_BOLD}{'=' * 70}{_RESET}")

    # Routing context
    tier = r.get("tier")
    reason = r.get("escalation_reason")
    fail = r.get("fast_fail_check")
    tier_colour = _RED if tier == 3 else _YELLOW if tier == 2 else _GREEN
    print(f"  Tier:       {tier_colour}{tier}{_RESET}")
    print(f"  Reason:     {_CYAN}{reason}{_RESET}")
    if fail:
        print(f"  Fast-fail:  {_CYAN}{fail}{_RESET}")
    if r.get("notes"):
        for note in r["notes"]:
            print(f"  Note:       {note}")

    # Statement (the meat of the node)
    if n.get("statement"):
        print(f"\n  {_BOLD}statement:{_RESET}")
        print(f"    {n['statement']}")

    # Source pointer
    if n.get("source_id"):
        print(f"\n  {_BOLD}source_id:{_RESET} {n['source_id']}")
    if n.get("source_loc"):
        print(f"  source_loc: {n['source_loc']}")

    # Optional structured fields
    for field in ("falsification_condition", "actor", "actor_type",
                  "extraction_notes", "civic_finding_kind"):
        if n.get(field):
            print(f"  {field}: {n[field]}")

    # Fiscal
    if n.get("fiscal"):
        print(f"\n  {_BOLD}fiscal:{_RESET} {json.dumps(n['fiscal'], default=str)[:200]}")


def prompt_decision() -> str:
    """Return one of: a (approve), r (reject), k (kickback), s (skip), q (quit)."""
    while True:
        choice = input(
            f"\n{_BOLD}[a]{_RESET}pprove  "
            f"{_BOLD}[r]{_RESET}eject  "
            f"{_BOLD}[k]{_RESET}ickback  "
            f"{_BOLD}[s]{_RESET}kip  "
            f"{_BOLD}[q]{_RESET}uit > "
        ).strip().lower()
        if choice in ("a", "r", "k", "s", "q"):
            return choice
        print("  invalid — pick one of a / r / k / s / q")


def collect_notes(prompt: str) -> str:
    return input(f"  {prompt}: ").strip()


# ---------------------------------------------------------------------------
# Persisting decisions
# ---------------------------------------------------------------------------

def apply_decision(node_id: str, decision: dict) -> int:
    """Re-write the jsonl file with `decision` merged into the matching row.

    Atomic: writes to a sibling tmp file then replaces.
    Returns the number of rows updated (0 if not found, >1 if duplicates).
    """
    if not LOCAL_NODES_PATH.exists():
        return 0
    tmp_path = LOCAL_NODES_PATH.with_suffix(".jsonl.tmp")
    updated = 0
    with LOCAL_NODES_PATH.open("r", encoding="utf-8") as src:
        with tmp_path.open("w", encoding="utf-8") as dst:
            for line in src:
                stripped = line.strip()
                if not stripped:
                    dst.write(line)
                    continue
                try:
                    row = json.loads(stripped)
                except json.JSONDecodeError:
                    dst.write(line)
                    continue
                if row.get("id") == node_id:
                    row.setdefault("_routing", {})["_review_decision"] = decision
                    if decision["action"] == "approve":
                        row["curator_approved"] = True
                        row["approved_by"] = "human"
                        row["verification_level"] = "human_curated"
                        row["last_audited_by"] = "human"
                        row["last_audited_at"] = decision["at"]
                    elif decision["action"] == "kickback":
                        row.setdefault("_routing", {})["kickback"] = True
                        row.setdefault("_routing", {})["kickback_reason"] = decision.get("notes", "")
                    updated += 1
                dst.write(json.dumps(row, default=str) + "\n")
    tmp_path.replace(LOCAL_NODES_PATH)
    return updated


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="SCHEMA-024 Tier 3 review CLI")
    parser.add_argument(
        "--tier", type=int, default=3,
        help="Filter by tier (default 3 — the human queue).",
    )
    parser.add_argument(
        "--reason", default=None,
        help="Filter by escalation_reason (e.g. precedent_node).",
    )
    parser.add_argument(
        "--count", action="store_true",
        help="Just print counts; don't enter interactive mode.",
    )
    parser.add_argument(
        "--include-decided", action="store_true",
        help="Include nodes that already have a review decision recorded.",
    )
    args = parser.parse_args()

    nodes = load_nodes()
    if not nodes:
        print(f"No candidate nodes found at {LOCAL_NODES_PATH.relative_to(REPO)}.")
        print("Run an ingestion (e.g. `python src/scripts/run_agent.py evidence`) first.")
        return

    if args.count:
        all_tiers = Counter(
            (n.get("_routing") or {}).get("tier") for n in nodes
        )
        all_reasons = Counter(
            (n.get("_routing") or {}).get("escalation_reason") for n in nodes
        )
        print(f"{_BOLD}Total candidate nodes:{_RESET} {len(nodes)}")
        print(f"\n{_BOLD}By tier:{_RESET}")
        for tier in sorted(all_tiers, key=lambda x: (x is None, x)):
            print(f"  tier={tier}: {all_tiers[tier]}")
        print(f"\n{_BOLD}By escalation reason:{_RESET}")
        for reason, count in all_reasons.most_common():
            print(f"  {reason}: {count}")
        return

    pending = filter_nodes(
        nodes, tier=args.tier, reason=args.reason,
        only_pending=not args.include_decided,
    )
    if not pending:
        print(
            f"No pending tier={args.tier} nodes"
            + (f" with reason={args.reason}" if args.reason else "")
            + "."
        )
        return

    print(f"{_BOLD}Reviewing {len(pending)} pending tier-{args.tier} node(s).{_RESET}")
    print("(Decisions are persisted as you go; you can quit at any time.)")

    decided = 0
    for i, node in enumerate(pending):
        render_node(node, i, len(pending))
        choice = prompt_decision()
        if choice == "q":
            break

        action_map = {
            "a": "approve",
            "r": "reject",
            "k": "kickback",
            "s": "skip",
        }
        action = action_map[choice]

        if action == "skip":
            continue

        notes_prompt = {
            "approve": "approval note (optional)",
            "reject":  "reason for rejection",
            "kickback":"why Claude got this wrong (for kickback log)",
        }[action]
        notes = collect_notes(notes_prompt)

        decision = {
            "action": action,
            "by": "harry",  # in the future: env var or argparse
            "at": datetime.now(timezone.utc).isoformat(),
            "notes": notes,
        }
        n_updated = apply_decision(node["id"], decision)
        if n_updated == 0:
            print(f"  {_RED}WARNING: node id {node['id']!r} not found in jsonl; not persisted.{_RESET}")
        else:
            tag = {
                "approve":  f"{_GREEN}approved{_RESET}",
                "reject":   f"{_RED}rejected{_RESET}",
                "kickback": f"{_YELLOW}kicked back{_RESET}",
            }[action]
            print(f"  {tag}.")
            decided += 1

    print(f"\n{_BOLD}Done.{_RESET} Decided {decided} of {len(pending)}.")


if __name__ == "__main__":
    main()
