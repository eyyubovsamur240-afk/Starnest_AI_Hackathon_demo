"""Run every ticket in data/tickets.json through the copilot and score it.

Each ticket's "expected" block is the hand-written answer key. It is only read here,
after the analysis, to score the result; it is never sent to Gemini or shown in the app.
Category, churn risk, sentiment and bot-failure reason are decided by Gemini (or by the
keyword rules with --offline) from the chat text alone.

Usage:
    python eval.py               # Gemini (needs GEMINI_API_KEY) -> results/eval_llm.*
    python eval.py --limit 5     # quick Gemini smoke run on the first 5 tickets
    python eval.py --offline     # keyword-rule baseline, no API -> results/eval_offline.*

Writes results/eval_<mode>.json and results/eval_<mode>.md (the table for the pitch slide).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from copilot import MODEL, analyze, llm_available

ROOT = Path(__file__).parent

# Paid-tier list price of gemini-2.5-flash in USD per 1M tokens (thinking tokens bill as output).
# Check https://ai.google.dev/pricing before quoting; the free tier used for the demo costs nothing.
PRICE_IN_PER_M = 0.30
PRICE_OUT_PER_M = 2.50


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true", help="use the keyword baseline instead of the LLM")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    if not args.offline and not llm_available():
        raise SystemExit(
            "GEMINI_API_KEY is not set, so Gemini cannot be evaluated.\n"
            '  PowerShell:  $env:GEMINI_API_KEY="your-key"   then   python eval.py\n'
            "  Or run the keyword-rule baseline on purpose:  python eval.py --offline"
        )
    decided_by = "keyword rules (offline)" if args.offline else f"Gemini ({MODEL})"
    print(f"Decided by: {decided_by}. The expected values are only used to score the results.\n")

    tickets = json.loads((ROOT / "data" / "tickets.json").read_text(encoding="utf-8"))[: args.limit]
    rows = []
    for t in tickets:
        try:
            res = analyze(t["chat"], force_offline=args.offline, known_names=[t["customer"]["name"]])
        except Exception as exc:  # keep going so one API error doesn't kill the run
            print(f"{t['id']}: ERROR {exc}")
            rows.append({"id": t["id"], "error": str(exc), "expected": t["expected"]})
            continue
        a, label = res.analysis, t["expected"]
        row = {
            "id": t["id"],
            "note": t.get("note", ""),
            "expected": label,
            "predicted": {"category": a.category, "churn_risk": a.churn_risk, "sentiment": a.sentiment, "bot_failure": a.bot_failure},
            "category_ok": a.category == label["category"],
            "risk_ok": a.churn_risk == label["churn_risk"],
            "sentiment_within_1": abs(a.sentiment - label["sentiment"]) <= 1,
            "failure_ok": a.bot_failure == label["bot_failure"],
            "masked": res.masked,
            "seconds": res.seconds,
            "mode": res.mode,
            "suggested_reply_az": a.suggested_reply_az,
            "tokens_in": res.tokens_in,
            "tokens_out": res.tokens_out,
        }
        rows.append(row)
        mark = lambda ok: "ok " if ok else "XX "
        print(
            f"{t['id']}  cat {mark(row['category_ok'])}{a.category:<17} "
            f"risk {mark(row['risk_ok'])}{a.churn_risk:<7} sent {a.sentiment}/{label['sentiment']}  "
            f"bot {mark(row['failure_ok'])}{a.bot_failure:<17} {res.seconds:>5.2f}s"
        )

    scored = [r for r in rows if "error" not in r]
    n = len(scored) or 1
    mode = scored[0]["mode"] if scored else ("offline" if args.offline else "llm")
    summary = {
        "mode": mode,
        "decided_by": decided_by,
        "tickets": len(rows),
        "errors": len(rows) - len(scored),
        "category_accuracy": round(100 * sum(r["category_ok"] for r in scored) / n, 1),
        "churn_risk_accuracy": round(100 * sum(r["risk_ok"] for r in scored) / n, 1),
        "sentiment_within_1": round(100 * sum(r["sentiment_within_1"] for r in scored) / n, 1),
        "bot_failure_accuracy": round(100 * sum(r["failure_ok"] for r in scored) / n, 1),
        "chats_with_masked_data": sum(1 for r in scored if r["masked"]),
        "avg_seconds": round(sum(r["seconds"] for r in scored) / n, 2),
        "max_seconds": max((r["seconds"] for r in scored), default=0),
        "avg_tokens_in": round(sum(r["tokens_in"] for r in scored) / n),
        "avg_tokens_out": round(sum(r["tokens_out"] for r in scored) / n),
    }
    summary["usd_per_chat"] = round(
        (summary["avg_tokens_in"] * PRICE_IN_PER_M + summary["avg_tokens_out"] * PRICE_OUT_PER_M) / 1e6, 5
    )
    summary["usd_per_1000_chats"] = round(summary["usd_per_chat"] * 1000, 2)

    out_dir = ROOT / "results"
    out_dir.mkdir(exist_ok=True)
    (out_dir / f"eval_{mode}.json").write_text(
        json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    misses = [r for r in scored if not (r["category_ok"] and r["risk_ok"])]
    md = [
        f"# Eval results ({mode})",
        "",
        f"Decided by: **{decided_by}**. Expected values come from the hand-written answer key in data/tickets.json.",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Tickets | {summary['tickets']} (errors: {summary['errors']}) |",
        f"| Category accuracy | {summary['category_accuracy']}% |",
        f"| Churn-risk accuracy | {summary['churn_risk_accuracy']}% |",
        f"| Sentiment within ±1 | {summary['sentiment_within_1']}% |",
        f"| Bot-failure reason accuracy | {summary['bot_failure_accuracy']}% |",
        f"| Chats with personal data masked | {summary['chats_with_masked_data']} |",
        f"| Avg / max response time | {summary['avg_seconds']}s / {summary['max_seconds']}s |",
        f"| Avg tokens per chat (in / out) | {summary['avg_tokens_in']} / {summary['avg_tokens_out']} |",
        f"| Cost per chat / per 1,000 chats (paid tier) | ${summary['usd_per_chat']} / ${summary['usd_per_1000_chats']} |",
        "",
        "## Misses",
        "",
        "| Ticket | Expected | Predicted | Note |",
        "|---|---|---|---|",
    ]
    for r in misses:
        md.append(
            f"| {r['id']} | {r['expected']['category']} / {r['expected']['churn_risk']} | "
            f"{r['predicted']['category']} / {r['predicted']['churn_risk']} | {r['note']} |"
        )
    if not misses:
        md.append("| none | | | |")
    (out_dir / f"eval_{mode}.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print("\n" + json.dumps(summary, indent=2))
    print(f"Saved results/eval_{mode}.md")


if __name__ == "__main__":
    main()
