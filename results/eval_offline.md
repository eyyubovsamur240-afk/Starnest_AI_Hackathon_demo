# Eval results (offline)

| Metric | Value |
|---|---|
| Tickets | 40 (errors: 0) |
| Category accuracy | 77.5% |
| Churn-risk accuracy | 67.5% |
| Sentiment within ±1 | 75.0% |
| Avg / max response time | 0.0s / 0.0s |

## Misses

| Ticket | Expected | Predicted | Note |
|---|---|---|---|
| T06 | billing / medium | billing / low |  |
| T09 | sim_card / medium | sim_card / low |  |
| T10 | tariff / medium | tariff / low |  |
| T14 | internet_speed / medium | internet_speed / low | tricky: sarcasm |
| T15 | refund / medium | billing / low | tricky: two issues in one chat |
| T22 | refund / medium | billing / medium |  |
| T23 | roaming / high | billing / high |  |
| T24 | network_coverage / medium | other / low |  |
| T26 | network_coverage / high | sim_card / high |  |
| T27 | sim_card / medium | sim_card / low |  |
| T29 | billing / medium | tariff / low |  |
| T33 | refund / high | billing / medium | tricky: churn hint stated mildly |
| T34 | internet_speed / medium | internet_speed / low |  |
| T36 | refund / medium | billing / low | tricky: refund request for the customer's own mistake |
| T38 | billing / medium | roaming / low | tricky: possible fraud, customer is worried rather than threatening |
| T39 | roaming / medium | roaming / low |  |
