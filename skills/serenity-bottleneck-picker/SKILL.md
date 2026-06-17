---
name: serenity-bottleneck-picker
description: >-
  Serenity Bottleneck Picker v2.1：用于分析新产业爆发、AI 基建、架构迁移、供应链瓶颈、瓶颈的瓶颈、
  上市公司代理、证据桥、涨幅惩罚和硬门槛。Use when the user asks to find, rank, or audit public
  equity candidates exposed to supply-chain bottlenecks, architecture shifts, scarcity economics, or
  Serenity-style bottleneck investing.
---

# Serenity Bottleneck Picker v2.1

Use this skill to analyze a stock, theme, sector, or new industrial boom with the Serenity bottleneck method.

Core rule: do not start from tickers. Start from demand/cost shock, architecture change, and physical constraints.

## Operating Modes

Use one of two modes based on the user request.

### Mode A — Single-stock bottleneck audit

Use when the user gives a ticker or company.

Goal: determine whether this company is a true bottleneck, chokepoint, bridge asset, weak thematic exposure, or fake linkage.

Required work:
- Identify the company's actual products, revenue lines, customers, capacity, balance sheet, and recent price move from public sources.
- Map the company's product into the full upstream/downstream chain.
- Find the demand or cost shock that would make this company matter now.
- Check whether the company controls a scarce node or merely participates in a hot theme.
- Score it with the scorecard and hard gates.
- Output a verdict with falsification triggers.

### Mode B — Theme-to-bottleneck discovery

Use when the user gives a theme, for example optical interconnect, CPO, AI power, HBM, humanoids, glass substrate, liquid cooling, or sovereign AI.

Goal: discover the real bottleneck layer and public proxies by reasoning upstream multiple layers.

Required work:
- Start from the demand/cost shock.
- Identify the architecture shift.
- Build a minimum 4-layer chain: end demand → system/module → component → material/foundry/test/equipment → public proxy.
- Compare candidate bottleneck layers and pick the tightest physical constraint.
- Find public companies that most cleanly express that constraint.
- Score the best candidates and state missing evidence.

For detailed source collection and chain-inference rules, load `references/research-protocol.md`.

## Workflow

1. **Define the shock**
   - Demand shock: new orders, capex, roadmap, policy, backlog, production ramp.
   - Cost shock: old architecture becomes too expensive, power-hungry, slow, unreliable, or hard to scale.
   - If the shock is unclear, stop and ask for the missing evidence.

2. **Map the architecture shift**
   - Old architecture → new architecture.
   - Ask what changes from optional to mandatory.
   - Map at least three layers upstream: system → module → component → material/foundry/test/equipment.

3. **Separate bottleneck, chokepoint, and bridge asset**
   - Bottleneck: currently limits supply, lead time, yield, capacity, or delivery.
   - Chokepoint: hard to replace once the architecture scales, even if not capacity-constrained today.
   - Bridge asset: controls integration, allocation, qualification, or customer access between scarce layers.

4. **Find the bottleneck of the bottleneck**
   - Continue two layers upstream from the obvious bottleneck.
   - Check materials, specialty chemicals, substrate, epitaxy, foundry slot, packaging, test, inspection, and equipment.

5. **Find the cleanest public proxy**
   - Prefer pure-play small/mid-cap bottleneck owners.
   - Then old-label mismatch suppliers, upstream material/equipment names, foundry/platform enablers, large-cap compounders, or baskets.
   - Reject fake AI linkage, tiny revenue exposure, serial dilution, impossible trading access, or easily bypassed nodes.

6. **Build the evidence bridge**
   - Grade evidence: confirmed / strong / rumor.
   - Confirmed or strong evidence is required before calling a candidate investable research.
   - Rumor may guide curiosity but must not carry the thesis.
   - Load `references/evidence-checklist.md` when auditing evidence.

7. **Run hard gates before scoring**
   - Financing dependence: LOW / MED / HIGH. HIGH caps the idea at observation/Lottery.
   - Counterparty quality: LOW / MED / HIGH. LOW caps the score until payment/backlog quality is verified.
   - Execution accessibility: ACCESSIBLE / LIMITED / INACCESSIBLE. INACCESSIBLE scores zero for this investor.

8. **Score industrial quality and current entry separately**
   - Industrial quality asks: is this a real bottleneck?
   - Current entry asks: can you still buy it with good risk/reward?
   - Load `references/scorecard.md` when a numeric score is requested.

9. **Apply price and crowding discipline**
   - Recent gain ≤100%: no penalty.
   - 100%-300%: light linear penalty.
   - 300%-500%: medium penalty; re-check odds.
   - 500%-800%: heavy penalty; wait for new evidence or pullback.
   - >800%: default to tracking only.
   - For A-shares, check turnover percentile, 龙虎榜 flow, company speculation warnings, and leader/laggard rotation.

10. **Write falsification triggers**
    - Falsification must be dated, binary, and checkable.
    - Include the threshold and the action it forces.

## Autonomous Research Contract

When current company facts, prices, filings, customer evidence, market caps, ownership, or A-share trading conditions matter, use public sources or available local data before scoring. Do not invent missing data.

Minimum source set for a scored answer:
- Company primary source: annual report, 10-K/20-F, investor presentation, prospectus, exchange filing, or official announcement.
- Product/technical source: datasheet, white paper, standards body, customer product page, teardown, or credible technical article.
- Market/price source: public quote source for recent gain and market cap, or mark unknown.
- Evidence source: customer qualification, order, backlog, revenue ramp, capacity expansion, government funding, patent, hiring, or supplier list.

If fewer than two independent evidence types are found, output Watchlist/Lottery only and cap confidence at medium.

## Output Template

```text
1. Executive view
2. Demand/cost shock
3. Architecture shift
4. Bottleneck map
5. Bottleneck vs chokepoint vs bridge asset
6. Public proxies
7. Evidence bridge
8. Hard gates
9. Industrial Bottleneck Score
10. Current Entry Score
11. A-share / crowding dashboard if relevant
12. Catalysts
13. Falsification triggers
14. Verdict: Core / Alpha / Watchlist / Lottery / Winner Tracking / Avoid
```

For stricter templates, load `references/output-templates.md`.

## Guardrails

- Do not fabricate evidence, market-structure data, customer relationships, prices, valuation history, or sell-side targets.
- Mark missing data as unknown and lower confidence.
- If a user asks for current market data, filings, rules, or prices, verify from public sources or local data before scoring.
- This skill produces research structure and priority ranking, not investment advice.
