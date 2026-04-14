#!/usr/bin/env python3
"""
Split BASIS_ROADMAP.md and schema_decisions.md into per-decision, per-question,
and per-phase markdown files under docs/. Adds YAML front-matter with status,
phase, and cross-reference metadata.

Idempotent — safe to re-run. Leaves the monoliths in place.
"""
from __future__ import annotations

import re
from pathlib import Path
from textwrap import dedent

REPO = Path(__file__).resolve().parents[1]
SCHEMA_MD = REPO / "schema_decisions.md"
ROADMAP_MD = REPO / "BASIS_ROADMAP.md"

DECISIONS_DIR = REPO / "docs" / "schema" / "decisions"
OQ_DIR = REPO / "docs" / "schema" / "open_questions"
ROADMAP_DIR = REPO / "docs" / "roadmap"
INFRA_DIR = REPO / "docs" / "infrastructure"

SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    return SLUG_RE.sub("-", text.lower()).strip("-")


# ---------------------------------------------------------------------------
# Schema decisions
# ---------------------------------------------------------------------------

SCHEMA_HEADER = re.compile(r"^### SCHEMA-(\d{3}): (.+)$", re.MULTILINE)


def split_schema_decisions() -> list[dict]:
    text = SCHEMA_MD.read_text()
    matches = list(SCHEMA_HEADER.finditer(text))
    records = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].rstrip()

        # Strip trailing horizontal rules that separated entries in the monolith.
        body = re.sub(r"\n+---\s*$", "", body)

        sid = f"SCHEMA-{m.group(1)}"
        title = m.group(2).strip()

        # Status line: "**Status:** SETTLED — ..." or similar.
        status = "UNKNOWN"
        sm = re.search(r"\*\*Status:\*\*\s*([A-Z]+)", body)
        if sm:
            status = sm.group(1)

        # Cross-refs: OQs resolved or referenced.
        resolves = sorted(set(re.findall(r"(?:Resolves|RESOLVED by .*?|Resolves )\s*(OQ-\d{3})", body)))
        related_oqs = sorted(set(re.findall(r"OQ-\d{3}", body)))
        # Keep "resolves" as the ones literally claimed; "related" as the rest.
        related = sorted(set(related_oqs) - set(resolves))

        records.append(
            {
                "id": sid,
                "title": title,
                "status": status,
                "resolves": resolves,
                "related": related,
                "body": body,
            }
        )
    return records


def write_schema_files(records: list[dict]) -> None:
    DECISIONS_DIR.mkdir(parents=True, exist_ok=True)
    for r in records:
        slug = slugify(r["title"])[:60].strip("-")
        path = DECISIONS_DIR / f"{r['id']}-{slug}.md"
        front = [
            "---",
            f"id: {r['id']}",
            f"title: {r['title']}",
            f"status: {r['status']}",
        ]
        if r["resolves"]:
            front.append("resolves: [" + ", ".join(r["resolves"]) + "]")
        if r["related"]:
            front.append("related: [" + ", ".join(r["related"]) + "]")
        front.append("source: schema_decisions.md")
        front.append("---")
        path.write_text("\n".join(front) + "\n\n" + r["body"] + "\n")


# ---------------------------------------------------------------------------
# Open questions
# ---------------------------------------------------------------------------

OQ_ROW = re.compile(
    r"^\|\s*(~~)?(OQ-\d{3})(~~)?\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|$",
    re.MULTILINE,
)


def split_open_questions() -> list[dict]:
    text = SCHEMA_MD.read_text()
    records = []
    for m in OQ_ROW.finditer(text):
        oid = m.group(2)
        question = m.group(4).strip()
        blocking = m.group(5).strip()
        phase = m.group(6).strip()
        resolved = bool(m.group(1)) or "RESOLVED" in question or "Resolved" in question
        records.append(
            {
                "id": oid,
                "question": question,
                "blocking": blocking,
                "phase": phase,
                "resolved": resolved,
            }
        )
    # De-duplicate by id, keep last (post-reconciliation the resolved row is last).
    seen: dict[str, dict] = {}
    for r in records:
        seen[r["id"]] = r
    return list(seen.values())


