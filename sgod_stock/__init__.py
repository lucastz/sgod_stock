"""Serenity 瓶颈公司发现系统的 Python 包入口。

本包只提供真实数据处理、抓取和评分逻辑；候选公司、X 帖子、公告链接等
输入必须来自用户授权抓取或公开数据源，正式代码不内置 mock 数据。
"""

__all__ = [
    "models",
    "text_filter",
    "scoring",
    "x_frontend",
    "chrome_devtools",
    "market_data",
    "reporting",
]
