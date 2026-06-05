"""公开行情数据补充。

当前只接入 yfinance。它是公开免费源，覆盖稳定性受 Yahoo Finance 限制；缺失值
会保留为 None 并在报告中提示人工复核。
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class MarketSnapshot:
    """单个 ticker 的公开市场快照。"""

    ticker: str
    recent_gain_pct: Optional[float]
    market_cap_usd: Optional[float]


def fetch_market_snapshot(ticker: str, period: str = "6mo") -> MarketSnapshot:
    """用 yfinance 获取近期涨幅和市值。

    period 默认 6 个月，用于判断是否已大幅拥挤；调用方可按研究周期调整。
    """

    try:
        import yfinance as yf
    except ImportError as exc:
        raise RuntimeError("公开行情补充需要安装 yfinance，建议使用 Python 3.8+ 环境") from exc

    yf_ticker = yf.Ticker(ticker)
    history = yf_ticker.history(period=period, auto_adjust=True)
    recent_gain_pct = None
    if not history.empty:
        start_price = float(history["Close"].iloc[0])
        end_price = float(history["Close"].iloc[-1])
        if start_price <= 0:
            raise ValueError(f"{ticker} first close price is non-positive")
        recent_gain_pct = (end_price / start_price - 1.0) * 100

    info = yf_ticker.fast_info
    market_cap = getattr(info, "market_cap", None)
    return MarketSnapshot(
        ticker=ticker,
        recent_gain_pct=recent_gain_pct,
        market_cap_usd=float(market_cap) if market_cap is not None else None,
    )
