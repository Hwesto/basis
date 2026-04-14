"""
pipeline.py — Unified extraction pipeline. Runs end to end.

Usage:
    # Extract legal nodes from a Lex provision
    python -m extraction.pipeline legal --lex-id "ukpga/2004/34/section/5" --domain housing

    # Extract evidence from a documentary source
    python -m extraction.pipeline evidence --url "https://ifs.org.uk/..." --domain health

    # Run full domain extraction via ego network
    python -m extraction.pipeline domain --anchor "ukpga/2004/34" --domain housing --hops 2

    # Check a single provision for amendments
    python -m extraction.pipeline check --lex-id "ukpga/2004/34/section/5"

Flow:
    Source -> Type routing -> Gemma extraction -> Flash cross-check
    -> Curator queue -> (Claude validation later) -> node_registry -> MC
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from base_schema import DomainEnum, JurisdictionEnum
from legal_schema import LegalNode
from source_models import (
    SourceTypeEnum,
    get_provider_tier,
)
from extraction.google_ai_client import (
    extract_legal_nodes,
    cross_check,
    classify_node_types,
    generate,
    FLASH_MODEL,
    GEMMA_MODEL,
    list_models,
)
from extraction.lex_client import (
    get_provision,
    get_explanatory_note,
    ego_network,
    check_amendment,
    compute_structural_stability,
    derive_commencement_status,
)


# ---------------------------------------------------------------------------
# Source type routing
# ---------------------------------------------------------------------------

def classify_source(url: str | None = None, metadata: dict | None = None) -> str:
    """Route an input to the correct source type."""
    meta = metadata or {}

    if "source_type" in meta:
        return meta["source_type"]

    if meta.get("lex_provision_id"):
        return "STRUCTURAL"
    if meta.get("computation_id"):
        return "DERIVED"

    if url:
        u = url.lower()
        if "doi.org" in u or meta.get("doi"):
            return "DOCUMENTARY"
        if any(api in u for api in ["ons.gov.uk/api", "police.uk/api", "digital.nhs.uk", "stat-xplore"]):
            return "STRUCTURED_DATA"
        if "lex" in u and ("provision" in u or "legislation" in u):
            return "STRUCTURAL"
        if any(p in u for p in ["hansard", "parliament.uk", "theyworkforyou"]):
            return "TESTIMONY"
        if "gov.uk" in u:
            return "DOCUMENTARY"

    if meta.get("provider") in ["ONS", "NHS Digital", "DWP", "Police.uk"]:
        return "STRUCTURED_DATA"
    if meta.get("actor") or meta.get("verbatim_ref"):
        return "TESTIMONY"

    return "DOCUMENTARY"


# ---------------------------------------------------------------------------
# Commencement gate
# ---------------------------------------------------------------------------

def commencement_gate(status: str) -> tuple[bool, str]:
    """SCHEMA-011: Block not_commenced/repealed. Pass others with notes."""
    if status in ("not_commenced", "repealed"):
        return False, f"Blocked: provision is {status}"
    if status == "partially_in_force":
        return True, "WARNING: partially in force — commencement_notes required"
    if status == "prospectively_repealed":
        return True, "WARNING: prospectively repealed — flagged for deprecation"
    if status == "unknown":
        return True, "WARNING: commencement status unknown"
    return True, "In force"


# ---------------------------------------------------------------------------
# Legal extraction pipeline
# ---------------------------------------------------------------------------

def extract_single_provision(
    lex_id: str,
    domain: str,
    jurisdiction: str = "england_and_wales",
    api_key: str | None = None,
    dry_run: bool = False,
) -> dict:
    """
    Full extraction pipeline for a single Lex provision.
    Returns a dict with extraction results and queue item.
    """
    result = {
        "lex_id": lex_id,
        "domain": domain,
        "status": "pending",
        "nodes": [],
        "queue_item": None,
        "errors": [],
    }

    # 1. Fetch provision from Lex
    print(f"  Fetching provision: {lex_id}")
    provision = get_provision(lex_id)
    if provision is None:
        result["status"] = "error"
        result["errors"].append(f"Could not fetch provision {lex_id} from Lex API")
        return result

    # 2. Commencement gate
    raw_status = provision.commencement_status
    comm_status = derive_commencement_status(raw_status)
    allowed, gate_note = commencement_gate(comm_status)
    print(f"  Commencement: {comm_status} — {gate_note}")

    if not allowed:
        result["status"] = "blocked"
        result["errors"].append(gate_note)
        return result

    # 3. Fetch explanatory note
    note = provision.explanatory_note
    if note is None:
        note = get_explanatory_note(lex_id)
    print(f"  Explanatory note: {'available' if note else 'not available'}")

    # 4. Compute structural signals
    stability = compute_structural_stability(
        provision.amendment_count, provision.last_amended
    )
    content_hash = hashlib.sha256(
        (provision.full_text or "").encode()
    ).hexdigest()

    # 5. Build lex_provisions row
    lex_row = {
        "lex_id": lex_id,
        "title": provision.title,
        "domain": domain,
        "jurisdiction": [jurisdiction],
        "full_text": provision.full_text,
        "explanatory_note": note,
        "content_hash": content_hash,
        "last_checked": datetime.now(timezone.utc).date().isoformat(),
        "amendment_watch": True,
        "in_degree": provision.in_degree,
        "amendment_count": provision.amendment_count,
        "last_amended": provision.last_amended,
        "commencement_status": comm_status,
        "structural_stability": stability,
        "citing_acts": provision.citing_acts,
    }
    result["lex_provision"] = lex_row

    if dry_run:
        print(f"  [DRY RUN] Would extract from: {provision.title}")
        result["status"] = "dry_run"
        return result

    # 6. Gemma extraction
    print(f"  Extracting via Gemma: {provision.title}")

    # Build schema for constrained output
    schema = LegalNode.model_json_schema()

    extraction = extract_legal_nodes(
        provision_text=provision.full_text or provision.title,
        lex_provision_id=lex_id,
        domain=domain,
        jurisdiction=jurisdiction,
        explanatory_note=note,
        response_schema=schema,
        key=api_key,
    )

    if not extraction.ok:
        result["status"] = "extraction_error"
        result["errors"].append(f"Gemma extraction failed: {extraction.error}")
        return result

    # Parse extraction
    extracted = extraction.parse_json()
    if extracted is None:
        # Try raw text
        try:
            extracted = json.loads(extraction.text)
        except json.JSONDecodeError:
            result["status"] = "parse_error"
            result["errors"].append(f"Could not parse Gemma output: {extraction.text[:200]}")
            return result

    # Handle single node or list
    if isinstance(extracted, dict):
        extracted_nodes = [extracted]
    elif isinstance(extracted, list):
        extracted_nodes = extracted
    else:
        result["status"] = "parse_error"
        result["errors"].append(f"Unexpected extraction format: {type(extracted)}")
        return result

    print(f"  Extracted {len(extracted_nodes)} node(s)")

    # 7. Flash cross-check each node
    for i, node_data in enumerate(extracted_nodes):
        print(f"  Cross-checking node {i+1}/{len(extracted_nodes)}...")

        check = cross_check(
            provision_text=provision.full_text or "",
            extracted_json=node_data,
            explanatory_note=note,
            key=api_key,
        )

        flash_result = "pass"
        flash_note = None

        if check.ok:
            check_text = check.text.strip().upper()
            if check_text.startswith("FAIL"):
                flash_result = "fail"
                flash_note = check.text.strip()
                print(f"    FLAGGED: {flash_note[:100]}")
            else:
                print(f"    PASS")
        else:
            flash_result = "error"
            flash_note = f"Cross-check error: {check.error}"
            print(f"    ERROR: {flash_note}")

        # Inject structural signals into node
        node_data["structural_stability"] = stability
        node_data["commencement_status"] = comm_status
        if comm_status == "partially_in_force" and not node_data.get("commencement_notes"):
            node_data["commencement_notes"] = gate_note

        # 8. Build curator queue item
        queue_item = {
            "node_type": node_data.get("node_type", "UNKNOWN"),
            "lex_provision_id": lex_id,
            "source_type": "STRUCTURAL",
            "registry": "lex_graph",
            "extracted_json": node_data,
            "extraction_run_id": f"pipeline_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            "flash_check_result": flash_result,
            "flash_check_note": flash_note,
            "needs_review": True,
            "flagged": flash_result == "fail",
            "flag_reason": flash_note if flash_result == "fail" else None,
        }

        result["nodes"].append(node_data)
        if result["queue_item"] is None:
            result["queue_item"] = []
        result["queue_item"].append(queue_item)

    result["status"] = "extracted"
    return result


# ---------------------------------------------------------------------------
# Domain extraction (ego network)
# ---------------------------------------------------------------------------

def extract_domain(
    anchor_id: str,
    domain: str,
    hops: int = 2,
    jurisdiction: str = "england_and_wales",
    max_provisions: int = 50,
    api_key: str | None = None,
    dry_run: bool = False,
) -> list[dict]:
    """
    SCHEMA-022: Extract all relevant provisions for a domain via ego network.
    """
    print(f"Ego network query: anchor={anchor_id}, hops={hops}")
    provisions = ego_network(anchor_id, hops=hops)

    if not provisions:
        print("No provisions found. Is the Lex API accessible?")
        return []

    print(f"Found {len(provisions)} provisions in ego network")

    # Limit for free tier
    if len(provisions) > max_provisions:
        print(f"Limiting to {max_provisions} provisions (free tier)")
        provisions = provisions[:max_provisions]

    results = []
    for i, prov in enumerate(provisions, 1):
        print(f"\n[{i}/{len(provisions)}] {prov.title}")
        result = extract_single_provision(
            lex_id=prov.lex_id,
            domain=domain,
            jurisdiction=jurisdiction,
            api_key=api_key,
            dry_run=dry_run,
        )
        results.append(result)

        # Status summary
        status = result["status"]
        n_nodes = len(result.get("nodes", []))
        errors = result.get("errors", [])
        if errors:
            print(f"  -> {status}: {errors[0][:80]}")
        else:
            print(f"  -> {status}: {n_nodes} node(s)")

    # Summary
    extracted = sum(1 for r in results if r["status"] == "extracted")
    blocked = sum(1 for r in results if r["status"] == "blocked")
    errored = sum(1 for r in results if "error" in r["status"])
    total_nodes = sum(len(r.get("nodes", [])) for r in results)
    print(f"\nDomain extraction complete: {extracted} extracted, "
          f"{blocked} blocked, {errored} errors, {total_nodes} total nodes")

    return results


# ---------------------------------------------------------------------------
# Evidence extraction
# ---------------------------------------------------------------------------

def extract_evidence(
    text: str,
    title: str,
    domain: str,
    tier: str = "T3",
    publisher: str = "",
    api_key: str | None = None,
) -> dict:
    """Extract evidence nodes from a documentary source."""
    from extraction.prompts import GEMMA_EVIDENCE_EXTRACTION

    prompt = GEMMA_EVIDENCE_EXTRACTION.format(
        title=title,
        tier=tier,
        publisher=publisher,
        passage=text[:8000],  # Gemma context limit
        domain=domain,
    )

    resp = generate(
        prompt=prompt,
        model=GEMMA_MODEL,
        response_mime_type="application/json",
        temperature=0.1,
        key=api_key,
    )

    if resp.ok:
        parsed = resp.parse_json()
        return {"status": "extracted", "nodes": parsed, "raw": resp.text}
    else:
        return {"status": "error", "error": resp.error}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="BASIS extraction pipeline")
    sub = parser.add_subparsers(dest="command")

    # Legal extraction
    legal = sub.add_parser("legal", help="Extract from a single Lex provision")
    legal.add_argument("--lex-id", required=True)
    legal.add_argument("--domain", required=True)
    legal.add_argument("--jurisdiction", default="england_and_wales")
    legal.add_argument("--dry-run", action="store_true")
    legal.add_argument("--output", default=None)

    # Domain extraction
    domain_cmd = sub.add_parser("domain", help="Extract all provisions for a domain")
    domain_cmd.add_argument("--anchor", required=True, help="Anchor Act lex_id")
    domain_cmd.add_argument("--domain", required=True)
    domain_cmd.add_argument("--hops", type=int, default=2)
    domain_cmd.add_argument("--max", type=int, default=50)
    domain_cmd.add_argument("--dry-run", action="store_true")
    domain_cmd.add_argument("--output", default=None)

    # Evidence extraction
    evidence = sub.add_parser("evidence", help="Extract evidence from text")
    evidence.add_argument("--file", required=True, help="Text file to extract from")
    evidence.add_argument("--domain", required=True)
    evidence.add_argument("--title", default="")
    evidence.add_argument("--tier", default="T3")

    # Amendment check
    check_cmd = sub.add_parser("check", help="Check provision for amendments")
    check_cmd.add_argument("--lex-id", required=True)
    check_cmd.add_argument("--stored-hash", default="")

    # Model check
    sub.add_parser("models", help="List available Google AI models")

    args = parser.parse_args()
    api_key = os.environ.get("GOOGLE_AI_API_KEY", "")

    if args.command == "models":
        models = list_models(api_key)
        for m in models:
            name = m.get("name", "")
            display = m.get("displayName", "")
            print(f"  {name}: {display}")
        return

    if args.command == "legal":
        result = extract_single_provision(
            lex_id=args.lex_id,
            domain=args.domain,
            jurisdiction=args.jurisdiction,
            api_key=api_key,
            dry_run=args.dry_run,
        )
        if args.output:
            with open(args.output, "w") as f:
                json.dump(result, f, indent=2, default=str)
            print(f"Output written to {args.output}")
        else:
            print(json.dumps(result, indent=2, default=str))

    elif args.command == "domain":
        results = extract_domain(
            anchor_id=args.anchor,
            domain=args.domain,
            hops=args.hops,
            max_provisions=args.max,
            api_key=api_key,
            dry_run=args.dry_run,
        )
        if args.output:
            with open(args.output, "w") as f:
                json.dump(results, f, indent=2, default=str)
            print(f"Output written to {args.output}")

    elif args.command == "evidence":
        with open(args.file) as f:
            text = f.read()
        result = extract_evidence(
            text=text,
            title=args.title,
            domain=args.domain,
            tier=args.tier,
            api_key=api_key,
        )
        print(json.dumps(result, indent=2, default=str))

    elif args.command == "check":
        changed = check_amendment(args.lex_id, args.stored_hash)
        if changed:
            print(f"CHANGED: {args.lex_id} has been amended since last extraction")
        else:
            print(f"UNCHANGED: {args.lex_id}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
