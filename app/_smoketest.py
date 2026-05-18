"""Smoke test for the Flask app - verifies endpoints work end-to-end.

Run from the repo root: python -m app._smoketest
"""

from __future__ import annotations

import json
import sys
import os

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from app.backend.app import app  # noqa: E402


def main() -> None:
    client = app.test_client()

    # /api/status
    r = client.get("/api/status")
    print("status:", r.status_code, json.dumps(r.get_json(), indent=2)[:500])

    # /api/sample
    r = client.get("/api/sample?split=test&index=0")
    sample = r.get_json()
    assert r.status_code == 200, sample
    print("\nsample id:", sample["id"], "category:", sample["category"])
    print("article (first 120):", sample["article"][:120])
    print("gold    (first 120):", sample["gold_summary"][:120])

    # /api/summarize textrank
    r = client.post(
        "/api/summarize",
        data=json.dumps({
            "text": sample["article"],
            "model": "textrank",
            "num_sentences": 3,
            "reference": sample["gold_summary"],
        }),
        content_type="application/json",
    )
    body = r.get_json()
    print("\nTEXTRANK status:", r.status_code)
    print("summary (200 char):", (body.get("summary") or "")[:200])
    print("rouge:", body.get("rouge"))
    print("stats:", body.get("stats"))
    assert r.status_code == 200, body

    # /api/summarize seq2seq (expect 503 because no checkpoint yet)
    r = client.post(
        "/api/summarize",
        data=json.dumps({"text": sample["article"], "model": "seq2seq"}),
        content_type="application/json",
    )
    print("\nSEQ2SEQ status:", r.status_code, "->", r.get_json())

    # /api/summarize gemini (expect 503 because no API key)
    r = client.post(
        "/api/summarize",
        data=json.dumps({"text": sample["article"], "model": "gemini"}),
        content_type="application/json",
    )
    print("\nGEMINI status:", r.status_code, "->", r.get_json())

    print("\nOK - smoke test passed.")


if __name__ == "__main__":
    main()
