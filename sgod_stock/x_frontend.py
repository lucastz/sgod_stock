"""X 前端公开接口和 Article 解析。

优先使用 X 当前前端包里暴露的 GraphQL queryId，避免硬编码过期接口。公开 guest
接口只用于不需要登录的单帖/文章读取；完整 1000 条主页数据应走授权 Chrome 会话。
"""

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests

from .models import TweetMetrics, TweetRecord
from .text_filter import extract_tickers


MAIN_JS_RE = re.compile(r'https://abs\.twimg\.com/responsive-web/client-web/main\.[^"]+\.js')
BEARER_RE = re.compile(r"Bearer ([A-Za-z0-9%._\-]+)")


@dataclass(frozen=True)
class GraphQLOperation:
    """X 前端 GraphQL 操作元数据。"""

    query_id: str
    name: str
    features: Dict[str, bool]
    field_toggles: Dict[str, bool]


class XFrontendClient:
    """X 公开前端接口客户端。

    该客户端会读取公开前端 JS 中的 bearer token 和 queryId，并申请 guest token。
    登录态采集请使用 chrome_devtools.py。
    """

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0",
                "x-twitter-active-user": "yes",
                "x-twitter-client-language": "en",
            }
        )
        self.main_js = self._load_main_js()
        self.bearer = self._extract_bearer(self.main_js)
        self.session.headers["authorization"] = f"Bearer {self.bearer}"
        self.session.headers["x-guest-token"] = self._activate_guest_token()

    def _load_main_js(self) -> str:
        """读取 X 首页并下载当前 main JS。"""

        response = self.session.get("https://x.com", timeout=20)
        response.raise_for_status()
        match = MAIN_JS_RE.search(response.text)
        if not match:
            raise RuntimeError("无法在 X 首页中找到 main JS URL")
        js_response = self.session.get(match.group(0), timeout=20)
        js_response.raise_for_status()
        return js_response.text

    def _extract_bearer(self, main_js: str) -> str:
        """从 main JS 中提取公开 bearer token。"""

        match = BEARER_RE.search(main_js)
        if not match:
            raise RuntimeError("无法从 X main JS 中提取 bearer token")
        return match.group(1)

    def _activate_guest_token(self) -> str:
        """申请 guest token。"""

        response = self.session.post("https://api.x.com/1.1/guest/activate.json", timeout=20)
        response.raise_for_status()
        token = response.json().get("guest_token")
        if not token:
            raise RuntimeError("X guest activate response missing guest_token")
        return token

    def operation(self, name: str) -> GraphQLOperation:
        """根据 operationName 从 main JS 中读取 queryId 和开关。"""

        pattern = (
            r'queryId:"([^"]+)",operationName:"'
            + re.escape(name)
            + r'",operationType:"[^"]+",metadata:{featureSwitches:\[(.*?)\],fieldToggles:\[(.*?)\]'
        )
        match = re.search(pattern, self.main_js)
        if not match:
            raise RuntimeError(f"无法在 X main JS 中找到 GraphQL operation: {name}")
        features = self._parse_toggle_list(match.group(2))
        field_toggles = self._parse_toggle_list(match.group(3))
        return GraphQLOperation(match.group(1), name, features, field_toggles)

    @staticmethod
    def _parse_toggle_list(raw: str) -> Dict[str, bool]:
        """解析前端包中的 feature/field toggle 列表。"""

        return {
            item.strip().strip('"'): True
            for item in raw.split(",")
            if item.strip().strip('"')
        }

    def graphql(self, operation: GraphQLOperation, variables: Dict[str, Any]) -> Dict[str, Any]:
        """调用 X GraphQL 公开接口。"""

        params = {
            "variables": json.dumps(variables, separators=(",", ":")),
            "features": json.dumps(operation.features, separators=(",", ":")),
            "fieldToggles": json.dumps(operation.field_toggles, separators=(",", ":")),
        }
        url = f"https://x.com/i/api/graphql/{operation.query_id}/{operation.name}"
        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def fetch_tweet_article(self, tweet_id: str) -> Dict[str, Any]:
        """读取带 X Article 的单帖。"""

        operation = self.operation("TweetResultByRestId")
        data = self.graphql(
            operation,
            {
                "tweetId": tweet_id,
                "withCommunity": False,
                "includePromotedContent": False,
                "withVoice": False,
            },
        )
        result = data["data"]["tweetResult"]["result"]
        article = result.get("article", {}).get("article_results", {}).get("result")
        if not article:
            raise RuntimeError(f"tweet {tweet_id} does not contain an article result")
        return article

    def fetch_user_profile(self, screen_name: str) -> Dict[str, Any]:
        """按 screen_name 读取用户资料。"""

        operation = self.operation("UserByScreenName")
        data = self.graphql(operation, {"screen_name": screen_name})
        return data["data"]["user"]["result"]


