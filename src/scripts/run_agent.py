#!/usr/bin/env python3
"""
run_agent.py — Execute a specific extraction agent.

Usage:
    python scripts/run_agent.py legal_extraction
    python scripts/run_agent.py structural_signals
    python scripts/run_agent.py local_data --dry-run
    python scripts/run_agent.py legal_extraction --domain housing --max 10

Called by GitHub Actions cron jobs or manually.
"""

import argparse
import hashlib
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from extraction.agents import AGENTS, AgentRun


def run_legal_extraction(args, run: AgentRun):
    """Daily: check watched provisions for changes, extract new legal nodes."""
    from extraction.pipeline import extract_single_provision
    from extraction.lex_client import get_provision

    api_key = os.environ.get("GOOGLE_AI_API_KEY", "")
    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY", "")

    # In production: query lex_provisions WHERE amendment_watch = true
    # For now: read from a watchlist file
    watchlist_path = Path("data/lex_watchlist.json")
    if not watchlist_path.exists():
        print("No watchlist found at data/lex_watchlist.json")
        print("Create one with: [{\"lex_id\": \"...\", \"domain\": \"...\", \"content_hash\": \"...\"}]")
        return

    with open(watchlist_path) as f:
        watchlist = json.load(f)

    run.input_count = len(watchlist)
    extracted = 0
    errors = 0

    for item in watchlist[:args.max]:
        lex_id = item["lex_id"]
        domain = item.get("domain", "housing")
        stored_hash = item.get("content_hash", "")

        print(f"\nChecking: {lex_id}")

        # Check for changes
        provision = get_provision(lex_id)
        if provision is None:
            print(f"  Could not fetch — skipping")
            errors += 1
            continue

        current_hash = hashlib.sha256(
            (provision.full_text or "").encode()
        ).hexdigest()

        if current_hash == stored_hash:
            print(f"  Unchanged — skipping")
            continue

        print(f"  Content changed — extracting")
        result = extract_single_provision(
            lex_id=lex_id,
            domain=domain,
            api_key=api_key,
            dry_run=args.dry_run,
        )

        if result["status"] == "extracted":
            extracted += len(result.get("nodes", []))
            # Update hash in watchlist
            item["content_hash"] = current_hash
        elif "error" in result["status"]:
            errors += 1
            print(f"  Error: {result.get('errors', ['unknown'])}")

    # Save updated watchlist
    if not args.dry_run:
        with open(watchlist_path, "w") as f:
            json.dump(watchlist, f, indent=2)

    run.complete(output_count=extracted, error_count=errors)
    print(f"\nLegal extraction: {extracted} nodes extracted, {errors} errors")


def run_structural_signals(args, run: AgentRun):
    """Daily: refresh structural signals on watched provisions. No LLM."""
    from extraction.lex_client import (
        get_provision,
        compute_structural_stability,
        derive_commencement_status,
    )

    watchlist_path = Path("data/lex_watchlist.json")
    if not watchlist_path.exists():
        print("No watchlist found")
        return

    with open(watchlist_path) as f:
        watchlist = json.load(f)

    run.input_count = len(watchlist)
    updated = 0

    for item in watchlist:
        lex_id = item["lex_id"]
        provision = get_provision(lex_id)
        if provision is None:
            continue

        old_stability = item.get("structural_stability")
        new_stability = compute_structural_stability(
            provision.amendment_count, provision.last_amended
        )
        new_status = derive_commencement_status(provision.commencement_status)

        if (new_stability != old_stability or
                new_status != item.get("commencement_status")):
            item["structural_stability"] = new_stability
            item["commencement_status"] = new_status
            item["in_degree"] = provision.in_degree
            item["amendment_count"] = provision.amendment_count
            item["last_checked"] = datetime.now(timezone.utc).date().isoformat()
            updated += 1

            if old_stability and new_stability != old_stability:
                print(f"  {lex_id}: stability {old_stability} -> {new_stability}")
                if new_stability == "LOW" and old_stability != "LOW":
                    print(f"    TRIGGER: re-extraction needed")

    if not args.dry_run:
        with open(watchlist_path, "w") as f:
            json.dump(watchlist, f, indent=2)

    run.complete(output_count=updated)
    print(f"\nStructural signals: {updated} provisions updated")


