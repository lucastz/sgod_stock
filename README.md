# Serenity 瓶颈公司发现系统

这是一个从零搭建的“报告 + 手册 + 筛选器”项目，用来把 Serenity
(@aleabitoreddit) 的供应链瓶颈投资方法落成可执行流程。

## 当前能力

- 读取 X 单帖 Article，例如 MarsCarsChipDip 的长文。
- 通过授权 Chrome DevTools 登录态抓取 X 用户时间线，不导出 cookie。
- 按投资关键词和 ticker 过滤帖子。
- 读取真实候选公司 CSV，按瓶颈强度、证据强度、涨幅惩罚、稀释风险等维度评分。
- 生成 Markdown 研究报告。

## 安装

```powershell
python -m pip install -r requirements.txt
```

当前机器默认 `python` 是 3.6.5，因此 requirements 已使用兼容版本标记。公开行情补充
模块里的新版 `yfinance` 只会在 Python 3.8+ 安装；抓取、过滤、评分和报告 CLI
可在当前环境运行。

## Chrome 登录态抓取

先关闭普通 Chrome，或新开一个调试版 Chrome 用户目录：

```powershell
Start-Process "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" -ArgumentList "--remote-debugging-port=9222 --user-data-dir=C:\tmp\sgod_stock_chrome"
```

在该 Chrome 中登录 X，并打开 `https://x.com/aleabitoreddit`。然后检查连接：

```powershell
python -m sgod_stock.cli chrome-status
```

抓取最近帖子：

```powershell
python -m sgod_stock.cli fetch-user-tweets-auth --screen-name aleabitoreddit --limit 1000 --out data/x/aleabitoreddit.jsonl
```

## 抓取 MarsCarsChipDip 长文

```powershell
python -m sgod_stock.cli fetch-article --tweet https://x.com/marscarschipdip/status/2060390190527451380 --out data/articles/marscarschipdip_2060390190527451380.json
```

## 候选公司评分

先按 `examples/candidates.schema.csv` 填写真实候选公司和证据链接。正式代码不内置 mock 数据。

```powershell
python -m sgod_stock.cli score-candidates --candidates data/candidates.csv --out reports/candidates.scored.json
```

## 生成报告

```powershell
python -m sgod_stock.cli report --tweets data/x/aleabitoreddit.jsonl --article data/articles/marscarschipdip_2060390190527451380.json --candidates data/candidates.csv --out reports/serenity_report.md
```

## 文档

- `docs/framework.md`：理论框架。
- `docs/manual.md`：任意新产业爆发时的人工 SOP。
- `docs/data_access.md`：数据源和登录态抓取说明。

## 注意

本项目只做研究流程和候选排序，不构成投资建议。所有结论必须绑定原帖、公告、财报或公开来源。
