# Eval results (llm): Gemini on 40 of 40 chats

Decided by: **Gemini (gemini-3.8-flash on 2, gemini-3.6-flash on 7, gemini-3.5-flash on 20, gemini-3.7-flash on 3, gemini-3.5-flash-lite on 8)**. Expected values come from the hand-written answer key in data/tickets.json.

| Metric | Value |
|---|---|
| Tickets scored | 40 of 40 (errors: 0, not run: 0) |
| Category accuracy | 87.5% |
| Churn-risk accuracy | 97.5% |
| Sentiment within ±1 | 100.0% |
| Bot-failure reason accuracy | 62.5% |
| Chats with personal data masked | 7 |
| Avg / max response time | 25.84s / 152.33s |
| Avg tokens per chat (in / out) | 1985 / 1466 |
| Cost per chat / per 1,000 chats (paid tier) | $0.00426 / $4.26 |

## Gemini vs keyword rules on the same 40 chats

| Metric | Gemini (40 chats) | Keyword rules (same 40 chats) |
|---|---|---|
| Category accuracy | 87.5% | 77.5% |
| Churn-risk accuracy | 97.5% | 67.5% |
| Sentiment within ±1 | 100.0% | 75.0% |
| Bot-failure reason accuracy | 62.5% | 67.5% |

## Misses

| Ticket | Expected | Predicted | Model | Note |
|---|---|---|---|---|
| T17 | roaming / high | refund / high | gemini-3.5-flash |  |
| T23 | roaming / high | refund / high | gemini-3.5-flash |  |
| T25 | other / low | sim_card / low | gemini-3.5-flash |  |
| T34 | internet_speed / medium | internet_speed / low | gemini-3.5-flash-lite |  |
| T37 | other / low | sim_card / low | gemini-3.5-flash-lite |  |
| T40 | internet_speed / high | network_coverage / high | gemini-3.5-flash-lite |  |
