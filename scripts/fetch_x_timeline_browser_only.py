"""通过已登录 Chrome DevTools 分批抓取 X 用户时间线。

这个脚本不直接请求 X 网络接口，不读取或导出 cookie 文件；所有 X 请求都在已登录的
浏览器页面内部执行。脚本只通过 localhost DevTools 收取 API 返回的公开帖子 JSON。
"""

import argparse
import json
import time
import urllib.request
from pathlib import Path

import websocket


def _devtools_page(endpoint):
    """找到一个 X 页面标签页。"""

    payload = urllib.request.urlopen(endpoint.rstrip("/") + "/json/list", timeout=5).read()
    pages = json.loads(payload.decode("utf-8"))
    for page in pages:
        if page.get("type") == "page" and "x.com" in page.get("url", ""):
            return page
    raise RuntimeError("未找到 X 页面，请在 DevTools Chrome 中打开 https://x.com")


def _evaluate(endpoint, expression, timeout=120):
    """在 X 页面中执行 JavaScript。"""

    page = _devtools_page(endpoint)
    ws = websocket.create_connection(
        page["webSocketDebuggerUrl"],
        timeout=timeout,
        origin=endpoint.rstrip("/"),
    )
    try:
        ws.send(json.dumps({"id": 1, "method": "Runtime.enable"}))
        while True:
            message = json.loads(ws.recv())
            if message.get("id") == 1:
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
            result = message["result"]["result"]
            exception = result.get("exceptionDetails")
            if exception:
                raise RuntimeError(json.dumps(exception, ensure_ascii=False))
            return result.get("value")
    finally:
        ws.close()


def _page_expression(screen_name, user_id, cursor):
    """生成浏览器内单页抓取脚本。

    元数据缓存在 window.__SGOD_X_TIMELINE_META 中，避免每页重复解析前端包。
    """

    return r"""
    (async () => {
      const screenName = __SCREEN_NAME__;
      const userId = __USER_ID__;
      const cursor = __CURSOR__;
      if (!window.__SGOD_X_TIMELINE_META) {
        const mainScript = Array.from(document.scripts)
          .map(script => script.src)
          .find(src => src.includes('/responsive-web/client-web/main.') && src.endsWith('.js'));
        if (!mainScript) throw new Error('Cannot find X main JS script on page');
        const mainJs = await (await fetch(mainScript)).text();
        const op = mainJs.match(/queryId:\"([^\"]+)\",operationName:\"UserTweets\",operationType:\"[^\"]+\",metadata:\{featureSwitches:\[(.*?)\],fieldToggles:\[(.*?)\]/);
        if (!op) throw new Error('Cannot find UserTweets operation metadata');
        const bearer = mainJs.match(/Bearer ([A-Za-z0-9%._\-]+)/);
        if (!bearer) throw new Error('Cannot find X bearer token');
        const parseToggles = raw => Object.fromEntries(
          raw.split(',')
            .map(item => item.trim().replace(/^\"|\"$/g, ''))
            .filter(Boolean)
            .map(item => [item, true])
        );
        window.__SGOD_X_TIMELINE_META = {
          queryId: op[1],
          features: parseToggles(op[2]),
          fieldToggles: parseToggles(op[3]),
          bearer: bearer[1]
        };
      }
      const meta = window.__SGOD_X_TIMELINE_META;
      const ct0 = (document.cookie.match(/(?:^|; )ct0=([^;]+)/) || [])[1];
      if (!ct0) throw new Error('Missing ct0 cookie; please login to X in this Chrome window');
      const headers = {
        Accept: 'application/json',
        authorization: 'Bearer ' + meta.bearer,
        'x-csrf-token': decodeURIComponent(ct0),
        'x-twitter-active-user': 'yes',
        'x-twitter-auth-type': 'OAuth2Session',
        'x-twitter-client-language': 'en'
      };
      const variables = {
        userId,
        count: 100,
        includePromotedContent: false,
        withQuickPromoteEligibilityTweetFields: false,
        withVoice: false
      };
      if (cursor) variables.cursor = cursor;
      const params = new URLSearchParams({
        variables: JSON.stringify(variables),
        features: JSON.stringify(meta.features),
        fieldToggles: JSON.stringify(meta.fieldToggles)
      });
      const response = await fetch(
        `https://x.com/i/api/graphql/${meta.queryId}/UserTweets?${params.toString()}`,
        {credentials: 'include', headers}
      );
      const text = await response.text();
      const responseHeaders = Object.fromEntries(response.headers.entries());
      if (!response.ok) {
        return {ok: false, status: response.status, headers: responseHeaders, body: text.slice(0, 500)};
      }
      const data = JSON.parse(text);
      const seen = new Set();
      const rows = [];
      let bottomCursor = null;

      function readTimelineBottomCursor(payload) {
        const instructions = payload?.data?.user?.result?.timeline?.timeline?.instructions || [];
        for (const instruction of instructions) {
          const entries = instruction.entries || (instruction.entry ? [instruction.entry] : []);
          for (const entry of entries) {
            if (typeof entry.entryId === 'string' && entry.entryId.startsWith('cursor-bottom')) {
              return entry.content && typeof entry.content.value === 'string' ? entry.content.value : null;
            }
          }
        }
        return null;
      }

      function addTweet(result) {
        if (!result || result.__typename !== 'Tweet' || !result.legacy || !result.rest_id) return;
        const id = result.rest_id;
        if (seen.has(id)) return;
        seen.add(id);
        const legacy = result.legacy || {};
        const noteText = result.note_tweet?.note_tweet_results?.result?.text ||
          result.note_tweet_results?.result?.text ||
          null;
        const fullText = noteText || legacy.full_text || '';
        const tickers = Array.from(fullText.matchAll(/(?<![A-Z0-9])\$([A-Z][A-Z0-9.]{0,9})(?![A-Z0-9])/g)).map(match => match[1].replace(/\.+$/g, ''));
        rows.push({
          tweet_id: id,
          author: screenName,
          created_at: legacy.created_at || '',
          text: fullText,
          url: `https://x.com/${screenName}/status/${id}`,
          metrics: {
            replies: legacy.reply_count ?? null,
            reposts: legacy.retweet_count ?? null,
            quotes: legacy.quote_count ?? null,
            likes: legacy.favorite_count ?? null,
            bookmarks: legacy.bookmark_count ?? null,
            views: result.views && result.views.count ? Number(result.views.count) : null
          },
          tickers: Array.from(new Set(tickers)).sort(),
          is_retweet: Boolean(legacy.retweeted_status_result),
          in_reply_to: legacy.in_reply_to_status_id_str || null,
          quoted_tweet_id: result.quoted_status_result && result.quoted_status_result.result ? result.quoted_status_result.result.rest_id || null : null
        });
      }

      function walk(value) {
        if (Array.isArray(value)) {
          for (const child of value) walk(child);
          return;
        }
        if (!value || typeof value !== 'object') return;
        if (value.itemContent && value.itemContent.tweet_results) addTweet(value.itemContent.tweet_results.result);
        for (const child of Object.values(value)) walk(child);
      }
      walk(data);
      bottomCursor = readTimelineBottomCursor(data);
      return {ok: true, status: response.status, headers: responseHeaders, rows, cursor: bottomCursor};
    })()
    """.replace("__SCREEN_NAME__", json.dumps(screen_name)).replace(
        "__USER_ID__", json.dumps(user_id)
    ).replace("__CURSOR__", json.dumps(cursor))


