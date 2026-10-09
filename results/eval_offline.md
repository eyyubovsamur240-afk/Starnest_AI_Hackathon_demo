# Eval results (offline)

Decided by: **keyword rules (offline)**. Expected values come from the hand-written answer key in data/tickets.json.

| Metric | Value |
|---|---|
| Tickets scored | 40 of 40 (errors: 0, not run: 0) |
| Category accuracy | 77.5% |
| Churn-risk accuracy | 67.5% |
| Sentiment within ±1 | 75.0% |
| Bot-failure reason accuracy | 67.5% |
| Chats with personal data masked | 7 |
| Avg / max response time | 0.0s / 0.0s |
| Avg tokens per chat (in / out) | 0 / 0 |
| Cost per chat / per 1,000 chats (paid tier) | $0.0 / $0.0 |

## Misses

| Ticket | Expected | Predicted | Model | Note |
|---|---|---|---|---|
| T06 | billing / medium | billing / low | - |  |
| T09 | sim_card / medium | sim_card / low | - |  |
| T10 | tariff / medium | tariff / low | - |  |
| T14 | internet_speed / medium | internet_speed / low | - | tricky: sarcasm |
| T15 | refund / medium | billing / low | - | tricky: two issues in one chat |
| T22 | refund / medium | billing / medium | - |  |
| T24 | network_coverage / medium | other / low | - |  |
| T26 | network_coverage / high | sim_card / high | - |  |
| T27 | sim_card / medium | sim_card / low | - |  |
| T29 | billing / medium | tariff / low | - |  |
| T31 | other / high | tariff / high | - | tricky: complaint about the bot itself, no technical issue named |
| T33 | refund / high | billing / medium | - | tricky: churn hint stated mildly |
| T34 | internet_speed / medium | internet_speed / low | - |  |
| T36 | refund / medium | billing / low | - | tricky: refund request for the customer's own mistake |
| T38 | billing / medium | roaming / low | - | tricky: possible fraud, customer is worried rather than threatening |
| T39 | roaming / medium | roaming / low | - |  |
