"""通过 X 搜索时间线直接补抓指定日期之前的公开帖子。

这个脚本用于绕开 Profile `UserTweets` cursor 回跳的问题：先让已登录浏览器打开
`/search` 页面，由 X 前端自己发出一条真实 SearchTimeline 请求；脚本捕获这条请求的
queryId 和 features，再用同一套参数继续带 cursor 翻页。

脚本不读取、不导出 cookie 文件；所有 X 请求都在已登录的浏览器页面上下文里执行。
"""

import argparse
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

import websocket


def _x_page(endpoint):
    """找到当前 DevTools Chrome 里的 X 页面标签页。"""

    payload = urllib.request.urlopen(endpoint.rstrip("/") + "/json/list", timeout=5).read()
    pages = json.loads(payload.decode("utf-8"))
    for page in pages:
        if page.get("type") == "page" and "x.com" in page.get("url", ""):
            return page
    raise RuntimeError("未找到 X 页面，请在 DevTools Chrome 中打开 https://x.com")


def _safe_json_line(payload):
    """把对象写成严格单行 JSONL。

    X 长帖正文里偶尔会包含 U+2028/U+2029；Python 的 splitlines 会把它们当成换行。
    这里显式转义，保证一个 tweet 永远只占 JSONL 的一行。
    """

    return (
        json.dumps(payload, ensure_ascii=False)
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def _load_seen(output_path):
    """读取已保存 tweet_id，避免搜索补抓时重复写入。"""

    seen = set()
    if not output_path.exists():
        return seen
    with output_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                seen.add(json.loads(line)["tweet_id"])
    return seen


def _load_cursor(cursor_path, raw_query):
    """读取同一个 raw_query 的搜索 cursor。"""

    if not cursor_path.exists():
        return None
    payload = json.loads(cursor_path.read_text(encoding="utf-8"))
    if payload.get("raw_query") != raw_query:
        raise RuntimeError("cursor 文件里的 raw_query 与本次参数不一致，请换一个 cursor-file")
    return payload.get("cursor")


def _extract_search_template(url):
    """从真实 SearchTimeline 请求 URL 中提取分页模板。"""

    parsed = urllib.parse.urlparse(url)
    match = re.search(r"/graphql/([^/]+)/SearchTimeline$", parsed.path)
    if not match:
        raise RuntimeError(f"不是 SearchTimeline GraphQL URL: {url}")
    params = urllib.parse.parse_qs(parsed.query)
    variables = json.loads(params["variables"][0])
    features = params["features"][0]
    field_toggles = params.get("fieldToggles", [None])[0]
    return {
        "query_id": match.group(1),
        "variables": variables,
        "features": features,
        "field_toggles": field_toggles,
    }


def _capture_first_search_page(endpoint, raw_query):
    """打开 X 搜索页并捕获第一条真实 SearchTimeline 请求和响应。

    SearchTimeline 的 queryId 会随 X 前端路由包变化；直接解析 main.js 可能拿到旧 id。
    因此这里让浏览器页面自己请求一次，再复用真实 URL 作为后续分页模板。
    """

    page = _x_page(endpoint)
    ws = websocket.create_connection(
        page["webSocketDebuggerUrl"],
        timeout=20,
        origin=endpoint.rstrip("/"),
    )
    ws.settimeout(5)
    next_id = 1
    pending_body = {}
    search_requests = {}

    def send(method, params=None):
        """发送一条 Chrome DevTools Protocol 命令并返回 message id。"""

        nonlocal next_id
        message_id = next_id
        next_id += 1
        ws.send(json.dumps({"id": message_id, "method": method, "params": params or {}}))
        return message_id

    search_url = (
        "https://x.com/search?q="
        + urllib.parse.quote(raw_query)
        + "&src=typed_query&f=live"
    )
    try:
        send("Network.enable")
        send("Page.enable")
        send("Page.navigate", {"url": search_url})
        started_at = time.time()
        while time.time() - started_at < 45:
            message = json.loads(ws.recv())
            method = message.get("method")
            params = message.get("params", {})

            if method == "Network.requestWillBeSent":
                url = params.get("request", {}).get("url", "")
                if "/SearchTimeline?" in url:
                    request_id = params["requestId"]
                    search_requests[request_id] = {
                        "url": url,
                        "status": None,
                    }
            elif method == "Network.responseReceived":
                request_id = params.get("requestId")
                if request_id in search_requests:
                    search_requests[request_id]["status"] = params.get("response", {}).get("status")
            elif method == "Network.loadingFinished":
                request_id = params.get("requestId")
                if request_id in search_requests:
                    body_message_id = send("Network.getResponseBody", {"requestId": request_id})
                    pending_body[body_message_id] = request_id
            elif message.get("id") in pending_body:
                request_id = pending_body.pop(message["id"])
                body = message.get("result", {}).get("body", "")
                request = search_requests[request_id]
                if request["status"] != 200:
                    raise RuntimeError(f"SearchTimeline HTTP {request['status']}: {body[:500]}")
                return _extract_search_template(request["url"]), json.loads(body)
    finally:
        ws.close()

    raise RuntimeError("45 秒内没有捕获到 SearchTimeline 响应")


def _search_payload_stream(endpoint, raw_query, max_pages):
    """通过滚动搜索页连续捕获 SearchTimeline 响应。

    SearchTimeline 的翻页请求依赖 X 前端生成的完整请求头；手工 fetch 即使 URL 一致也会
    返回 404。因此这里保持 DevTools 网络监听开启，让页面自己滚动、自己请求下一页。
    """

    page = _x_page(endpoint)
    ws = websocket.create_connection(
        page["webSocketDebuggerUrl"],
        timeout=20,
        origin=endpoint.rstrip("/"),
    )
    next_id = 1
    pending_body = {}
    search_requests = {}
    yielded_pages = 0

    def send(method, params=None):
        """发送 Chrome DevTools Protocol 命令。"""

        nonlocal next_id
        message_id = next_id
        next_id += 1
        ws.send(json.dumps({"id": message_id, "method": method, "params": params or {}}))
        return message_id

    def scroll_to_bottom():
        """触发 X 搜索结果加载下一页。"""

        send(
            "Runtime.evaluate",
            {
                "expression": "window.scrollTo(0, document.body.scrollHeight)",
                "awaitPromise": False,
                "returnByValue": True,
            },
        )

    search_url = (
        "https://x.com/search?q="
        + urllib.parse.quote(raw_query)
        + "&src=typed_query&f=live"
    )
    try:
        send("Network.enable")
        send("Runtime.enable")
        send("Page.enable")
        send("Page.navigate", {"url": search_url})
        page_started_at = time.time()
        while not max_pages or yielded_pages < max_pages:
            if yielded_pages > 0:
                scroll_to_bottom()
            while True:
                if time.time() - page_started_at > 90:
                    raise RuntimeError("90 秒内没有捕获到下一页 SearchTimeline 响应")
                try:
                    message = json.loads(ws.recv())
                except websocket.WebSocketTimeoutException:
                    scroll_to_bottom()
                    continue
                method = message.get("method")
                params = message.get("params", {})

                if method == "Network.requestWillBeSent":
                    url = params.get("request", {}).get("url", "")
                    if "/SearchTimeline?" in url:
                        request_id = params["requestId"]
                        search_requests[request_id] = {
                            "url": url,
                            "status": None,
                            "headers": {},
                        }
                elif method == "Network.responseReceived":
                    request_id = params.get("requestId")
                    if request_id in search_requests:
                        response = params.get("response", {})
                        search_requests[request_id]["status"] = response.get("status")
                        search_requests[request_id]["headers"] = response.get("headers", {})
                elif method == "Network.loadingFinished":
                    request_id = params.get("requestId")
                    if request_id in search_requests:
                        body_message_id = send("Network.getResponseBody", {"requestId": request_id})
                        pending_body[body_message_id] = request_id
                elif message.get("id") in pending_body:
                    request_id = pending_body.pop(message["id"])
                    request = search_requests[request_id]
                    body = message.get("result", {}).get("body", "")
                    if request["status"] != 200:
                        raise RuntimeError(f"SearchTimeline HTTP {request['status']}: {body[:500]}")
                    yielded_pages += 1
                    page_started_at = time.time()
                    yield json.loads(body), request["headers"]
                    break
    finally:
        ws.close()


def _evaluate(endpoint, expression, timeout=180):
    """在 X 页面中执行 JavaScript 并返回 JSON 可序列化结果。"""

    page = _x_page(endpoint)
    ws = websocket.create_connection(
        page["webSocketDebuggerUrl"],
        timeout=timeout,
        origin=endpoint.rstrip("/"),
    )
    try:
        ws.send(json.dumps({"id": 1, "method": "Runtime.enable"}))
        while True:
            if json.loads(ws.recv()).get("id") == 1:
                break
        ws.send(
            json.dumps(
                {
                    "id": 2,
                    "method": "Runtime.evaluate",
                    "params": {
                        "expression": expression,
                        "awaitPromise": True,
                        "returnByValue": True,
                    },
                }
            )
        )
        while True:
            message = json.loads(ws.recv())
            if message.get("id") != 2:
                continue
            if "exceptionDetails" in message:
                raise RuntimeError(json.dumps(message["exceptionDetails"], ensure_ascii=False))
            result = message["result"]["result"]
            if "value" not in result:
                raise RuntimeError(f"DevTools did not return a by-value result: {result}")
            return result["value"]
    finally:
        ws.close()


def _build_search_url(template, raw_query, cursor, count):
    """用真实 SearchTimeline 模板生成下一页 URL。"""

    template_variables = template["variables"]
    variables = {
        "rawQuery": raw_query,
        "count": count,
    }
    if cursor:
        variables["cursor"] = cursor
    for key in (
        "querySource",
        "product",
        "withGrokTranslatedBio",
        "withQuickPromoteEligibilityTweetFields",
    ):
        variables[key] = template_variables[key]

    params = {
        "variables": json.dumps(variables, separators=(",", ":")),
        "features": template["features"],
    }
    if template["field_toggles"] is not None:
        params["fieldToggles"] = template["field_toggles"]
    return (
        "https://x.com/i/api/graphql/"
        + template["query_id"]
        + "/SearchTimeline?"
        # X 前端的 URLSearchParams 会把空格编码为 %20；quote_plus 生成的 + 会导致该接口 404。
        + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    )


def _search_fetch_expression(url):
    """生成浏览器内 SearchTimeline fetch 脚本。"""

    return r"""
    (async () => {
      const url = __URL__;
      const mainScript = Array.from(document.scripts)
        .map(script => script.src)
        .find(src => src.includes('/responsive-web/client-web/main.') && src.endsWith('.js'));
      if (!mainScript) throw new Error('Cannot find X main JS script on page');
      const mainJs = await (await fetch(mainScript)).text();
      const bearer = mainJs.match(/Bearer ([A-Za-z0-9%._\-]+)/);
      if (!bearer) throw new Error('Cannot find X bearer token');
      const ct0 = (document.cookie.match(/(?:^|; )ct0=([^;]+)/) || [])[1];
      if (!ct0) throw new Error('Missing ct0 cookie; please login to X in this Chrome window');
      const response = await fetch(url, {
        credentials: 'include',
        headers: {
          Accept: 'application/json',
          authorization: 'Bearer ' + bearer[1],
          'x-csrf-token': decodeURIComponent(ct0),
          'x-twitter-active-user': 'yes',
          'x-twitter-auth-type': 'OAuth2Session',
          'x-twitter-client-language': 'en'
        }
      });
      const text = await response.text();
      const headers = Object.fromEntries(response.headers.entries());
      if (!response.ok) {
        return {ok: false, status: response.status, headers, body: text.slice(0, 500)};
      }
      return {ok: true, status: response.status, headers, body: text};
    })()
    """.replace("__URL__", json.dumps(url))


def _tweet_author(result):
    """读取 SearchTimeline Tweet result 的作者 screen_name。"""

    user = result.get("core", {}).get("user_results", {}).get("result", {})
    core = user.get("core", {})
    return core.get("screen_name")


def _tweet_text(result):
    """读取短帖或长帖的完整正文。"""

    note_text = (
        result.get("note_tweet", {})
        .get("note_tweet_results", {})
        .get("result", {})
        .get("text")
    )
    if isinstance(note_text, str) and note_text:
        return note_text
    direct_note_text = result.get("note_tweet_results", {}).get("result", {}).get("text")
    if isinstance(direct_note_text, str) and direct_note_text:
        return direct_note_text
    return result.get("legacy", {}).get("full_text", "")


def _tweet_tickers(result, text):
    """从正文和 X symbols 字段中提取 ticker。"""

    symbols = (
        result.get("note_tweet", {})
        .get("note_tweet_results", {})
        .get("result", {})
        .get("entity_set", {})
        .get("symbols", [])
    )
    legacy_symbols = result.get("legacy", {}).get("entities", {}).get("symbols", [])
    tickers = [
        match.group(1).rstrip(".")
        for match in re.finditer(r"(?<![A-Z0-9])\$([A-Z][A-Z0-9.]{0,9})(?![A-Z0-9])", text)
    ]
    tickers.extend(symbol.get("text", "").rstrip(".") for symbol in symbols + legacy_symbols)
    return sorted({ticker for ticker in tickers if ticker})


def _extract_rows_and_cursor(payload, screen_name):
    """从 SearchTimeline JSON 中提取 tweet 记录和 bottom cursor。"""

    rows = []
    seen_in_page = set()
    bottom_cursor = None

    def add_tweet(result):
        """把单个 Tweet result 转成项目统一 JSONL 结构。"""

        if not result or result.get("__typename") != "Tweet":
            return
        if _tweet_author(result) != screen_name:
            return
        legacy = result.get("legacy", {})
        tweet_id = result.get("rest_id")
        if not tweet_id or tweet_id in seen_in_page:
            return
        seen_in_page.add(tweet_id)
        text = _tweet_text(result)
        rows.append(
            {
                "tweet_id": tweet_id,
                "author": screen_name,
                "created_at": legacy.get("created_at", ""),
                "text": text,
                "url": "https://x.com/" + screen_name + "/status/" + tweet_id,
                "metrics": {
                    "replies": legacy.get("reply_count"),
                    "reposts": legacy.get("retweet_count"),
                    "quotes": legacy.get("quote_count"),
                    "likes": legacy.get("favorite_count"),
                    "bookmarks": legacy.get("bookmark_count"),
                    "views": int(result.get("views", {}).get("count"))
                    if result.get("views", {}).get("count")
                    else None,
                },
                "tickers": _tweet_tickers(result, text),
                "is_retweet": bool(legacy.get("retweeted_status_result")),
                "in_reply_to": legacy.get("in_reply_to_status_id_str"),
                "quoted_tweet_id": result.get("quoted_status_result", {})
                .get("result", {})
                .get("rest_id"),
            }
        )

    def walk(value):
        """递归遍历 timeline 响应，寻找主时间线 tweet 和底部 cursor。"""

        nonlocal bottom_cursor
        if isinstance(value, list):
            for child in value:
                walk(child)
            return
        if not isinstance(value, dict):
            return
        if isinstance(value.get("entryId"), str) and value["entryId"].startswith("cursor-bottom"):
            cursor_value = value.get("content", {}).get("value")
            if isinstance(cursor_value, str):
                bottom_cursor = cursor_value
        tweet_result = value.get("itemContent", {}).get("tweet_results", {}).get("result")
        if tweet_result:
            add_tweet(tweet_result)
        for child in value.values():
            walk(child)

    walk(payload)
    return rows, bottom_cursor


def main():
    """命令行入口。"""

    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default="http://127.0.0.1:9223")
    parser.add_argument("--screen-name", required=True)
    parser.add_argument("--raw-query", required=True)
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--out", required=True)
    parser.add_argument("--cursor-file", required=True)
    parser.add_argument("--page-size", type=int, default=20)
    parser.add_argument("--delay-seconds", type=float, default=1.0)
    parser.add_argument("--max-pages", type=int, default=0)
    args = parser.parse_args()

    output_path = Path(args.out)
    cursor_path = Path(args.cursor_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cursor_path.parent.mkdir(parents=True, exist_ok=True)

    seen = _load_seen(output_path)
    if cursor_path.exists():
        _load_cursor(cursor_path, args.raw_query)
    print("search_scroll", "resume_count", len(seen), flush=True)

    with output_path.open("a", encoding="utf-8") as output:
        for page_number, (payload, headers) in enumerate(
            _search_payload_stream(args.endpoint, args.raw_query, args.max_pages),
            start=1,
        ):
            rows, cursor = _extract_rows_and_cursor(payload, args.screen_name)
            new_count = 0
            for row in rows:
                tweet_id = row["tweet_id"]
                if tweet_id in seen:
                    continue
                seen.add(tweet_id)
                output.write(_safe_json_line(row) + "\n")
                new_count += 1
                if len(seen) >= args.limit:
                    break
            output.flush()
            cursor_path.write_text(
                json.dumps(
                    {
                        "raw_query": args.raw_query,
                        "cursor": cursor,
                        "count": len(seen),
                        "page": page_number,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            print(
                "page",
                page_number,
                "page_rows",
                len(rows),
                "new",
                new_count,
                "total",
                len(seen),
                "has_cursor",
                bool(cursor),
                "remaining",
                headers.get("x-rate-limit-remaining") or headers.get("X-Rate-Limit-Remaining"),
                flush=True,
            )
            if len(seen) >= args.limit:
                break
            if not cursor:
                raise RuntimeError("SearchTimeline response did not include bottom cursor")
            time.sleep(args.delay_seconds)


if __name__ == "__main__":
    main()
