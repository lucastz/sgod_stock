# Skill 对比：investment-os vs serenity-bottleneck-picker

## 已安装位置

- 开源 skill：`C:\Users\tiaze\.codex\skills\investment-os`
- 本项目 skill：`C:\Users\tiaze\.codex\skills\serenity-bottleneck-picker`

重启 Codex 后，两者都会进入 skill 发现列表。

## 核心区别

| 维度 | investment-os | serenity-bottleneck-picker |
|---|---|---|
| 来源 | `youmadefox-spec/ai-botanic-picker-serenity-skill` | 本项目基于 1000 条 Serenity 贴文归纳 |
| 范围 | Serenity + FrankTrading 市场结构择时 | Serenity 瓶颈选股 + 本项目评分器 |
| 强项 | 市场结构、hard gates、旧标签重估、A 股拥挤度 | 真实推文语料、瓶颈的瓶颈、产能分配代理、CLI/数据留痕 |
| 适合问题 | “这个标的现在能不能买、多大仓位” | “这个新产业里谁是真瓶颈/代理公司” |
| 数据要求 | 可输出 unknown，强调不编造市场结构数据 | 要求证据链接和 CSV 明确输入，缺列直接报错 |
| 评分 | Industrial Bottleneck Score + Serenity Entry Score + Market Structure | 扩展后的 Serenity Score + 硬门槛封顶 |

## 本项目吸收的五个模块

1. `cost_shock`：成本冲击会迫使架构变化。
2. `failure_cost_jump`：小节点失败造成的下游损失越大，稀缺价值越高。
3. `old_label_mismatch`：旧业务标签和新架构角色之间的估值错配。
4. `hard_gates`：融资依赖、交易对手质量、交易可达性先于评分。
5. `a_share_crowding_dashboard`：换手率、龙虎榜、公司风险提示、龙头/补涨节奏。

## 涨幅惩罚差异

本项目按用户要求调整为：

- ≤100%：不扣分。
- 100%-300%：轻度线性扣分。
- 300%-500%：中等惩罚。
- 500%-800%：重罚。
- >800%：默认只跟踪不挖掘。

## 推荐对比 prompt

```text
使用 investment-os 分析 [主题/股票]，重点看市场结构、hard gates 和当前入场性价比。
```

```text
使用 serenity-bottleneck-picker 分析 [主题/股票]，重点从需求/成本冲击、架构变化、瓶颈的瓶颈和上市代理出发，找出可验证候选。
```