def _load_seen(output_path):
    """读取已保存 tweet id，支持断点续抓。"""

    seen = set()
    if not output_path.exists():
        return seen
    with output_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                seen.add(json.loads(line)["tweet_id"])
    return seen


def _load_cursor(cursor_path):
    """读取上次保存的 cursor。"""

    if not cursor_path.exists():
        return None
    payload = json.loads(cursor_path.read_text(encoding="utf-8"))
    return payload.get("cursor")


def main():
    """命令行入口。"""

    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default="http://127.0.0.1:9223")
    parser.add_argument("--screen-name", required=True)
    parser.add_argument("--user-id", required=True)
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--out", required=True)
    parser.add_argument("--cursor-file", required=True)
    parser.add_argument("--delay-seconds", type=float, default=2.0)
    parser.add_argument(
        "--max-pages",
        type=int,
        default=0,
        help="最多请求多少个时间线分页；0 表示一直抓到 limit，用于诊断 cursor 是否重复。",
    )
    args = parser.parse_args()

    output_path = Path(args.out)
    cursor_path = Path(args.cursor_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cursor_path.parent.mkdir(parents=True, exist_ok=True)

    seen = _load_seen(output_path)
    cursor = _load_cursor(cursor_path)
    print("resume_count", len(seen), "has_cursor", bool(cursor), flush=True)

    with output_path.open("a", encoding="utf-8") as output:
        page_count = 0
        while len(seen) < args.limit:
            if args.max_pages and page_count >= args.max_pages:
                print("max_pages_reached", args.max_pages, "total", len(seen), flush=True)
                break

            result = _evaluate(
                args.endpoint,
                _page_expression(args.screen_name, args.user_id, cursor),
                timeout=180,
            )
            page_count += 1
            if not result.get("ok"):
                if result.get("status") == 429:
                    reset = int(result.get("headers", {}).get("x-rate-limit-reset", 0))
                    wait_seconds = max(60, reset - int(time.time()) + 5)
                    print(
                        "rate_limited",
                        "wait_seconds",
                        wait_seconds,
                        "collected",
                        len(seen),
                        flush=True,
                    )
                    time.sleep(wait_seconds)
                    continue
                raise RuntimeError(json.dumps(result, ensure_ascii=False))

            new_count = 0
            for row in result.get("rows", []):
                tweet_id = row["tweet_id"]
                if tweet_id in seen:
                    continue
                seen.add(tweet_id)
                output.write(json.dumps(row, ensure_ascii=False) + "\n")
                new_count += 1
                if len(seen) >= args.limit:
                    break
            output.flush()

            cursor = result.get("cursor")
            cursor_path.write_text(
                json.dumps({"cursor": cursor, "count": len(seen)}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(
                "page",
                page_count,
                "page_rows",
                len(result.get("rows", [])),
                "new",
                new_count,
                "total",
                len(seen),
                "has_cursor",
                bool(cursor),
                flush=True,
            )
            if not cursor:
                raise RuntimeError("X response did not include bottom cursor")
            time.sleep(args.delay_seconds)


if __name__ == "__main__":
    main()
