"""
lex_client.py — Client for i.AI Lex API.

Lex API: 220K Acts and SIs, 892K amendments, 89K explanatory notes.
Free. 1,000 requests/hour. MCP server available.

This client handles both direct REST and MCP access patterns.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import requests

LEX_API_BASE = "https://lex.lab.i.ai.gov.uk"
LEX_MCP_URL = "https://lex.lab.i.ai.gov.uk/mcp"

# Rate limiting: 1000 req/hr = ~1 req/3.6s to be safe
REQUEST_DELAY = 1.0
_last_request_time = 0.0


def _rate_limit():
    global _last_request_time
    now = time.time()
    elapsed = now - _last_request_time
    if elapsed < REQUEST_DELAY:
        time.sleep(REQUEST_DELAY - elapsed)
    _last_request_time = time.time()


@dataclass
class LexProvision:
    """A provision from Lex Graph."""
    lex_id: str
    title: str
    full_text: str | None = None
    explanatory_note: str | None = None
    act_title: str | None = None
    section: str | None = None
    # Structural signals
    in_degree: int | None = None
    amendment_count: int | None = None
    last_amended: str | None = None
    commencement_status: str | None = None
    citing_acts: list[str] = field(default_factory=list)


@dataclass
class LexSearchResult:
    """Search result from Lex API."""
    provisions: list[LexProvision]
    total: int
    query: str


def search_provisions(
    query: str,
    limit: int = 20,
) -> LexSearchResult:
    """
    Search Lex API for provisions matching a query.
    Supports semantic and exact search.
    """
    _rate_limit()

    try:
        resp = requests.get(
            f"{LEX_API_BASE}/api/search",
            params={"q": query, "limit": limit},
            timeout=15,
        )

        if resp.status_code != 200:
            print(f"Lex search error: {resp.status_code}")
            return LexSearchResult(provisions=[], total=0, query=query)

        data = resp.json()
        provisions = []
        for item in data.get("results", []):
            provisions.append(LexProvision(
                lex_id=item.get("id", ""),
                title=item.get("title", ""),
                full_text=item.get("text"),
                act_title=item.get("act_title"),
                section=item.get("section"),
            ))

        return LexSearchResult(
            provisions=provisions,
            total=data.get("total", len(provisions)),
            query=query,
        )

    except requests.exceptions.RequestException as e:
        print(f"Lex search failed: {e}")
        return LexSearchResult(provisions=[], total=0, query=query)


def get_provision(lex_id: str) -> LexProvision | None:
    """Fetch a single provision by Lex ID."""
    _rate_limit()

    try:
        resp = requests.get(
            f"{LEX_API_BASE}/api/provision/{lex_id}",
            timeout=15,
        )

        if resp.status_code != 200:
            return None

        data = resp.json()
        return LexProvision(
            lex_id=data.get("id", lex_id),
            title=data.get("title", ""),
            full_text=data.get("text"),
            explanatory_note=data.get("explanatory_note"),
            act_title=data.get("act_title"),
            section=data.get("section"),
            in_degree=data.get("in_degree"),
            amendment_count=data.get("amendment_count"),
            last_amended=data.get("last_amended"),
            commencement_status=data.get("commencement_status"),
            citing_acts=data.get("citing_acts", []),
        )

    except requests.exceptions.RequestException as e:
        print(f"Lex provision fetch failed: {e}")
        return None


def get_explanatory_note(lex_id: str) -> str | None:
    """Fetch explanatory note for a provision if available."""
    _rate_limit()

    try:
        resp = requests.get(
            f"{LEX_API_BASE}/api/provision/{lex_id}/explanatory_note",
            timeout=15,
        )

        if resp.status_code == 200:
            data = resp.json()
            return data.get("text")
        return None

    except requests.exceptions.RequestException:
        return None


def ego_network(
    anchor_id: str,
    hops: int = 2,
    edge_types: list[str] | None = None,
) -> list[LexProvision]:
    """
    SCHEMA-022: Ego network query from an anchor provision.
    Returns all provisions reachable within `hops` via citation/amendment edges.

    Used for corpus scoping per domain.
    """
    _rate_limit()

    params: dict[str, Any] = {
        "anchor": anchor_id,
        "hops": hops,
    }
    if edge_types:
        params["edge_types"] = ",".join(edge_types)

    try:
        resp = requests.get(
            f"{LEX_API_BASE}/api/ego_network",
            params=params,
            timeout=30,
        )

        if resp.status_code != 200:
            print(f"Ego network query failed: {resp.status_code}")
            return []

        data = resp.json()
        provisions = []
        for item in data.get("provisions", []):
            provisions.append(LexProvision(
                lex_id=item.get("id", ""),
                title=item.get("title", ""),
                full_text=item.get("text"),
                act_title=item.get("act_title"),
                section=item.get("section"),
                in_degree=item.get("in_degree"),
                amendment_count=item.get("amendment_count"),
            ))

        return provisions

    except requests.exceptions.RequestException as e:
        print(f"Ego network query failed: {e}")
        return []


def check_amendment(lex_id: str, stored_hash: str) -> bool:
    """
    Check if a provision's content has changed since last extraction.
    Returns True if content_hash differs (amendment detected).
    """
    import hashlib

    provision = get_provision(lex_id)
    if provision is None or provision.full_text is None:
        return False

    current_hash = hashlib.sha256(provision.full_text.encode()).hexdigest()
    return current_hash != stored_hash


def compute_structural_stability(
    amendment_count: int | None,
    last_amended: str | None,
) -> str:
    """
    Derive structural_stability from amendment history.
    HIGH = untouched >10yrs; MEDIUM = amended 1-3 times; LOW = amended >3 times in 5yrs
    """
    if amendment_count is None:
        return "MEDIUM"  # conservative default

    if amendment_count == 0:
        return "HIGH"

    # Simple heuristic without date parsing
    if amendment_count <= 3:
        return "MEDIUM"
    else:
        return "LOW"


def derive_commencement_status(raw_status: str | None) -> str:
    """Map Lex Graph's commencement data to SCHEMA-011 six-value enum."""
    if raw_status is None:
        return "unknown"

    status_lower = raw_status.lower()

    if "repeal" in status_lower and "prospective" in status_lower:
        return "prospectively_repealed"
    elif "repeal" in status_lower:
        return "repealed"
    elif "not commenced" in status_lower or "not in force" in status_lower:
        return "not_commenced"
    elif "partial" in status_lower:
        return "partially_in_force"
    elif "in force" in status_lower or "commenced" in status_lower:
        return "in_force"
    else:
        return "unknown"
