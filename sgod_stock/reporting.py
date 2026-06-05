"""报告和手册生成。

报告生成器读取真实抓取结果和评分结果，输出 Markdown，方便继续人工编辑。
"""

import json
from collections import Counter
from pathlib import Path
from typing import List, Optional

from .models import ScoredCandidate, TweetRecord


def load_tweets_jsonl(path: Path) -> List[TweetRecord]:
    """从 JSONL 加载 TweetRecord。

    JSONL 应由本系统抓取命令输出；字段缺失直接报错，避免把不完整数据写入报告。
    """

    tweets = []  # type: List[TweetRecord]
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            payload = json.loads(line)
            tweets.append(
                TweetRecord(
                    tweet_id=payload["tweet_id"],
                    author=payload["author"],
                    created_at=payload["created_at"],
                    text=payload["text"],
                    url=payload["url"],
                    tickers=tuple(payload.get("tickers", [])),
                )
            )
    return tweets


def render_research_report(
    tweets: List[TweetRecord],
    article_text: Optional[str],
    scored: List[ScoredCandidate],
) -> str:
    """渲染 Serenity 方法论研究报告。"""

    ticker_counter = Counter()
    for tweet in tweets:
        ticker_counter.update(tweet.tickers)

    lines = [
        "# Serenity 瓶颈公司发现系统研究报告",
        "",
        "## 数据概览",
        f"- 已纳入投资相关帖子：{len(tweets)} 条",
        f"- 已识别 ticker 数量：{len(ticker_counter)} 个",
        f"- MarsCarsChipDip 长文：{'已纳入' if article_text else '未纳入'}",
        "",
        "## 核心理论",
        "- 先确认确定性需求冲击，再反向拆解完整产业链。",
        "- 真瓶颈必须同时具备供给集中、扩产慢、认证长、替代难、客户路线图依赖。",
        "- 优先寻找主营纯、市值相对小、市场尚未按新产业逻辑重估的干净代理公司。",
        "- 证据按监管披露/财报电话会、客户与政府项目、招聘专利与社媒线索分层。",
        "- 涨幅过大、融资稀释、财务脆弱会削弱入场性价比，即使瓶颈判断正确。",
        "",
        "## MarsCarsChipDip 长文精华",
    ]
    if article_text:
        lines.extend(
            [
                "- 八问框架：需求冲击、约束层、供应链节点、上市公司代理、弹性、证据、风险、时机。",
                "- Botanic Entry Score：瓶颈分 + 证据分 + 时机分 - 涨幅惩罚 - 拥挤度惩罚 - 稀释/质量惩罚。",
                "- 最重要的翻车约束：逻辑正确但涨幅透支时，赔率会显著变差。",
                "- 原文纪律：已涨 5-10 倍的标的只跟踪不挖掘，尤其 `>800%` 要优先排除追高冲动。",
            ]
        )
    else:
        lines.append("- 未提供长文输入，暂不生成该部分。")
    lines.extend(
        [
            "",
        "## 高频 ticker",
        ]
    )
    for ticker, count in ticker_counter.most_common(30):
        lines.append(f"- ${ticker}: {count} 次")

    lines.extend(["", "## 候选公司评分"])
    for item in sorted(scored, key=lambda row: row.score.total_score, reverse=True):
        candidate = item.candidate
        flags = "；".join(item.score.review_flags) if item.score.review_flags else "无"
        lines.extend(
            [
                f"### {candidate.company_name} ({candidate.ticker})",
                f"- 总分：{item.score.total_score}，正分：{item.score.positive_score}，扣分：{item.score.penalty_score}",
                f"- 产业主题：{candidate.industry_theme}",
                f"- 供应链环节：{candidate.supply_chain_node}",
                f"- 瓶颈证据：{candidate.bottleneck_evidence}",
                f"- 人工复核提示：{flags}",
            ]
        )
        for link in candidate.evidence_links:
            lines.append(f"- 证据链接：{link}")
    return "\n".join(lines) + "\n"


def write_markdown(path: Path, content: str) -> None:
    """写出 Markdown 文件。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
