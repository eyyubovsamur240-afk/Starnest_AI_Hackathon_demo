# Eval results (llm): Gemini on 2 of 40 chats, a sample

**Sample, not the full set.** Scored 2 of 40 chats; 38 not run, 0 failed with an error.

Run `python eval.py` again later: chats with a saved Gemini answer are not sent again.

Decided by: **Gemini (gemini-3.8-flash on 2)**. Expected values come from the hand-written answer key in data/tickets.json.

| Metric | Value |
|---|---|
| Tickets scored | 2 of 40 (errors: 0, not run: 38) |
| Category accuracy | 100.0% |
| Churn-risk accuracy | 100.0% |
| Sentiment within ±1 | 100.0% |
| Bot-failure reason accuracy | 100.0% |
| Chats with personal data masked | 0 |
| Avg / max response time | 20.13s / 28.31s |
| Avg tokens per chat (in / out) | 1994 / 1592 |
| Cost per chat / per 1,000 chats (paid tier) | $0.00458 / $4.58 |

## Gemini vs keyword rules on the same 2 chats

| Metric | Gemini (2 chats) | Keyword rules (same 2 chats) |
|---|---|---|
| Category accuracy | 100.0% | 100.0% |
| Churn-risk accuracy | 100.0% | 100.0% |
| Sentiment within ±1 | 100.0% | 100.0% |
| Bot-failure reason accuracy | 100.0% | 100.0% |

## Misses

| Ticket | Expected | Predicted | Model | Note |
|---|---|---|---|---|
| none | | | | |
