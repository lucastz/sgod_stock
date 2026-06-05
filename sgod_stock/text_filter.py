"""帖子过滤和 ticker 提取。

过滤器只做可解释的关键词规则，不把非投资内容误包装成研究结论。后续如要接入
LLM 分类，也应先保存本模块输出的规则命中结果作为可审计基线。
"""

import re
from dataclasses import dataclass
from typing import List, Tuple

from .models import TweetRecord


TICKER_RE = re.compile(r"(?<![A-Z0-9])\$([A-Z][A-Z0-9.]{0,9})(?![A-Z0-9])")


INVESTMENT_KEYWORDS = (
    "supply chain",
    "chokepoint",
    "bottleneck",
    "capacity",
    "qualification",
    "customer",
    "contract",
    "order",
    "revenue",
    "earnings",
    "guidance",
    "capex",
    "margin",
    "dilution",
    "atm",
    "valuation",
    "multiple",
    "stock",
    "ticker",
    "semiconductor",
    "photonics",
    "optical",
    "CPO",
    "HBM",
    "ASIC",
    "GPU",
    "AI",
    "datacenter",
    "data center",
    "foundry",
    "substrate",
    "laser",
    "module",
    "power",
)


NON_INVESTMENT_KEYWORDS = (
    "congrats",
    "birthday",
    "meme",
    "anime",
    "subscribe",
    "followers",
    "most subscribed",
)


@dataclass(frozen=True)
class FilterDecision:
    """单条帖子的过滤结果。

    reasons 记录命中的关键词，方便人工复核为什么某条被保留或剔除。
    """

    keep: bool
    tickers: Tuple[str, ...]
    reasons: Tuple[str, ...]
    negative_reasons: Tuple[str, ...]


def extract_tickers(text: str) -> Tuple[str, ...]:
    """从文本中提取美元符号 ticker。

    只提取显式 `$XXX`，不猜测普通英文大写词是否为股票代码，避免过度扩展。
    """

    tickers = sorted({match.group(1).rstrip(".") for match in TICKER_RE.finditer(text)})
    return tuple(tickers)


def decide_investment_relevance(text: str) -> FilterDecision:
    """判断文本是否和投资研究相关。

    规则优先保留带 ticker 或产业链关键词的帖子；明显社交/账号运营内容如果没有
    投资信号会被剔除。
    """

    normalized = text.lower()
    tickers = extract_tickers(text)
    positive_hits = tuple(
        keyword for keyword in INVESTMENT_KEYWORDS if keyword.lower() in normalized
    )
    negative_hits = tuple(
        keyword for keyword in NON_INVESTMENT_KEYWORDS if keyword.lower() in normalized
    )

    has_investment_signal = bool(tickers or positive_hits)
    only_social_signal = bool(negative_hits) and not has_investment_signal
    return FilterDecision(
        keep=has_investment_signal and not only_social_signal,
        tickers=tickers,
        reasons=positive_hits,
        negative_reasons=negative_hits,
    )


def filter_tweets(tweets: List[TweetRecord]) -> List[TweetRecord]:
    """过滤帖子并补充 ticker 字段。

    dataclass 是 frozen 的，因此这里创建新对象而不是原地修改，避免数据流混乱。
    """

    kept = []  # type: List[TweetRecord]
    for tweet in tweets:
        decision = decide_investment_relevance(tweet.text)
        if not decision.keep:
            continue
        kept.append(
            TweetRecord(
                tweet_id=tweet.tweet_id,
                author=tweet.author,
                created_at=tweet.created_at,
                text=tweet.text,
                url=tweet.url,
                metrics=tweet.metrics,
                tickers=decision.tickers,
                is_retweet=tweet.is_retweet,
                in_reply_to=tweet.in_reply_to,
                quoted_tweet_id=tweet.quoted_tweet_id,
                raw=tweet.raw,
            )
        )
    return kept
