"""
Runs the full test-case matrix against a running backend (localhost:8000 by
default) and flags anomalies automatically - including regressions of the
two bugs already found (markdown-in-text instead of structured table/chart,
and duplicate/fan-out rows).

Setup:
    pip install requests

Run (backend must already be running):
    python test_queries.py
"""

import requests
import uuid
import json

BASE_URL = "http://localhost:8000"

# (persona, question, expected_type) - expected_type is a hint for the
# report, not a hard assertion, since the agent can reasonably choose
# text vs table for borderline cases.
TEST_CASES = [
    ("inventory_manager", "Which items are below their min stock level?", "text_or_table"),
    ("inventory_manager", "Which locations hold the most stock value?", "chart"),
    ("inventory_manager", "What moved in and out of stock in the last 30 days?", "table"),
    ("inventory_manager", "How many active inventory locations do we have?", "text"),
    ("procurement_manager", "Which POs are pending receipt?", "table"),
    ("procurement_manager", "Show vendor-wise total PO value", "chart"),
    ("procurement_manager", "Any PO line items with a quantity mismatch on receipt?", "table"),
    ("procurement_manager", "What payment tranches are due soon?", "table"),
    ("owner", "What's our total procurement spend this year?", "text"),
    ("owner", "Give me a quick health check on inventory and procurement", "text"),
    ("owner", "Which vendors are we most dependent on by spend?", "chart"),
]

TRUNCATION_PHRASES = ["and more", "...", "etc.", "for brevity"]


def check_anomalies(resp: dict) -> list[str]:
    issues = []
    text = (resp.get("text") or "").lower()
    rtype = resp.get("response_type")

    # Regression check: markdown table stuffed into `text`
    if rtype == "text" and ("|---" in text or text.count("\n|") > 1 or text.count("\n1.") > 0):
        issues.append("possible markdown/list-in-text regression (should be response_type=table)")

    # Regression check: silent truncation language
    if any(p in text for p in TRUNCATION_PHRASES):
        issues.append(f"possible silent truncation language in text: {text[:80]!r}")

    # table/chart declared but empty
    if rtype == "table" and not resp.get("table"):
        issues.append("response_type=table but table field is empty/null")
    if rtype == "chart" and not resp.get("chart"):
        issues.append("response_type=chart but chart field is empty/null")

    # Duplicate-row check (the fan-out bug found earlier)
    if rtype == "table" and resp.get("table"):
        rows = resp["table"]
        if rows and "id" in rows[0]:
            ids = [r.get("id") for r in rows]
            if len(ids) != len(set(ids)):
                issues.append(f"duplicate rows detected by id ({len(ids)} rows, {len(set(ids))} unique ids)")

    return issues


def main():
    results = []
    for persona, question, expected in TEST_CASES:
        thread_id = f"autotest-{uuid.uuid4()}"
        try:
            r = requests.post(
                f"{BASE_URL}/chat",
                json={"message": question, "persona": persona, "thread_id": thread_id},
                timeout=60,
            )
            r.raise_for_status()
            data = r.json()
            issues = check_anomalies(data)
            results.append((persona, question, expected, data["response_type"], issues, None))
        except Exception as e:
            results.append((persona, question, expected, None, [], str(e)))

    print("\n" + "=" * 70)
    print("TEST RESULTS")
    print("=" * 70)
    clean, flagged, errored = 0, 0, 0
    for persona, question, expected, actual_type, issues, error in results:
        print(f"\n[{persona}] {question}")
        if error:
            print(f"  ERROR: {error}")
            errored += 1
            continue
        print(f"  expected~{expected} | got={actual_type}")
        if issues:
            flagged += 1
            for issue in issues:
                print(f"  ⚠️  {issue}")
        else:
            clean += 1
            print("  ✅ no anomalies detected")

    print("\n" + "=" * 70)
    print(f"SUMMARY: {clean} clean, {flagged} flagged, {errored} errored, {len(results)} total")
    print("=" * 70)


if __name__ == "__main__":
    main()
