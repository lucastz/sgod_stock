"""用 X 单帖接口刷新已抓取 JSONL 的完整 text 字段。

用于修复 legacy.full_text 截断问题。脚本通过已登录 Chrome 页面发请求，不读取或导出
cookie 文件；每条修复后写入临时文件，结束后再替换原文件。
"""

import argparse
import json
import time
import urllib.request
from pathlib import Path

import websocket


def _x_page(endpoint):
    """找到一个 X 页面标签页。"""

    payload = urllib.request.urlopen(endpoint.rstrip("/") + "/json/list", timeout=5).read()
    pages = json.loads(payload.decode("utf-8"))
    for page in pages:
        if page.get("type") == "page" and "x.com" in page.get("url", ""):
            return page
    raise RuntimeError("未找到 X 页面，请在 DevTools Chrome 中打开 X")


def _evaluate(endpoint, expression, timeout=180):
    """在 X 页面中执行 JavaScript。"""

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
            result = message["result"]["result"]
            if "exceptionDetails" in result:
                raise RuntimeError(json.dumps(result["exceptionDetails"], ensure_ascii=False))
            return result.get("value")
    finally:
        ws.close()


def _refresh_expression(tweet_id):
    """生成浏览器内单条刷新脚本。"""

    return r"""
    (async () => {
      const tweetId = __TWEET_ID__;
      if (!window.__SGOD_X_TWEET_META) {
        const mainScript = Array.from(document.scripts)
          .map(script => script.src)
          .find(src => src.includes('/responsive-web/client-web/main.') && src.endsWith('.js'));
        const mainJs = await (await fetch(mainScript)).text();
        const op = mainJs.match(/queryId:\"([^\"]+)\",operationName:\"TweetResultByRestId\",operationType:\"[^\"]+\",metadata:\{featureSwitches:\[(.*?)\],fieldToggles:\[(.*?)\]/);
        if (!op) throw new Error('Cannot find TweetResultByRestId metadata');
        const bearer = mainJs.match(/Bearer ([A-Za-z0-9%._\-]+)/);
        if (!bearer) throw new Error('Cannot find X bearer token');
        const parseToggles = raw => Object.fromEntries(
          raw.split(',')
            .map(item => item.trim().replace(/^\"|\"$/g, ''))
            .filter(Boolean)
            .map(item => [item, true])
        );
        window.__SGOD_X_TWEET_META = {
          queryId: op[1],
          features: parseToggles(op[2]),
          fieldToggles: parseToggles(op[3]),
          bearer: bearer[1]
        };
      }
      const meta = window.__SGOD_X_TWEET_META;
      const ct0 = (document.cookie.match(/(?:^|; )ct0=([^;]+)/) || [])[1];
      if (!ct0) throw new Error('Missing ct0 cookie; please login to X');
      const headers = {
        Accept: 'application/json',
        authorization: 'Bearer ' + meta.bearer,
        'x-csrf-token': decodeURIComponent(ct0),
        'x-twitter-active-user': 'yes',
        'x-twitter-auth-type': 'OAuth2Session',
        'x-twitter-client-language': 'en'
      };
      const variables = {
        tweetId,
        withCommunity: false,
        includePromotedContent: false,
        withVoice: false
      };
      const params = new URLSearchParams({
        variables: JSON.stringify(variables),
        features: JSON.stringify(meta.features),
        fieldToggles: JSON.stringify(meta.fieldToggles)
      });
      const response = await fetch(
        `https://x.com/i/api/graphql/${meta.queryId}/TweetResultByRestId?${params.toString()}`,
        {credentials: 'include', headers}
      );
      const responseText = await response.text();
      const responseHeaders = Object.fromEntries(response.headers.entries());
      if (!response.ok) {
        return {ok: false, status: response.status, headers: responseHeaders, body: responseText.slice(0, 300)};
      }
      const data = JSON.parse(responseText);
      const result = data?.data?.tweetResult?.result;
      if (!result || result.__typename !== 'Tweet') {
        return {ok: false, status: 0, headers: responseHeaders, body: 'missing tweet result'};
      }
      const text = result.note_tweet?.note_tweet_results?.result?.text ||
        result.note_tweet_results?.result?.text ||
        result.legacy?.full_text ||
        '';
      const symbols = result.note_tweet?.note_tweet_results?.result?.entity_set?.symbols ||
        result.legacy?.entities?.symbols ||
        [];
      const tickers = Array.from(new Set(
        [
          ...Array.from(text.matchAll(/(?<![A-Z0-9])\$([A-Z][A-Z0-9.]{0,9})(?![A-Z0-9])/g)).map(match => match[1].replace(/\.+$/g, '')),
          ...symbols.map(symbol => symbol.text).filter(Boolean).map(text => text.replace(/\.+$/g, ''))
        ]
      )).sort();
      return {ok: true, status: response.status, headers: responseHeaders, text, tickers};
    })()
    """.replace("__TWEET_ID__", json.dumps(tweet_id))


def main():
    """命令行入口。"""

    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default="http://127.0.0.1:9223")
    parser.add_argument("--in-out", required=True)
    parser.add_argument("--progress-file", required=True)
    parser.add_argument("--delay-seconds", type=float, default=0.5)
    args = parser.parse_args()

    jsonl_path = Path(args.in_out)
    progress_path = Path(args.progress_file)
    temp_path = jsonl_path.with_suffix(".refreshing.jsonl")

    rows = [
        json.loads(line)
        for line in jsonl_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    start_index = 0
    if progress_path.exists():
        start_index = json.loads(progress_path.read_text(encoding="utf-8")).get("index", 0)

    if start_index == 0:
        temp_path.write_text("", encoding="utf-8")
    elif not temp_path.exists():
        raise RuntimeError("progress exists but temp refresh file is missing")

    with temp_path.open("a", encoding="utf-8") as output:
        for index, row in enumerate(rows[start_index:], start=start_index):
            result = _evaluate(args.endpoint, _refresh_expression(row["tweet_id"]))
            if not result.get("ok"):
                if result.get("status") == 429:
                    reset = int(result.get("headers", {}).get("x-rate-limit-reset", 0))
                    wait_seconds = max(60, reset - int(time.time()) + 5)
                    print("rate_limited", "wait_seconds", wait_seconds, "index", index)
                    time.sleep(wait_seconds)
                    result = _evaluate(args.endpoint, _refresh_expression(row["tweet_id"]))
                    if not result.get("ok"):
                        raise RuntimeError(json.dumps(result, ensure_ascii=False))
                else:
                    raise RuntimeError(json.dumps(result, ensure_ascii=False))

            row["text"] = result["text"]
            row["tickers"] = result["tickers"]
            output.write(json.dumps(row, ensure_ascii=False) + "\n")
            output.flush()
            progress_path.write_text(
                json.dumps({"index": index + 1, "total": len(rows)}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            if (index + 1) % 25 == 0:
                print("refreshed", index + 1, "of", len(rows))
            time.sleep(args.delay_seconds)

    jsonl_path.write_text(temp_path.read_text(encoding="utf-8"), encoding="utf-8")
    progress_path.write_text(
        json.dumps({"index": len(rows), "total": len(rows), "done": True}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("refreshed", len(rows), "rows")


if __name__ == "__main__":
    main()
