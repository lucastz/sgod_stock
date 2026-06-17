# Scorecard

Use this scorecard when a user asks for a numeric ranking.

## Industrial Quality Inputs

Score each field 0-5 from sourced evidence. Do not infer from vibes.

| Field | Meaning |
|---|---|
| demand_certainty | Downstream demand is validated by capex, orders, roadmap, policy, backlog, or production ramp. |
| cost_shock | Old solution is becoming too expensive, power-hungry, slow, unreliable, or hard to scale. |
| failure_cost_jump | Failure of this node causes much larger downstream cost than before. |
| mandatory_adoption | New architecture makes this node mandatory or hard to avoid. |
| bottleneck_strength | The node limits supply, delivery, lead time, yield, capacity, or roadmap. |
| evidence_strength | Evidence quality and independence. |
| pure_play | Revenue/profit/valuation maps cleanly to the bottleneck. |
| expansion_difficulty | Capacity, qualification, process, material, or equipment expansion is slow. |
| customer_validation | Top customers, ecosystem partners, or government programs validate the node. |
| old_label_mismatch | Market still values the company under an outdated label. |
| market_attention_gap | Consensus has not fully recognized the new role. |
| timing_score | Catalysts are visible in the next 1-4 quarters. |

## Risk Inputs

Score each risk field 0-5.

| Field | Meaning |
|---|---|
| crowding_risk | The trade is already consensus or momentum-crowded. |
| a_share_crowding_risk | A-share turnover, 龙虎榜, company warnings, and leader/laggard pattern are overheated. |
| dilution_risk | ATM, converts, equity raises, or cash burn can dilute holders. |
| financial_risk | Debt, cash flow, margin, or going-concern risk is high. |
| technical_substitution_risk | The node may be bypassed by another architecture. |
| evidence_gap_risk | The thesis lacks confirmed/strong evidence. |

## Hard Gates

Run these before final classification:

| Gate | Values | Effect |
|---|---|---|
| financing_dependence | LOW / MED / HIGH | HIGH caps total attractiveness at observation/Lottery. |
| counterparty_quality | LOW / MED / HIGH | LOW caps total attractiveness until contract/backlog quality is proven. |
| execution_accessibility | ACCESSIBLE / LIMITED / INACCESSIBLE | INACCESSIBLE scores zero for this investor. |

## Recent Gain Penalty

```text
≤100%: no penalty
100%-300%: light linear penalty
300%-500%: medium penalty
500%-800%: heavy penalty
>800%: tracking only by default
```

## Recommended Verdict Labels

- Core: strong industrial quality, strong entry, hard gates pass.
- Alpha: high-quality bottleneck with acceptable entry.
- Watchlist: valid thesis but needs better evidence or entry.
- Lottery: high optionality, weak validation or hard-gate cap.
- Winner Tracking: great company or theme, but move already happened.
- Avoid: weak evidence, fake linkage, inaccessible trade, or failed thesis.
