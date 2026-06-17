# Research Protocol

This protocol turns the skill from a checklist into an autonomous research workflow.

## Mode A: Single-stock Bottleneck Audit

Use this when the user gives a ticker or company.

### Step 1: Company Fact Base

Collect sourced facts:

- Exact products and business segments.
- Revenue mix and whether the bottleneck exposure can become material.
- Customers, design wins, qualifications, backlog, or shipment evidence.
- Capacity, utilization, expansion plans, equipment orders, hiring, or subsidies.
- Balance sheet, financing dependence, dilution history, and liquidity.
- Recent share-price move, market cap, and trading access.

If a fact is not found, write `unknown`; do not infer it.

### Step 2: Chain Placement

Place the company in a chain:

```text
End demand
→ system/platform
→ module
→ component/device
→ material/substrate/foundry/test/equipment
→ candidate company
```

Then ask:

- Is the company upstream enough to benefit before revenue becomes obvious?
- Is it the owner of the scarce node, a bridge asset, or just a reseller/distributor?
- Does failure at this node block downstream delivery or merely raise cost slightly?

### Step 3: Bottleneck Status

Classify the company:

- **Bottleneck**: supply, lead time, yield, capacity, or qualification currently constrains scale.
- **Chokepoint**: structurally hard to replace once architecture scales.
- **Bridge asset**: controls integration, allocation, qualification, or customer access.
- **Thematic exposure**: participates in the theme but does not constrain it.
- **Fake linkage**: story cannot be tied to product, customer, or financial evidence.

### Step 4: Score and Gates

Use `scorecard.md`.

Apply hard gates before final verdict:

- financing_dependence
- counterparty_quality
- execution_accessibility

Then apply recent-gain penalty and crowding checks.

## Mode B: Theme-to-Bottleneck Discovery

Use this when the user gives a theme or new industry.

### Step 1: Demand/Cost Shock

Define the shock:

- Who is buying or changing behavior?
- Why now?
- What breaks if the old solution continues?
- Which quarter or product generation should evidence appear?

### Step 2: Architecture Shift

Write old architecture → new architecture.

Example:

```text
Copper / pluggable-heavy interconnect
→ CPO / optical I/O / higher-speed optical fabric
```

### Step 3: Upstream Chain Expansion

Map at least four layers:

```text
End demand
→ system/module
→ active/passive component
→ material/substrate/process
→ capacity/equipment/test
→ public proxy
```

Do not stop at the first obvious layer. Always ask for the bottleneck of the bottleneck.

### Step 4: Candidate Layer Ranking

Rank layers by:

- Supply concentration.
- Expansion time.
- Qualification difficulty.
- Technical replacement difficulty.
- Downstream failure cost.
- Public proxy purity.
- Evidence visibility.
- Market recognition gap.

### Step 5: Public Proxy Search

For each high-scoring layer, find public companies globally:

- US, Europe, Japan, Korea, Taiwan, Hong Kong, A-share, OTC/ADR if executable.
- Prefer pure-play small/mid-cap proxies.
- Use large caps mostly as evidence unless the exposure is material.

### Step 6: Chain Thesis

Output a plain chain like:

```text
Demand shock
→ architecture shift
→ critical component
→ unavoidable material/process
→ scarce supplier group
→ cleanest public proxy
→ why market may still mislabel it
```

Example shape:

```text
光互连需求暴涨
→ 光模块/CPO 需要更高带宽和更低功耗
→ 激光器和光探测器依赖 InP 相关材料体系
→ 高质量 InP 衬底稳定量产供应商稀少
→ 小市值衬底厂若具备真实客户和产能，就是整条光子链的海峡
```

The example is a reasoning shape, not proof. Replace every arrow with sourced evidence before scoring.

## Source Priority

1. Company filings, official announcements, prospectus, annual report.
2. Customer or partner confirmation.
3. Datasheets, standards, patents, technical papers.
4. Earnings-call language, backlog, capex, utilization, shipment evidence.
5. Government funding or procurement records.
6. Credible industry reports and dated channel checks.
7. Social media clues only as leads, never as load-bearing evidence.

## Confidence Rules

- No primary source: confidence cannot exceed medium.
- No product-level evidence: cannot classify as Core/Alpha.
- No customer or financial bridge: Watchlist at most.
- Financing dependence HIGH: Lottery/observation cap.
- Inaccessible listing: score zero for this investor and find another expression.
