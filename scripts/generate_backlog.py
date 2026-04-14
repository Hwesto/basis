"""
generate_backlog.py — extract the 172 v1 sources into a v2 ingestion backlog.

v1 source shape (from data/basis-kg-full.json):
    {"id": "SRC-NHS-001", "title": "...", "url": null, "tier": 3,
     "author": "...", "date": "2024-09", "domain": "nhs"}

v2 backlog entry shape (one per source):
    {
      "source_id": "SRC-NHS-001",
      "url": "...",                # may be null for some v1 entries
      "title": "...",
      "author": "...",
      "published_date": "2024-09",
      "domain": "health",          # mapped from v1 'nhs' to v2 'health'
      "default_tier_hint": "T3",   # v1 integer tier -> 'T<n>'
      "priority": "high|medium|low",
      "metadata": {"v1_id": "SRC-NHS-001", "v1_domain": "nhs"}
    }

Priority heuristic:
    - high: v1 tier 1-3 (authoritative)
    - medium: v1 tier 4
    - low: v1 tier 5-6

Run:
    python scripts/generate_backlog.py
Output:
    data/v1_ingestion_backlog.json
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GRAPH = REPO / "archive" / "v1" / "data" / "basis-kg-full.json"
BACKLOG = REPO / "data" / "v1_ingestion_backlog.json"

V1_TO_V2_DOMAIN = {
    "housing": "housing",
    "nhs": "health",
    "education": "education",
    "welfare": "benefits",
    "taxation": "taxation",
    "environment": "environment",
    "immigration": "immigration",
    "defence": "defence",
    "justice": "justice",
    # Newly-added v2 domains (SCHEMA-002 v2)
    "energy": "energy",
    "eu-trade": "eu_trade",
    "electoral-reform": "electoral_reform",
}


def priority_for_tier(tier: int | None) -> str:
    if tier in (1, 2, 3):
        return "high"
    if tier == 4:
        return "medium"
    return "low"


def main() -> None:
    graph = json.loads(GRAPH.read_text())
    sources = graph["sources"]

    # Sentinel header as first entry — documents the backlog's origin
    # and the url-recovery strategy for v1 sources that were never URL-captured.
    backlog: list[dict] = [{
        "_meta": True,
        "generated_from": "data/basis-kg-full.json (v1 archive)",
        "v1_source_count": len(sources),
        "note": (
            "v1 sources have no URLs — only (title, author, tier, date). "
            "The v2 ingestion pipeline must resolve URLs before fetching. "
            "Resolution order: DOI (if any) via CrossRef / Semantic Scholar; "
            "publisher website search (e.g. ifs.org.uk/search) by title; "
            "gov.uk content API by title; fallback to Google Custom Search "
            "with publisher-domain filter. Entries that do not yield a URL "
            "go to the manual curator backlog."
        ),
    }]
    for s in sources:
        raw_tier = s.get("tier")
        tier_str = f"T{raw_tier}" if isinstance(raw_tier, int) else None
        v1_domain = s.get("domain") or ""
        v2_domain = V1_TO_V2_DOMAIN.get(v1_domain, v1_domain)

        backlog.append({
            "source_id": s.get("id"),
            "url": s.get("url"),
            "title": s.get("title"),
            "author": s.get("author"),
            "published_date": s.get("date"),
            "domain": v2_domain,
            "default_tier_hint": tier_str,
            "priority": priority_for_tier(raw_tier),
            "metadata": {
                "v1_id": s.get("id"),
                "v1_domain": v1_domain,
                "v1_tier": raw_tier,
            },
        })

    # Sort: _meta first, then high-priority, then by source_id for stability.
    priority_rank = {"high": 0, "medium": 1, "low": 2}
    def sort_key(e: dict) -> tuple:
        if e.get("_meta"):
            return (-1, "")
        return (priority_rank.get(e["priority"], 3), e["source_id"] or "")
    backlog.sort(key=sort_key)

    BACKLOG.write_text(json.dumps(backlog, indent=2))
    entries = [e for e in backlog if not e.get("_meta")]
    print(f"Wrote {len(entries)} backlog entries to {BACKLOG.relative_to(REPO)}")
    print(f"  High priority:   {sum(1 for e in entries if e['priority'] == 'high')}")
    print(f"  Medium priority: {sum(1 for e in entries if e['priority'] == 'medium')}")
    print(f"  Low priority:    {sum(1 for e in entries if e['priority'] == 'low')}")
    print(f"  With URLs:       {sum(1 for e in entries if e['url'])}")
    print(f"  Without URLs:    {sum(1 for e in entries if not e['url'])}")


if __name__ == "__main__":
    main()
