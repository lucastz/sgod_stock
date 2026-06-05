"""系统核心数据结构。

这些 dataclass 是后续抓取、过滤、评分、报告生成共用的边界对象。
所有字段都尽量保留来源信息，方便最终报告把结论追溯到原帖或公开材料。
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple


@dataclass(frozen=True)
class SourceRef:
    """一条证据来源。

    label 用于在报告里显示来源名称；url 或 source_id 至少应有一个，避免
    产生无法核验的结论。
    """

    label: str
    url: Optional[str] = None
    source_id: Optional[str] = None


@dataclass(frozen=True)
class TweetMetrics:
    """X 帖子的互动指标。

    指标来自 X 前端返回的 legacy 字段；缺失时保持为 None，不用 0 冒充真实值。
    """

    replies: Optional[int] = None
    reposts: Optional[int] = None
    quotes: Optional[int] = None
    likes: Optional[int] = None
    bookmarks: Optional[int] = None
    views: Optional[int] = None


@dataclass(frozen=True)
class TweetRecord:
    """标准化后的 X 帖子记录。

    text 是后续过滤和 ticker 提取的主文本；raw 保留原始对象，方便排查字段
    变化或补充新的指标。
    """

    tweet_id: str
    author: str
    created_at: str
    text: str
    url: str
    metrics: TweetMetrics = field(default_factory=TweetMetrics)
    tickers: Tuple[str, ...] = ()
    is_retweet: bool = False
    in_reply_to: Optional[str] = None
    quoted_tweet_id: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class CandidateCompany:
    """候选公司的人工/自动合并输入。

    筛选器不凭空生成公司事实。调用方需要提供公司所处环节、证据说明和证据链接；
    市场数据可由公开行情接口补充。
    """

    ticker: str
    company_name: str
    exchange: str
    industry_theme: str
    supply_chain_node: str
    demand_shock: str
    bottleneck_evidence: str
    evidence_links: Tuple[str, ...]
    recent_gain_pct: Optional[float] = None
    market_cap_usd: Optional[float] = None
    notes: Optional[str] = None


@dataclass(frozen=True)
class ScoreBreakdown:
    """候选公司评分明细。

    positive_score 和 penalty_score 分开保留，便于看清公司是“真瓶颈不足”
    还是“涨幅/稀释/财务风险太高”。
    """

    total_score: float
    positive_score: float
    penalty_score: float
    fields: Dict[str, float]
    review_flags: Tuple[str, ...]


@dataclass(frozen=True)
class ScoredCandidate:
    """打分后的候选公司。

    candidate 保留原始输入，score 只表达模型计算结果，不替代人工尽调。
    """

    candidate: CandidateCompany
    score: ScoreBreakdown
