"""通过 Chrome DevTools 使用已登录 X 会话。

本模块只在页面上下文里执行 JavaScript fetch，不读取或导出 cookie 文件。Chrome
必须用 `--remote-debugging-port` 启动；如果没有调试端口，调用方会收到明确错误。
"""

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List

import websocket


@dataclass(frozen=True)
class ChromeTab:
    """DevTools 暴露的一个浏览器标签页。"""

    id: str
    title: str
    url: str
    web_socket_debugger_url: str


class ChromeDevToolsClient:
    """Chrome DevTools Protocol 的最小客户端。

    这里只实现本项目需要的标签页发现和 Runtime.evaluate，避免引入复杂浏览器自动化。
    """

    def __init__(self, endpoint: str = "http://127.0.0.1:9222") -> None:
        self.endpoint = endpoint.rstrip("/")
        self._message_id = 0

    def list_tabs(self) -> List[ChromeTab]:
        """列出当前可调试的 Chrome 标签页。"""

        try:
            response = urllib.request.urlopen(f"{self.endpoint}/json/list", timeout=5)
        except urllib.error.URLError as exc:
            raise RuntimeError(
                "无法连接 Chrome DevTools。请用 --remote-debugging-port=9222 启动 Chrome，"
                "并在该 Chrome 中打开 X 页面。"
            ) from exc
        with response:
            payload = json.loads(response.read().decode("utf-8"))
        tabs = []  # type: List[ChromeTab]
        for item in payload:
            ws_url = item.get("webSocketDebuggerUrl")
            if not ws_url:
                continue
            tabs.append(
                ChromeTab(
                    id=item["id"],
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    web_socket_debugger_url=ws_url,
                )
            )
        return tabs

    def find_x_tab(self) -> ChromeTab:
        """找到一个已打开的 X/Twitter 标签页。"""

        for tab in self.list_tabs():
            if "x.com" in tab.url or "twitter.com" in tab.url:
                return tab
        raise RuntimeError("未找到 X/Twitter 标签页，请先在调试版 Chrome 中打开目标页面")

    def evaluate(self, tab: ChromeTab, expression: str, await_promise: bool = True) -> Any:
        """在指定标签页执行 JavaScript 并返回 JSON 可序列化结果。"""

        ws = websocket.create_connection(
            tab.web_socket_debugger_url,
            timeout=10,
            origin=self.endpoint,
        )
        try:
            message_id = self._next_message_id()
            self._send_and_wait(ws, message_id, {"method": "Runtime.enable"})
            message_id = self._next_message_id()
            ws.send(
                json.dumps(
                    {
                        "id": message_id,
                        "method": "Runtime.evaluate",
                        "params": {
                            "expression": expression,
                            "awaitPromise": await_promise,
                            "returnByValue": True,
                        },
                    }
                )
            )
            while True:
                message = json.loads(ws.recv())
                if message.get("id") != message_id:
                    continue
                if "exceptionDetails" in message:
                    raise RuntimeError(json.dumps(message["exceptionDetails"], ensure_ascii=False))
                result = message["result"]["result"]
                if "value" not in result:
                    raise RuntimeError(f"DevTools did not return a by-value result: {result}")
                return result["value"]
        finally:
            ws.close()

    def _next_message_id(self) -> int:
        """生成 DevTools 命令 id。"""

        self._message_id += 1
        return self._message_id

    def _send_and_wait(self, ws: websocket.WebSocket, message_id: int, payload: dict) -> None:
        """发送 DevTools 命令并等待对应 id 的响应。

        Chrome 有时在 Runtime domain 未启用时不会稳定返回 evaluate 响应，因此先显式启用。
        """

        ws.send(json.dumps({"id": message_id, **payload}))
        while True:
            message = json.loads(ws.recv())
            if message.get("id") == message_id:
                if "error" in message:
                    raise RuntimeError(json.dumps(message["error"], ensure_ascii=False))
                return

    def fetch_json_from_x_tab(self, url: str, bearer_token: str = None) -> Dict[str, Any]:
        """在已登录 X 页面内请求 JSON。

        fetch 会自动携带该页面当前登录态。函数只返回响应 JSON，不暴露 cookie。
        """

        auth_header = f"Bearer {bearer_token}" if bearer_token else ""
        expression = f"""
        (async () => {{
          const headers = {{ 'Accept': 'application/json', 'x-twitter-active-user': 'yes', 'x-twitter-client-language': 'en' }};
          const ct0 = (document.cookie.match(/(?:^|; )ct0=([^;]+)/) || [])[1];
          if (ct0) {{
            headers['x-csrf-token'] = decodeURIComponent(ct0);
            headers['x-twitter-auth-type'] = 'OAuth2Session';
          }}
          if ({json.dumps(bool(auth_header))}) {{
            headers['authorization'] = {json.dumps(auth_header)};
          }}
          const response = await fetch({json.dumps(url)}, {{
            credentials: 'include',
            headers
          }});
          if (!response.ok) {{
            const body = await response.text();
            throw new Error(`HTTP ${{response.status}} ${{response.statusText}} ${{body.slice(0, 500)}}`);
          }}
          return await response.json();
        }})()
        """
        tab = self.find_x_tab()
        value = self.evaluate(tab, expression)
        if not isinstance(value, dict):
            raise RuntimeError("X fetch did not return a JSON object")
        return value
