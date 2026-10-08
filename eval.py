"""Run every ticket in data/tickets.json through the copilot and score it against the labels.

Usage:
    python eval.py               # LLM if GEMINI_API_KEY is set, else offline rules
    python eval.py --offline     # force the offline keyword baseline
    python eval.py --limit 5     # quick smoke run on the first 5 tickets

Writes results/eval_<mode>.json and results/eval_<mode>.md (the table for the pitch slide).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from copilot import analyze

ROOT = Path(__file__).parent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true", help="use the keyword baseline instead of the LLM")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    tickets = json.loads((ROOT / "data" / "tickets.json").read_text(encoding="utf-8"))[: args.limit]
    rows = []
    for t in tickets:
        try:
            res = analyze(t["chat"], force_offline=args.offline, known_names=[t["customer"]["name"]])
        except Exception as exc:  # keep going so one API error doesn't kill the run
            print(f"{t['id']}: ERROR {exc}")
            rows.append({"id": t["id"], "error": str(exc), "label": t["label"]})
            continue
        a, label = res.analysis, t["label"]
        row = {
            "id": t["id"],
            "note": t.get("note", ""),
            "label": label,
            "predicted": {"category": a.category, "churn_risk": a.churn_risk, "sentiment": a.sentiment, "bot_failure": a.bot_failure},
            "category_ok": a.category == label["category"],
            "risk_ok": a.churn_risk == label["churn_risk"],
            "sentiment_within_1": abs(a.sentiment - label["sentiment"]) <= 1,
            "failure_ok": a.bot_failure == label["bot_failure"],
            "masked": res.masked,
            "seconds": res.seconds,
            "mode": res.mode,
            "suggested_reply_az": a.suggested_reply_az,
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
        "tickets": len(rows),
        "errors": len(rows) - len(scored),
        "category_accuracy": round(100 * sum(r["category_ok"] for r in scored) / n, 1),
        "churn_risk_accuracy": round(100 * sum(r["risk_ok"] for r in scored) / n, 1),
        "sentiment_within_1": round(100 * sum(r["sentiment_within_1"] for r in scored) / n, 1),
        "bot_failure_accuracy": round(100 * sum(r["failure_ok"] for r in scored) / n, 1),
        "chats_with_masked_data": sum(1 for r in scored if r["masked"]),
        "avg_seconds": round(sum(r["seconds"] for r in scored) / n, 2),
        "max_seconds": max((r["seconds"] for r in scored), default=0),
    }

    out_dir = ROOT / "results"
    out_dir.mkdir(exist_ok=True)
    (out_dir / f"eval_{mode}.json").write_text(
        json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    misses = [r for r in scored if not (r["category_ok"] and r["risk_ok"])]
    md = [
        f"# Eval results ({mode})",
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
        "",
        "## Misses",
        "",
        "| Ticket | Expected | Predicted | Note |",
        "|---|---|---|---|",
    ]
    for r in misses:
        md.append(
            f"| {r['id']} | {r['label']['category']} / {r['label']['churn_risk']} | "
            f"{r['predicted']['category']} / {r['predicted']['churn_risk']} | {r['note']} |"
        )
    if not misses:
        md.append("| none | | | |")
    (out_dir / f"eval_{mode}.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print("\n" + json.dumps(summary, indent=2))
    print(f"Saved results/eval_{mode}.md")


if __name__ == "__main__":
    main()
