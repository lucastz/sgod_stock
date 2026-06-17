# Serenity 瓶颈公司发现系统研究报告

## 数据概览
- 已抓取 Serenity 贴文：1000 条
- 唯一 tweet_id：1000 个
- 正文为空：0 条
- 已纳入投资相关帖子：约 857 条
- 样本时间范围：2026-03-16 22:31:32 UTC 至 2026-06-05 09:10:16 UTC
- MarsCarsChipDip 长文：已纳入

## 核心理论
- Serenity 方法不是寻找“热门产业里的好公司”，而是寻找下游需求确定、全链路扩产被小节点限制、且该节点能被上市公司高纯度映射的股票。
- 需求冲击必须来自真实客户预算、订单、路线图、政策、backlog 或认证进度；需求本身不真，后续瓶颈都是故事。
- 需要区分 chokepoint 和 bottleneck：chokepoint 是路线图卡点，bottleneck 是扩产约束；有些公司通过锁定产能分配，成为可交易瓶颈代理。
- 真瓶颈必须同时具备供给集中、扩产慢、认证长、替代难、客户路线图依赖、价值捕获和可交易代理。
- 高优先级机会常来自“瓶颈的瓶颈”：材料、特种化学品、substrate、foundry、epitaxy、test/burn-in 或关键设备。
- 涨幅过大、交易拥挤、融资稀释、财务脆弱会削弱入场性价比，即使瓶颈判断正确。

## MarsCarsChipDip 长文精华
- 八问框架：需求冲击、约束层、供应链节点、上市公司代理、弹性、证据、风险、时机。
- Botanic Entry Score：瓶颈分 + 证据分 + 时机分 - 涨幅惩罚 - 拥挤度惩罚 - 稀释/质量惩罚。
- 最重要的翻车约束：逻辑正确但涨幅透支时，赔率会显著变差。
- 原文纪律：已涨 5-10 倍的标的只跟踪不挖掘，尤其 `>800%` 要优先排除追高冲动。

## 高频 ticker
- `SIVE`：477 次
- `LITE`：259 次
- `AAOI`：154 次
- `AXTI`：153 次
- `NVDA`：151 次
- `MRVL`：117 次
- `SOI`：101 次
- `COHR`：88 次
- `IQE`：75 次
- `MSFT`：72 次

## 高频主题
- `photonics`：197 次
- `CPO`：184 次
- `laser`：169 次
- `hyperscaler`：137 次
- `optical`：117 次
- `bottleneck`：90 次
- `substrate`：68 次
- `capacity`：66 次
- `chokepoint`：66 次

## 代表性原帖
- `2058374522353672558`：区分 SIVE 的 chokepoint 与 Win Semi 的产能 bottleneck，并提出产能分配会让中间公司成为瓶颈代理。
- `2043906518026989817`：把 InP substrate 继续上拆到 high purity phosphorus 和 indium，体现“瓶颈的瓶颈”。
- `2061348882685243497`：用 XFAB 展示从 Nvidia 800VDC 需求反推 GaN/SiC foundry 和 Western supply chain premium。
- `2055822766600016238`：把 photonics TAM、LITE backlog、SIVE CW laser、JBL/POET/MRVL/AMD 等下游路线串成一条链。

## v2 落地公式
```text
Serenity Score =
需求确定性 + 瓶颈强度 + 证据强度 + 公司纯度 + 扩产难度 + 客户验证 + 市场未定价 + 时机
- 涨幅惩罚 - 拥挤度风险 - 稀释风险 - 财务风险 - 技术替代风险 - 证据断裂风险
```

## 候选公司评分
当前仓库还没有填入真实候选公司 CSV，因此本节不生成具体买入名单。下一步应按 `examples/candidates.schema.csv` 为每个主题填入真实候选、证据链接、涨幅和风险分，再运行评分器。
