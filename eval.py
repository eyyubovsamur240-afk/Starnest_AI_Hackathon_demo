"""Run every ticket in data/tickets.json through the copilot and score it.

Each ticket's "expected" block is the hand-written answer key. It is only read here,
after the analysis, to score the result; it is never sent to Gemini or shown in the app.
Category, churn risk, sentiment and bot-failure reason are decided by Gemini (or by the
keyword rules with --offline) from the chat text alone.

Every Gemini answer is saved to results/gemini_cache.json, so a re-run only calls Gemini for
chats that have no saved answer yet. One chat costs one Gemini request. When the daily free-tier
quota runs out, the run stops and the report covers the chats that finished, marked as partial.

Several models can be chained with GEMINI_MODEL="model-a,model-b": each has its own free-tier quota, so
when one runs out (or stays busy with 503s) the next one answers. Every row records which model answered.

Usage:
    python eval.py --list-models # models this key can use, to pick GEMINI_MODEL
    python eval.py               # Gemini -> results/eval_llm.*
    python eval.py --limit 5     # quick Gemini check on the first 5 tickets
    python eval.py --offline     # keyword-rule baseline, no API -> results/eval_offline.*

Without GEMINI_API_KEY, `python eval.py` scores only the chats that already have a saved Gemini answer.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from copilot import MODELS, QuotaError, SetupError, analyze, key_description, list_models, llm_available

ROOT = Path(__file__).parent
OUT_DIR = ROOT / "results"

# Paid-tier price in USD per 1M tokens (thinking tokens bill as output). The defaults are the
# gemini-2.5-flash list price; set GEMINI_PRICE_IN / GEMINI_PRICE_OUT to the current price of the
# model you use (https://ai.google.dev/pricing). The free tier used for the demo costs nothing.
PRICE_IN_PER_M = float(os.getenv("GEMINI_PRICE_IN", "0.30"))
PRICE_OUT_PER_M = float(os.getenv("GEMINI_PRICE_OUT", "2.50"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true", help="use the keyword baseline instead of the LLM")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--list-models", action="store_true", help="print the Gemini models this key can use")
    args = parser.parse_args()

    if args.list_models:
        if not llm_available():
            raise SystemExit('Set the key first (PowerShell):  $env:GEMINI_API_KEY="your-key"')
        print(f"API key: {key_description()}\nModels this key can use for generateContent:")
        for name in list_models():
            print(f"  {name}{'   <- in GEMINI_MODEL' if name in MODELS else ''}")
        print('\nEach model has its own free-tier quota. Chain several, first choice first (PowerShell):\n'
              f'  $env:GEMINI_MODEL="{",".join(MODELS)},another-flash-model"')
        return

    live = not args.offline and llm_available()
    if not args.offline and not live:
        print(
            "GEMINI_API_KEY is not set: scoring only chats with a saved Gemini answer in results/gemini_cache.json.\n"
            '  For live calls (PowerShell):  $env:GEMINI_API_KEY="your-key"   then   python eval.py\n'
            "  For the keyword-rule baseline:  python eval.py --offline\n"
        )
    if live:
        print(f"API key: {key_description()}")
    planned = "keyword rules (offline)" if args.offline else f"Gemini ({', '.join(MODELS)})"
    print(f"Decided by: {planned}. The expected values are only used to score the results.\n")

    tickets = json.loads((ROOT / "data" / "tickets.json").read_text(encoding="utf-8"))[: args.limit]
    rows, not_run, stop_reason = [], [], None
    for i, t in enumerate(tickets):
        try:
            res = analyze(t["chat"], force_offline=args.offline, known_names=[t["customer"]["name"]], live=live)
        except (SetupError, QuotaError) as exc:  # every remaining chat would fail the same way
            stop_reason = str(exc)
            not_run = [x["id"] for x in tickets[i:]]
            print(f"\n{t['id']}: stopped. {exc}\n")
            break
        except Exception as exc:  # keep going so one API error doesn't kill the run
            print(f"{t['id']}: ERROR {exc}")
            rows.append({"id": t["id"], "error": str(exc), "expected": t["expected"]})
            continue
        if not args.offline and res.mode == "offline":  # no key and no saved answer
            not_run.append(t["id"])
            continue
        a, label = res.analysis, t["expected"]
        row = {
            "id": t["id"],
            "model": res.model,
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
        if not args.offline:  # the keyword rules on the same chat, for a like-for-like comparison
            o = analyze(t["chat"], force_offline=True, known_names=[t["customer"]["name"]]).analysis
            row["offline"] = {
                "category_ok": o.category == label["category"],
                "risk_ok": o.churn_risk == label["churn_risk"],
                "sentiment_within_1": abs(o.sentiment - label["sentiment"]) <= 1,
                "failure_ok": o.bot_failure == label["bot_failure"],
            }
        rows.append(row)
        mark = lambda ok: "ok " if ok else "XX "
        source = (f" {res.model}" if res.model else "") + (" (saved)" if res.mode == "cache" else "")
        print(
            f"{t['id']}  cat {mark(row['category_ok'])}{a.category:<17} "
            f"risk {mark(row['risk_ok'])}{a.churn_risk:<7} sent {a.sentiment}/{label['sentiment']}  "
            f"bot {mark(row['failure_ok'])}{a.bot_failure:<17} {res.seconds:>5.2f}s{source}"
        )

    scored = [r for r in rows if "error" not in r]
    errors = len(rows) - len(scored)
    if not scored:
        hint = stop_reason or ("" if live else "No saved Gemini answers yet: set GEMINI_API_KEY to run Gemini.")
        raise SystemExit(f"No chat was scored. {hint}".strip())
    n = len(scored)
    mode = "offline" if args.offline else "llm"
    partial = bool(not_run or errors)
    models_used: dict[str, int] = {}
    for r in scored:
        if r.get("model"):
            models_used[r["model"]] = models_used.get(r["model"], 0) + 1
    decided_by = "keyword rules (offline)" if args.offline else (
        "Gemini (" + ", ".join(f"{m} on {c}" for m, c in models_used.items()) + ")" if models_used else planned
    )
    pct = lambda rs, k: round(100 * sum(r[k] for r in rs) / len(rs), 1)
    summary = {
        "mode": mode,
        "decided_by": decided_by,
        "models_used": models_used,
        "partial": partial,
        "stop_reason": stop_reason,
        "tickets_in_set": len(tickets),
        "tickets": n,
        "errors": errors,
        "not_run": not_run,
        "from_saved_answers": sum(1 for r in scored if r["mode"] == "cache"),
        "category_accuracy": round(100 * sum(r["category_ok"] for r in scored) / n, 1),
        "churn_risk_accuracy": round(100 * sum(r["risk_ok"] for r in scored) / n, 1),
        "sentiment_within_1": round(100 * sum(r["sentiment_within_1"] for r in scored) / n, 1),
        "bot_failure_accuracy": round(100 * sum(r["failure_ok"] for r in scored) / n, 1),
        "chats_with_masked_data": sum(1 for r in scored if r["masked"]),
        "avg_seconds": round(sum(r["seconds"] for r in scored) / n, 2),
        "max_seconds": max(r["seconds"] for r in scored),
        "avg_tokens_in": round(sum(r["tokens_in"] for r in scored) / n),
        "avg_tokens_out": round(sum(r["tokens_out"] for r in scored) / n),
    }
    summary["usd_per_chat"] = round(
        (summary["avg_tokens_in"] * PRICE_IN_PER_M + summary["avg_tokens_out"] * PRICE_OUT_PER_M) / 1e6, 5
    )
    summary["usd_per_1000_chats"] = round(summary["usd_per_chat"] * 1000, 2)
    if not args.offline:
        same = [r["offline"] for r in scored]
        summary["offline_on_same_chats"] = {
            "category_accuracy": pct(same, "category_ok"),
            "churn_risk_accuracy": pct(same, "risk_ok"),
            "sentiment_within_1": pct(same, "sentiment_within_1"),
            "bot_failure_accuracy": pct(same, "failure_ok"),
        }

    OUT_DIR.mkdir(exist_ok=True)
    (OUT_DIR / f"eval_{mode}.json").write_text(
        json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    if args.offline:
        title = f"# Eval results ({mode}, PARTIAL: {n} of {len(tickets)} chats)" if partial else f"# Eval results ({mode})"
    else:
        title = f"# Eval results (llm): Gemini on {n} of {len(tickets)} chats" + (", a sample" if partial else "")
    md = [title, ""]
    if partial:
        md += [
            f"**Sample, not the full set.** Scored {n} of {len(tickets)} chats; "
            f"{len(not_run)} not run, {errors} failed with an error.",
            f"Stopped because: {stop_reason}" if stop_reason else "",
            "Run `python eval.py` again later: chats with a saved Gemini answer are not sent again.",
            "",
        ]
    misses = [r for r in scored if not (r["category_ok"] and r["risk_ok"])]
    md += [
        f"Decided by: **{decided_by}**. Expected values come from the hand-written answer key in data/tickets.json.",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Tickets scored | {n} of {len(tickets)} (errors: {errors}, not run: {len(not_run)}) |",
        f"| Category accuracy | {summary['category_accuracy']}% |",
        f"| Churn-risk accuracy | {summary['churn_risk_accuracy']}% |",
        f"| Sentiment within ±1 | {summary['sentiment_within_1']}% |",
        f"| Bot-failure reason accuracy | {summary['bot_failure_accuracy']}% |",
        f"| Chats with personal data masked | {summary['chats_with_masked_data']} |",
        f"| Avg / max response time | {summary['avg_seconds']}s / {summary['max_seconds']}s |",
        f"| Avg tokens per chat (in / out) | {summary['avg_tokens_in']} / {summary['avg_tokens_out']} |",
        f"| Cost per chat / per 1,000 chats (paid tier) | ${summary['usd_per_chat']} / ${summary['usd_per_1000_chats']} |",
        "",
        *(
            [
                f"## Gemini vs keyword rules on the same {n} chats",
                "",
                f"| Metric | Gemini ({n} chats) | Keyword rules (same {n} chats) |",
                "|---|---|---|",
                *[
                    f"| {label} | {summary[k]}% | {summary['offline_on_same_chats'][k]}% |"
                    for label, k in (
                        ("Category accuracy", "category_accuracy"),
                        ("Churn-risk accuracy", "churn_risk_accuracy"),
                        ("Sentiment within ±1", "sentiment_within_1"),
                        ("Bot-failure reason accuracy", "bot_failure_accuracy"),
                    )
                ],
                "",
            ]
            if not args.offline
            else []
        ),
        "## Misses",
        "",
        "| Ticket | Expected | Predicted | Model | Note |",
        "|---|---|---|---|---|",
    ]
    for r in misses:
        md.append(
            f"| {r['id']} | {r['expected']['category']} / {r['expected']['churn_risk']} | "
            f"{r['predicted']['category']} / {r['predicted']['churn_risk']} | {r.get('model') or '-'} | {r['note']} |"
        )
    if not misses:
        md.append("| none | | | | |")
    (OUT_DIR / f"eval_{mode}.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print("\n" + json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"Saved results/eval_{mode}.md" + (" (partial)" if partial else ""))
    if stop_reason:
        raise SystemExit(f"Stopped early: {stop_reason}")


if __name__ == "__main__":
    main()
