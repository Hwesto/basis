"""
google_ai_client.py — Working client for Gemma 4 and Gemini Flash.

Handles:
  - Pydantic-constrained extraction via Gemma 4 26B MoE
  - Cross-check via Gemini Flash
  - Explanatory note validation via Gemini Flash (cheap)
  - Model availability check

Free tier: 1K requests/day for Gemma, generous for Flash.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any

import requests

API_KEY = os.environ.get("GOOGLE_AI_API_KEY", "")
BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

# Model identifiers — check availability with list_models()
GEMMA_MODEL = "gemma-3-27b-it"  # closest available; update when Gemma 4 lands
FLASH_MODEL = "gemini-2.0-flash"

# Rate limiting
REQUEST_DELAY = 0.1  # seconds between requests
_last_request_time = 0.0


def _rate_limit():
    """Simple rate limiter."""
    global _last_request_time
    now = time.time()
    elapsed = now - _last_request_time
    if elapsed < REQUEST_DELAY:
        time.sleep(REQUEST_DELAY - elapsed)
    _last_request_time = time.time()


@dataclass
class AIResponse:
    """Standardised response from any model call."""
    text: str
    model: str
    usage: dict | None = None
    raw: dict | None = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None

    def parse_json(self) -> dict | None:
        """Try to parse response as JSON."""
        try:
            # Strip markdown fences if present
            clean = self.text.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[1]
                if clean.endswith("```"):
                    clean = clean[:-3]
            return json.loads(clean)
        except (json.JSONDecodeError, IndexError):
            return None


def list_models(key: str | None = None) -> list[dict]:
    """List available models. Useful for checking Gemma 4 availability."""
    api_key = key or API_KEY
    resp = requests.get(
        f"{BASE_URL}/models",
        params={"key": api_key},
        timeout=10,
    )
    if resp.status_code != 200:
        print(f"Error listing models: {resp.status_code} {resp.text[:200]}")
        return []
    data = resp.json()
    return data.get("models", [])


def generate(
    prompt: str,
    model: str = FLASH_MODEL,
    system: str | None = None,
    response_schema: dict | None = None,
    response_mime_type: str | None = None,
    temperature: float = 0.1,
    max_tokens: int = 4096,
    key: str | None = None,
) -> AIResponse:
    """
    Call Google AI generateContent endpoint.

    For Pydantic-constrained extraction:
        response_mime_type = "application/json"
        response_schema = YourModel.model_json_schema()

    This guarantees schema-conformant output — violations fail the call.
    """
    api_key = key or API_KEY
    if not api_key:
        return AIResponse(text="", model=model, error="No API key set")

    _rate_limit()

    url = f"{BASE_URL}/models/{model}:generateContent"

    # Build request body
    contents = [{"parts": [{"text": prompt}]}]

    generation_config: dict[str, Any] = {
        "temperature": temperature,
        "maxOutputTokens": max_tokens,
    }

    if response_mime_type:
        generation_config["responseMimeType"] = response_mime_type
    if response_schema:
        generation_config["responseSchema"] = response_schema

    body: dict[str, Any] = {
        "contents": contents,
        "generationConfig": generation_config,
    }

    if system:
        body["systemInstruction"] = {
            "parts": [{"text": system}]
        }

    try:
        resp = requests.post(
            url,
            params={"key": api_key},
            json=body,
            timeout=60,
        )

        if resp.status_code != 200:
            return AIResponse(
                text="",
                model=model,
                error=f"HTTP {resp.status_code}: {resp.text[:500]}",
                raw=resp.json() if resp.headers.get("content-type", "").startswith("application/json") else None,
            )

        data = resp.json()
        candidates = data.get("candidates", [])
        if not candidates:
            return AIResponse(
                text="",
                model=model,
                error="No candidates in response",
                raw=data,
            )

        # Extract text from first candidate
        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts)

        usage = data.get("usageMetadata")

        return AIResponse(
            text=text,
            model=model,
            usage=usage,
            raw=data,
        )

    except requests.exceptions.Timeout:
        return AIResponse(text="", model=model, error="Request timed out")
    except requests.exceptions.ConnectionError as e:
        return AIResponse(text="", model=model, error=f"Connection error: {e}")
    except Exception as e:
        return AIResponse(text="", model=model, error=f"Unexpected error: {e}")


# ---------------------------------------------------------------------------
# High-level extraction functions
# ---------------------------------------------------------------------------

def extract_legal_nodes(
    provision_text: str,
    lex_provision_id: str,
    domain: str,
    jurisdiction: str = "england_and_wales",
    explanatory_note: str | None = None,
    response_schema: dict | None = None,
    key: str | None = None,
) -> AIResponse:
    """
    Extract Hohfeldian legal nodes from a provision using Gemma.
    Uses Pydantic schema constraint for guaranteed conformant output.
    """
    from extraction.prompts import GEMMA_LEGAL_EXTRACTION

    prompt = GEMMA_LEGAL_EXTRACTION.format(
        provision_text=provision_text,
        explanatory_note=explanatory_note or "(not available)",
        lex_provision_id=lex_provision_id,
        domain=domain,
        jurisdiction=jurisdiction,
    )

    return generate(
        prompt=prompt,
        model=GEMMA_MODEL,
        response_mime_type="application/json" if response_schema else None,
        response_schema=response_schema,
        temperature=0.1,
        key=key,
    )


def cross_check(
    provision_text: str,
    extracted_json: dict,
    explanatory_note: str | None = None,
    key: str | None = None,
) -> AIResponse:
    """
    Gemini Flash cross-check: does the extraction match the provision?
    Returns PASS or FAIL: [reason].
    Cost: ~$0.001/check.
    """
    from extraction.prompts import FLASH_CROSS_CHECK

    prompt = FLASH_CROSS_CHECK.format(
        provision_text=provision_text,
        explanatory_note=explanatory_note or "(not available)",
        extracted_json=json.dumps(extracted_json, indent=2),
    )

    return generate(
        prompt=prompt,
        model=FLASH_MODEL,
        temperature=0.0,
        max_tokens=200,
        key=key,
    )


def validate_against_note(
    explanatory_note: str,
    extracted_json: dict,
    key: str | None = None,
) -> AIResponse:
    """
    Cheap validation: does the extraction match the explanatory note?
    Uses Flash (cheapest available).
    """
    from extraction.prompts import HAIKU_NOTE_VALIDATION

    prompt = HAIKU_NOTE_VALIDATION.format(
        explanatory_note=explanatory_note,
        extracted_json=json.dumps(extracted_json, indent=2),
    )

    return generate(
        prompt=prompt,
        model=FLASH_MODEL,
        temperature=0.0,
        max_tokens=100,
        key=key,
    )


def classify_node_types(
    source_type: str,
    title: str,
    domain: str,
    key: str | None = None,
) -> list[str]:
    """
    Cheap classification: what node types should we extract from this source?
    """
    from extraction.prompts import HAIKU_CLASSIFY_NODE_TYPE

    prompt = HAIKU_CLASSIFY_NODE_TYPE.format(
        source_type=source_type,
        title=title,
        domain=domain,
    )

    resp = generate(
        prompt=prompt,
        model=FLASH_MODEL,
        response_mime_type="application/json",
        temperature=0.0,
        max_tokens=100,
        key=key,
    )

    if resp.ok:
        parsed = resp.parse_json()
        if isinstance(parsed, list):
            return parsed
    return ["FACT", "ASSUMPTION"]  # safe default
