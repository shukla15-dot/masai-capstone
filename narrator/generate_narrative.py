"""
Part 3 — GenAI-Powered Insight Narrator (30 marks)
Mamaearth Returns & Growth Intelligence Pipeline.

Turns the verified Part 1 + Part 2 numbers (narrator/findings.json, written by code
at the end of analysis/clean_and_eda.py) into an SCR (Situation-Complication-
Resolution) business narrative for regional ops and finance heads.

Two paths, same return-dict shape:
  * ONLINE  — Gemini via the google-genai client (needs a free Google AI Studio key
              in the GEMINI_API_KEY env var).
  * OFFLINE — a fully deterministic, keyless template. Runs with zero configuration
              and zero network, so the pipeline is always gradable.

The orchestrator uses the online path only when a key is set AND the call succeeds;
otherwise it falls back to offline. A numeric-accuracy checker then confirms the five
key figures survived into the narrative.

Run:
  # offline (no key needed):
  python narrator/generate_narrative.py
  # online (PowerShell):   $env:GEMINI_API_KEY = "your-free-key"; python narrator/generate_narrative.py
  # online (bash):         GEMINI_API_KEY=your-free-key python narrator/generate_narrative.py
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")  # clean em-dashes on a cp1252 console
except (AttributeError, ValueError):
    pass

REPO_ROOT = Path(__file__).resolve().parent.parent

# Load a local .env (repo root) if python-dotenv is installed, so GEMINI_API_KEY can
# live in a git-ignored .env file instead of being exported every shell session.
# Optional by design: the offline path needs neither this package nor any .env.
try:
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env")
except ImportError:
    pass

FINDINGS_PATH = REPO_ROOT / "narrator" / "findings.json"
SAMPLE_OUTPUT_PATH = REPO_ROOT / "narrator" / "sample_output.txt"

# Model is configurable; defaults to the free flash-lite tier taught in the course.
MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def load_findings():
    with open(FINDINGS_PATH, encoding="utf-8") as f:
        return json.load(f)


def month_name(year_month):
    """'2026-03' -> 'March 2026'."""
    return datetime.strptime(year_month, "%Y-%m").strftime("%B %Y")


# ---------------------------------------------------------------------------
# Task 2 + Task 3 — online Gemini path with locked parameters & error handling
# ---------------------------------------------------------------------------
def generate_scr_narrative(findings: dict) -> dict:
    """Generate the SCR narrative with Gemini.

    Returns a structured dict in BOTH branches so the caller never sees a raw
    exception:
      success -> {"status": "success", "narrative": str, "tokens": int}
      failure -> {"status": "error",   "narrative": None, "message": str}
    """
    # System instruction is kept separate from the user prompt: it fixes the role,
    # the required 3-section structure, and the no-invented-numbers constraint.
    system_instruction = (
        "You are a senior data analyst writing for Mamaearth's regional ops and "
        "finance heads. Write a concise business narrative with EXACTLY three "
        "sections, each on its own line and labeled in capitals: SITUATION, "
        "COMPLICATION, RESOLUTION. "
        "Every number you state MUST come from the supplied findings and appear "
        "with the same value — never invent, round differently, or add statistics "
        "that are not in the findings. Keep it to about 250 words, plain prose, no "
        "bullet lists."
    )

    # The user prompt is BUILT FROM the findings dict (interpolated, not hardcoded),
    # so a different findings.json yields a different narrative with no code change.
    user_prompt = (
        "Write the SCR narrative using only these verified findings (JSON):\n\n"
        f"{json.dumps(findings, indent=2)}\n\n"
        "Guidance: the Situation covers cleaned vs raw revenue and the duplicate-driven "
        "reconciliation delta; the Complication covers return rates by payment method and "
        "the single highest-risk payment x city-tier segment; the Resolution covers the "
        "outlier-corrected true peak month and the recommended actions. Use INR for money."
    )

    try:
        # Imported lazily so the offline path needs neither the library nor a key.
        from google import genai
        from google.genai import types

        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("No GEMINI_API_KEY / GOOGLE_API_KEY set in the environment.")

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=MODEL,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                # temperature 0.0: this is a factual business report, not creative
                # writing — we want the most deterministic, grounded output.
                temperature=0.0,
                # Explicit, generous token budget (brief requires >= 300; the taught
                # pitfall is that too low a cap truncates the narrative).
                max_output_tokens=1024,
                # Timeout in MILLISECONDS (taught Gemini minimum is 10000 = 10s).
                http_options=types.HttpOptions(timeout=30000),
            ),
        )
        return {
            "status": "success",
            "narrative": response.text,
            "tokens": response.usage_metadata.total_token_count,
        }
    except Exception as err:  # noqa: BLE001 — caller must never receive a raw exception
        return {"status": "error", "narrative": None, "message": str(err)}


# ---------------------------------------------------------------------------
# Task 4 — offline, keyless fallback (fully deterministic)
# ---------------------------------------------------------------------------
def generate_scr_narrative_offline(findings: dict) -> dict:
    """Deterministic SCR narrative built from an f-string template over findings.

    No network, no API key, no third-party import. Same return-dict shape as the
    online path, and guaranteed to contain all five required figures (Task 5).
    """
    cleaned = findings["cleaned_total_revenue_inr"]
    raw = findings["raw_total_revenue_inr"]
    delta = findings["duplicate_reconciliation_delta_inr"]
    rr = findings["return_rate_by_payment"]
    seg = findings["highest_risk_segment"]
    peak = findings["true_peak_month"]
    inflated = findings["outlier_inflated_month"]

    peak_name = month_name(peak["month"])
    inflated_name = month_name(inflated["month"])

    narrative = (
        "SITUATION\n"
        f"After cleaning the order book, Mamaearth's net revenue over the window stands at "
        f"INR {cleaned:,.2f}. The raw, uncleaned ledger overstated this by INR {delta:,.2f} "
        f"(reporting INR {raw:,.2f}): exactly the combined value of five double-submitted "
        f"duplicate orders that were removed. The cleaned figure of INR {cleaned:,.2f} is the "
        f"number finance should carry forward.\n\n"
        "COMPLICATION\n"
        f"Returns are not spread evenly across payment methods. Cash-on-Delivery (COD) orders "
        f"are returned at {rr['COD']}%, versus {rr['UPI']}% for UPI and {rr['CARD']}% for Card — "
        f"roughly three times the Card rate. The risk concentrates further by geography: "
        f"{seg['payment_method']} orders placed from Tier-{seg['city_tier']} cities are returned at "
        f"{seg['return_rate_pct']}%, the single highest-risk segment in the business. A blended "
        f"company-wide return rate would have hidden this pocket entirely.\n\n"
        "RESOLUTION\n"
        f"Two actions follow. First, tighten COD in Tier-{seg['city_tier']} cities — through prepaid "
        f"incentives, order-confirmation calls, or COD caps — where the {seg['return_rate_pct']}% "
        f"return rate is eroding margin fastest. Second, correct the revenue calendar: once the two "
        f"bulk-order outliers are excluded, {peak_name} is the true peak month at "
        f"INR {peak['revenue_inr']:,.2f}, not {inflated_name} (whose apparent "
        f"INR {inflated['apparent_revenue_inr']:,.2f} collapses to INR "
        f"{inflated['corrected_revenue_inr']:,.2f} once the outliers are removed). Plan inventory "
        f"and regional campaigns around the real {peak_name.split()[0]} peak."
    )
    return {"status": "success", "narrative": narrative, "tokens": 0}


# ---------------------------------------------------------------------------
# Orchestrator — online when possible, offline otherwise
# ---------------------------------------------------------------------------
def generate_narrative(findings: dict) -> dict:
    """Use the online Gemini path when a key is set and the call succeeds; else fall
    back to the deterministic offline path. The returned dict carries a 'source' key.
    """
    has_key = bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))
    if has_key:
        result = generate_scr_narrative(findings)
        if result["status"] == "success" and result["narrative"]:
            result["source"] = "online-gemini"
            return result
        print(f"[warn] online Gemini path failed, falling back to offline: "
              f"{result.get('message', 'empty response')}")

    result = generate_scr_narrative_offline(findings)
    result["source"] = "offline-template"
    return result


# ---------------------------------------------------------------------------
# Task 5 — numeric accuracy checklist
# ---------------------------------------------------------------------------
def check_numeric_accuracy(narrative_text: str) -> bool:
    """Confirm all five required figures appear in the narrative. Prints a pass/fail
    line per figure and returns True only if every figure is present.

    Commas are stripped before matching so '97,358.30' and '97358.30' both match.
    """
    normalized = narrative_text.replace(",", "")

    checks = [
        ("Cleaned total revenue (97,358.30)", lambda t: "97358.3" in t),
        ("COD return rate (44.4)",            lambda t: "44.4" in t),
        ("COD+Tier-2 segment rate (54.5)",    lambda t: "54.5" in t),
        ("Reconciliation delta (2,501.90)",   lambda t: "2501.9" in t),
        ("True peak month (March 20,318.90)", lambda t: ("March" in narrative_text) and ("20318.9" in t)),
    ]

    print("\nNumeric accuracy check:")
    all_pass = True
    for label, test in checks:
        ok = test(normalized)
        all_pass = all_pass and ok
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}")
    print(f"Overall: {'ALL FIGURES PRESENT' if all_pass else 'MISSING FIGURE(S)'}")
    return all_pass


# ---------------------------------------------------------------------------
def main():
    findings = load_findings()
    result = generate_narrative(findings)

    print("=" * 78)
    print(f"SCR NARRATIVE  (source: {result['source']}, tokens: {result['tokens']})")
    print("=" * 78)
    print(result["narrative"])

    # Save the produced narrative, then run the checker against the SAVED file —
    # the grader verifies the saved sample, not a live API call (Task 5).
    SAMPLE_OUTPUT_PATH.write_text(result["narrative"], encoding="utf-8")
    print(f"\nwrote {SAMPLE_OUTPUT_PATH}")

    saved = SAMPLE_OUTPUT_PATH.read_text(encoding="utf-8")
    passed = check_numeric_accuracy(saved)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
