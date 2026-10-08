# Eval results (offline)

| Metric | Value |
|---|---|
| Tickets | 20 (errors: 0) |
| Category accuracy | 95.0% |
| Churn-risk accuracy | 75.0% |
| Sentiment within ±1 | 90.0% |
| Avg / max response time | 0.0s / 0.0s |

## Misses

| Ticket | Expected | Predicted | Note |
|---|---|---|---|
| T06 | billing / medium | billing / low |  |
| T09 | sim_card / medium | sim_card / low |  |
| T10 | tariff / medium | tariff / low |  |
| T14 | internet_speed / medium | internet_speed / low | tricky: sarcasm |
| T15 | refund / medium | billing / low | tricky: two issues in one chat |