def write_oq_files(records: list[dict]) -> None:
    OQ_DIR.mkdir(parents=True, exist_ok=True)
    for r in records:
        title_for_slug = re.sub(r"~~|\*\*|RESOLVED.*|Resolved.*", "", r["question"]).strip()
        slug = slugify(title_for_slug)[:60].strip("-") or "question"
        path = OQ_DIR / f"{r['id']}-{slug}.md"
        if r["resolved"]:
            status = "resolved"
        elif re.search(r"Deferred|\(Deferred", r["question"]):
            status = "deferred"
        else:
            status = "open"
        front = [
            "---",
            f"id: {r['id']}",
            f"status: {status}",
            f"blocking: {r['blocking']}",
            f"phase: {r['phase']}",
            "source: schema_decisions.md",
            "---",
        ]
        body = f"# {r['id']}\n\n**Question:** {r['question']}\n\n**Blocking:** {r['blocking']}\n\n**Phase:** {r['phase']}\n"
        path.write_text("\n".join(front) + "\n\n" + body)


# ---------------------------------------------------------------------------
# Roadmap phases
# ---------------------------------------------------------------------------

PHASE_HEADER = re.compile(r"^### ((?:COMPLETED|NEXT|Foundation|Legislation|Phase) [^\n]+)$", re.MULTILINE)


def split_roadmap() -> list[dict]:
    text = ROADMAP_MD.read_text()
    # Only split from the "## Phase Roadmap" section onward.
    start = text.find("## Phase Roadmap")
    if start < 0:
        return []
    end = text.find("## Technical Architecture")
    if end < 0:
        end = len(text)
    section = text[start:end]

    matches = list(PHASE_HEADER.finditer(section))
    records = []
    for i, m in enumerate(matches):
        hdr = m.group(1).strip()
        s = m.start()
        e = matches[i + 1].start() if i + 1 < len(matches) else len(section)
        body = section[s:e].rstrip()

        # Determine phase number + status.
        status = "planned"
        if hdr.startswith("COMPLETED"):
            status = "completed"
        elif hdr.startswith("NEXT"):
            status = "in_progress"

        # Phase number — check special prefixes first, else pull from header.
        phase_num = None
        # Strip COMPLETED/NEXT status prefix before matching the real header start.
        head = re.sub(r"^(COMPLETED|NEXT)\s+—\s+", "", hdr)
        if head.startswith("Foundation"):
            phase_num = "foundation"
        elif head.startswith("Legislation"):
            phase_num = "audit"
        else:
            pm = re.search(r"Phase\s+(\d+[ab]?)", head)
            if pm:
                phase_num = pm.group(1)

        records.append(
            {
                "header": hdr,
                "phase": phase_num,
                "status": status,
                "body": body,
            }
        )
    return records


def phase_filename(r: dict) -> str:
    p = r["phase"]
    slug_source = r["header"].replace("COMPLETED — ", "").replace("NEXT — ", "")
    slug = slugify(slug_source)[:60].strip("-")
    ordering = {
        "foundation": "00",
        "0": "01",
        "1": "02",
        "2a": "03",
        "2b": "04",
        "audit": "05",
        "3": "06",
        "4": "07",
        "5": "08",
        "6": "09",
        "7": "10",
        "8": "11",
    }
    prefix = ordering.get(str(p), "99")
    return f"{prefix}-{slug}.md"


def write_roadmap_files(records: list[dict]) -> None:
    ROADMAP_DIR.mkdir(parents=True, exist_ok=True)
    for r in records:
        path = ROADMAP_DIR / phase_filename(r)
        front = [
            "---",
            f"phase: {r['phase']}",
            f"status: {r['status']}",
            "source: BASIS_ROADMAP.md",
            "---",
        ]
        path.write_text("\n".join(front) + "\n\n" + r["body"] + "\n")


