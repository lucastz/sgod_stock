"""X 时间线解析工具。

X 前端时间线结构经常变化，因此这里采用递归扫描 Tweet 和 Cursor 的方式；
扫描结果只来自接口真实返回，不人工补齐缺失分页。
"""

from typing import Any, List, Optional, Set

from .models import TweetRecord
from .x_frontend import normalize_tweet_result


def extract_tweets(data: dict, author_screen_name: str) -> List[TweetRecord]:
    """从 X 时间线响应中提取 TweetRecord。

    只提取 timeline item 的主 tweet，不递归抓 quoted_status_result 里的别人原帖。
    同一条 tweet 可能出现在置顶和普通列表中；这里按 tweet_id 去重并保留首次出现。
    """

    records = []  # type: List[TweetRecord]
    seen = set()  # type: Set[str]

    def add_result(result: Any) -> None:
        """添加一个 timeline 主 tweet。"""

        if not isinstance(result, dict):
            return
        if result.get("__typename") != "Tweet" or "legacy" not in result or "rest_id" not in result:
            return
        tweet_id = result["rest_id"]
        if tweet_id in seen:
            return
        seen.add(tweet_id)
        records.append(normalize_tweet_result(result, author_screen_name))

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            item_content = value.get("itemContent")
            if isinstance(item_content, dict):
                tweet_result = item_content.get("tweet_results", {}).get("result")
                add_result(tweet_result)
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(data)
    return records


def extract_bottom_cursor(data: dict) -> Optional[str]:
    """从 X 时间线响应中提取下一页 bottom cursor。"""

    cursors = []  # type: List[str]

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            cursor_type = value.get("cursorType")
            cursor_value = value.get("value")
            if cursor_type == "Bottom" and isinstance(cursor_value, str):
                cursors.append(cursor_value)
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(data)
    return cursors[-1] if cursors else None
