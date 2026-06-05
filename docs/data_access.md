# 数据源和抓取说明

## X 数据

目标：抓取 @aleabitoreddit 最近约 1000 条公开帖子，并保留正文、时间、互动指标、ticker、引用关系。

首选方式：

- 使用你授权的已登录 Chrome 会话。
- Chrome 必须开启 `--remote-debugging-port=9222`。
- 本系统通过 DevTools 在页面内执行 fetch，自动携带登录态。
- 代码不读取、不保存、不导出 cookie 文件。

公开 guest 接口限制：

- 可读取部分单帖、Article 和用户资料。
- 普通主页 guest 流可能不给完整分页 cursor。
- 搜索时间线 guest 入口可能返回 404。
- 因此完整 1000 条以登录态 DevTools 方案为准。

## 股票和公告数据

免费公开源优先：

- Yahoo Finance / yfinance：价格、市值、近期涨幅。
- SEC EDGAR：美股公告、年报、招股书。
- 公司投资者关系页面：订单、客户、产能、财报材料。
- 交易所公告页面：A 股、港股、日股、欧股公告。
- CNINFO：A 股公告和年报。

数据缺失原则：

- 缺失字段保持为空或 None。
- 报告中标注“需要人工复核”。
- 不在正式代码里写 mock 数据补齐。

## 候选公司 CSV

候选公司必须来自真实研究输入。字段见：

```text
examples/candidates.schema.csv
```

`evidence_links` 使用 `|` 分隔多个公开链接。

## 输出文件

- `data/x/*.jsonl`：X 帖子抓取结果。
- `data/articles/*.json`：X Article 结果。
- `reports/*.json`：候选评分结果。
- `reports/*.md`：研究报告。