# ---------------------------------------------------------------------------
# Indexes
# ---------------------------------------------------------------------------


def write_schema_index(decisions: list[dict], oqs: list[dict]) -> None:
    (REPO / "docs" / "schema").mkdir(parents=True, exist_ok=True)
    lines = [
        "# Schema decisions — index",
        "",
        "Canonical source for each decision and open question lives in this folder.",
        "`schema_decisions.md` in the repo root is retained as a read-only monolith and",
        "will be regenerated from these files.",
        "",
        "## Decisions",
        "",
        "| ID | Title | Status | Resolves |",
        "|---|---|---|---|",
    ]
    for r in sorted(decisions, key=lambda x: x["id"]):
        slug = slugify(r["title"])[:60].strip("-")
        resolves = ", ".join(r["resolves"]) if r["resolves"] else ""
        lines.append(
            f"| [{r['id']}](decisions/{r['id']}-{slug}.md) | {r['title']} | {r['status']} | {resolves} |"
        )
    lines += ["", "## Open questions", "", "| ID | Status | Blocking | Phase |", "|---|---|---|---|"]
    for r in sorted(oqs, key=lambda x: x["id"]):
        title_for_slug = re.sub(r"~~|\*\*|RESOLVED.*|Resolved.*", "", r["question"]).strip()
        slug = slugify(title_for_slug)[:60].strip("-") or "question"
        if r["resolved"]:
            status = "resolved"
        elif re.search(r"Deferred|\(Deferred", r["question"]):
            status = "deferred"
        else:
            status = "open"
        lines.append(
            f"| [{r['id']}](open_questions/{r['id']}-{slug}.md) | {status} | {r['blocking']} | {r['phase']} |"
        )
    (REPO / "docs" / "schema" / "README.md").write_text("\n".join(lines) + "\n")


def write_roadmap_index(records: list[dict]) -> None:
    lines = [
        "# Roadmap — index",
        "",
        "Canonical source per phase. `BASIS_ROADMAP.md` in the repo root is retained",
        "as a read-only monolith and will be regenerated from these files.",
        "",
        "| Phase | Name | Status |",
        "|---|---|---|",
    ]
    # Sort by filename prefix so the index reads top-to-bottom in pipeline order.
    for r in sorted(records, key=lambda x: phase_filename(x)):
        fname = phase_filename(r)
        lines.append(f"| {r['phase']} | [{r['header']}]({fname}) | {r['status']} |")
    (ROADMAP_DIR / "README.md").write_text("\n".join(lines) + "\n")


def write_infra_stub() -> None:
    INFRA_DIR.mkdir(parents=True, exist_ok=True)
    stub = dedent(
        """\
        # Infrastructure — index

        Cross-cutting systems referenced from multiple phases. One file per system.

        Planned (to be extracted from monoliths in the next pass):

        - `curator-queue.md` — single queue, node_type discriminator
        - `mc-engine.md` — Monte Carlo propagation, alpha priors, 10k samples
        - `ci-validator.md` — 8 checks (schema, edges, topics, fiscal, confidence, sources, checks 7-8 legal)
        - `source-pipeline.md` — ingestion, Semantic Scholar enrichment, tier assignment

        These are referenced by the SCHEMA decisions and by the Phase roadmap files.
        """
    )
    (INFRA_DIR / "README.md").write_text(stub)


def main() -> None:
    decisions = split_schema_decisions()
    oqs = split_open_questions()
    roadmap = split_roadmap()

    write_schema_files(decisions)
    write_oq_files(oqs)
    write_roadmap_files(roadmap)
    write_schema_index(decisions, oqs)
    write_roadmap_index(roadmap)
    write_infra_stub()

    print(f"Wrote {len(decisions)} SCHEMA decisions")
    print(f"Wrote {len(oqs)} open questions")
    print(f"Wrote {len(roadmap)} roadmap phase files")


if __name__ == "__main__":
    main()
