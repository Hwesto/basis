#!/usr/bin/env python3
"""
check_links.py — Weekly dead link check on all source URLs.

Checks all URLs in sources data. Reports dead links with status codes.
Writes report to reports/link_check.json.
"""

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    print("requests not installed. Run: pip install requests")
    sys.exit(1)


TIMEOUT = 10
DELAY = 0.5  # be polite


def load_sources() -> list[dict]:
    """Load sources from data directory."""
    sources = []
    data_dir = Path("data")
    for pattern in ["sources/*.json", "sources.json", "**/sources*.json"]:
        for f in data_dir.glob(pattern):
            try:
                with open(f) as fh:
                    data = json.load(fh)
                    if isinstance(data, list):
                        sources.extend(data)
                    elif isinstance(data, dict):
                        sources.append(data)
            except (json.JSONDecodeError, KeyError):
                continue
    return sources


def check_url(url: str) -> dict:
    """Check a single URL. Returns status info."""
    try:
        resp = requests.head(url, timeout=TIMEOUT, allow_redirects=True)
        return {
            "url": url,
            "status": resp.status_code,
            "ok": resp.status_code < 400,
            "redirected_to": str(resp.url) if resp.url != url else None,
        }
    except requests.exceptions.Timeout:
        return {"url": url, "status": "timeout", "ok": False}
    except requests.exceptions.ConnectionError:
        return {"url": url, "status": "connection_error", "ok": False}
    except Exception as e:
        return {"url": url, "status": str(e), "ok": False}


def main():
    report_mode = "--report" in sys.argv

    sources = load_sources()
    urls = set()
    for s in sources:
        url = s.get("url")
        if url and url.startswith("http"):
            urls.add(url)
        methodology = s.get("methodology_url")
        if methodology and methodology.startswith("http"):
            urls.add(methodology)

    if not urls:
        print("No URLs found in sources.")
        sys.exit(0)

    print(f"Checking {len(urls)} URLs...\n")

    results = []
    dead = []
    for i, url in enumerate(sorted(urls), 1):
        result = check_url(url)
        results.append(result)
        status = "OK" if result["ok"] else f"DEAD ({result['status']})"
        print(f"  [{i}/{len(urls)}] {status}: {url}")
        if not result["ok"]:
            dead.append(result)
        time.sleep(DELAY)

    print(f"\nResults: {len(results) - len(dead)}/{len(results)} OK, {len(dead)} dead")

    if report_mode or dead:
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)
        report = {
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "total": len(results),
            "ok": len(results) - len(dead),
            "dead": len(dead),
            "dead_urls": dead,
            "all_results": results,
        }
        with open(reports_dir / "link_check.json", "w") as f:
            json.dump(report, f, indent=2)
        print(f"Report written to reports/link_check.json")

    # Exit non-zero only if >20% dead (transient errors shouldn't block)
    if dead and len(dead) / len(results) > 0.2:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