def tweet_id_from_url(url_or_id: str) -> str:
    """从 X URL 或纯数字字符串中提取 tweet id。"""

    if url_or_id.isdigit():
        return url_or_id
    match = re.search(r"/status/(\d+)", url_or_id)
    if not match:
        raise ValueError(f"无法从输入中提取 tweet id: {url_or_id}")
    return match.group(1)


def article_plain_text(article: Dict[str, Any]) -> str:
    """从 X Article 对象提取正文纯文本。"""

    plain_text = article.get("plain_text")
    if isinstance(plain_text, str) and plain_text.strip():
        return plain_text
    blocks = article.get("content_state", {}).get("blocks", [])
    return "\n".join(block.get("text", "") for block in blocks).strip()


def build_graphql_url(operation: GraphQLOperation, variables: Dict[str, Any]) -> str:
    """构造可在登录态页面内 fetch 的 GraphQL URL。"""

    params = {
        "variables": json.dumps(variables, separators=(",", ":")),
        "features": json.dumps(operation.features, separators=(",", ":")),
        "fieldToggles": json.dumps(operation.field_toggles, separators=(",", ":")),
    }
    return f"https://x.com/i/api/graphql/{operation.query_id}/{operation.name}?{urlencode(params)}"


def normalize_tweet_result(result: Dict[str, Any], author_screen_name: str) -> TweetRecord:
    """把 X GraphQL Tweet result 转换为 TweetRecord。"""

    legacy = result.get("legacy", {})
    tweet_id = result["rest_id"]
    text = extract_full_tweet_text(result)
    metrics = TweetMetrics(
        replies=legacy.get("reply_count"),
        reposts=legacy.get("retweet_count"),
        quotes=legacy.get("quote_count"),
        likes=legacy.get("favorite_count"),
        bookmarks=legacy.get("bookmark_count"),
        views=_parse_views(result),
    )
    return TweetRecord(
        tweet_id=tweet_id,
        author=author_screen_name,
        created_at=legacy.get("created_at", ""),
        text=text,
        url=f"https://x.com/{author_screen_name}/status/{tweet_id}",
        metrics=metrics,
        tickers=extract_tickers(text),
        is_retweet="retweeted_status_result" in legacy,
        in_reply_to=legacy.get("in_reply_to_status_id_str"),
        quoted_tweet_id=result.get("quoted_status_result", {}).get("result", {}).get("rest_id"),
        raw=result,
    )


def _parse_views(result: Dict[str, Any]) -> Optional[int]:
    """解析 X view_count_info 字段。"""

    raw_count = result.get("views", {}).get("count")
    if raw_count is None:
        return None
    return int(raw_count)


def extract_full_tweet_text(result: Dict[str, Any]) -> str:
    """提取 X 帖子的完整正文。

    普通短帖在 legacy.full_text；长帖会被截断，完整正文在
    note_tweet.note_tweet_results.result.text。这里优先读取长帖字段。
    """

    note_result = (
        result.get("note_tweet", {})
        .get("note_tweet_results", {})
        .get("result", {})
    )
    note_text = note_result.get("text")
    if isinstance(note_text, str) and note_text:
        return note_text

    direct_note_result = result.get("note_tweet_results", {}).get("result", {})
    direct_note_text = direct_note_result.get("text")
    if isinstance(direct_note_text, str) and direct_note_text:
        return direct_note_text

    return result.get("legacy", {}).get("full_text", "")