def run_local_data(args, run: AgentRun):
    """Per-cadence: refresh area_metrics from live APIs."""
    from extraction.data_sources import (
        resolve_postcode,
        get_crime_summary,
        cqc_ratings_summary,
        ons_list_datasets,
    )

    # Load postcodes to refresh (sample or full list)
    postcodes_path = Path("data/tracked_postcodes.json")
    if not postcodes_path.exists():
        print("No tracked postcodes at data/tracked_postcodes.json")
        print("Create one with: [\"SW1A 1AA\", \"BS1 1AA\", ...]")
        print("\nFalling back to ONS dataset listing check...")
        datasets = ons_list_datasets()
        print(f"  ONS API accessible: {len(datasets)} datasets available")
        for ds in datasets[:5]:
            print(f"    {ds.get('id', '?')}: {ds.get('title', '?')}")
        run.complete(output_count=0)
        return

    with open(postcodes_path) as f:
        postcodes = json.load(f)

    run.input_count = len(postcodes)
    metrics_collected = 0

    results = []
    for pc in postcodes[:args.max]:
        print(f"\n  Fetching: {pc}")
        geo = resolve_postcode(pc)
        if not geo:
            print(f"    Could not resolve")
            continue

        print(f"    {geo.la_name} / {geo.constituency_name} / {geo.country}")

        row = {
            "postcode": pc,
            "la_code": geo.la_code,
            "la_name": geo.la_name,
            "ward_code": geo.ward_code,
            "constituency_code": geo.constituency_code,
            "country": geo.country,
            "metrics": {},
        }

        # Crime data
        if geo.latitude and geo.longitude:
            crimes = get_crime_summary(geo.latitude, geo.longitude)
            total = sum(crimes.values())
            row["metrics"]["crime_total_rate"] = {
                "value": total,
                "breakdown": crimes,
                "source": "police.uk",
            }
            metrics_collected += 1
            print(f"    Crime: {total} incidents nearby")

        # CQC
        if geo.la_name:
            ratings = cqc_ratings_summary(geo.la_name)
            if ratings:
                total_homes = sum(ratings.values())
                good = ratings.get("Good", 0) + ratings.get("Outstanding", 0)
                pct = round(100 * good / total_homes, 1) if total_homes else 0
                row["metrics"]["council_cqc_good"] = {
                    "value": pct,
                    "total": total_homes,
                    "source": "cqc",
                }
                metrics_collected += 1
                print(f"    CQC: {pct}% Good/Outstanding ({total_homes} homes)")

        results.append(row)

    # Save results
    if not args.dry_run and results:
        output_path = Path("data/local_metrics_latest.json")
        output_path.parent.mkdir(exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nSaved to {output_path}")

    run.complete(output_count=metrics_collected)
    print(f"\nLocal data: {metrics_collected} metrics across {len(results)} postcodes")


def run_evidence(args, run: AgentRun):
    """Weekly: check for new statistical releases and extract."""
    print("Evidence agent: checking release calendars")
    print("  Would monitor: ONS release calendar, DWP publications, NHS stats")
    print("  Not yet connected — stub for now")
    run.complete(output_count=0)


def run_parliamentary(args, run: AgentRun):
    """Daily: monitor parliament-mcp for new bills and Hansard."""
    print("Parliamentary agent: checking parliament-mcp")
    print("  Would monitor: new bills, Hansard debates, committee reports")
    print("  Requires parliament-mcp access — stub for now")
    run.complete(output_count=0)


AGENT_RUNNERS = {
    "legal_extraction": run_legal_extraction,
    "structural_signals": run_structural_signals,
    "local_data": run_local_data,
    "evidence": run_evidence,
    "parliamentary": run_parliamentary,
}


def main():
    parser = argparse.ArgumentParser(description="Run a BASIS extraction agent")
    parser.add_argument("agent", choices=list(AGENT_RUNNERS.keys()))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--domain", default=None)
    parser.add_argument("--max", type=int, default=50)
    args = parser.parse_args()

    config = AGENTS.get(args.agent)
    if config and not config.enabled:
        print(f"Agent '{args.agent}' is disabled")
        sys.exit(0)

    run = AgentRun(
        agent_type=args.agent,
        run_id=f"{args.agent}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
    )
    run.start()

    print(f"{'='*60}")
    print(f"Agent: {args.agent}")
    if config:
        print(f"Model: {config.model or 'none'}")
        print(f"Schedule: {config.schedule}")
    print(f"Run ID: {run.run_id}")
    if args.dry_run:
        print("MODE: DRY RUN")
    print(f"{'='*60}\n")

    runner = AGENT_RUNNERS[args.agent]
    runner(args, run)

    print(f"\n{'='*60}")
    print(f"Run complete: {run.output_count} outputs, {run.error_count} errors")
    print(f"Duration: {run.started_at} -> {run.completed_at}")

    # Save run log
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    with open(logs_dir / f"{run.run_id}.json", "w") as f:
        json.dump(run.to_dict(), f, indent=2)


if __name__ == "__main__":
    main()
