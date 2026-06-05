"""命令行入口。

CLI 负责把真实输入文件、X 抓取接口和评分模型串起来。所有命令失败时直接抛出
明确错误，方便调试数据源或字段问题。
"""

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from .chrome_devtools import ChromeDevToolsClient
from .reporting import load_tweets_jsonl, render_research_report, write_markdown
from .scoring import load_candidates_csv, score_candidate
from .timeline import extract_bottom_cursor, extract_tweets
from .text_filter import filter_tweets
from .x_frontend import (
    XFrontendClient,
    article_plain_text,
    build_graphql_url,
    tweet_id_from_url,
)


def _cmd_chrome_status(args: argparse.Namespace) -> None:
    """检查 Chrome DevTools 是否可连接。"""

    client = ChromeDevToolsClient(args.endpoint)
    tabs = client.list_tabs()
    print(json.dumps([asdict(tab) for tab in tabs], ensure_ascii=False, indent=2))


def _cmd_fetch_article(args: argparse.Namespace) -> None:
    """抓取 X Article 并写出 JSON。"""

    client = XFrontendClient()
    tweet_id = tweet_id_from_url(args.tweet)
    article = client.fetch_tweet_article(tweet_id)
    text = article_plain_text(article)
    output = {
        "tweet_id": tweet_id,
        "title": article.get("title"),
        "plain_text": text,
        "raw": article if args.include_raw else None,
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out_path}")


def _cmd_score_candidates(args: argparse.Namespace) -> None:
    """读取候选公司 CSV 并输出排序结果。"""

    inputs = load_candidates_csv(Path(args.candidates))
    scored = [score_candidate(item) for item in inputs]
    payload = [
        {
            "ticker": item.candidate.ticker,
            "company_name": item.candidate.company_name,
            "exchange": item.candidate.exchange,
            "total_score": item.score.total_score,
            "positive_score": item.score.positive_score,
            "penalty_score": item.score.penalty_score,
            "fields": item.score.fields,
            "review_flags": list(item.score.review_flags),
            "evidence_links": list(item.candidate.evidence_links),
        }
        for item in sorted(scored, key=lambda row: row.score.total_score, reverse=True)
    ]
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out_path}")


def _cmd_fetch_user_tweets_auth(args: argparse.Namespace) -> None:
    """通过已登录 Chrome 会话抓取用户时间线。"""

    x_client = XFrontendClient()
    profile = x_client.fetch_user_profile(args.screen_name)
    user_id = profile["rest_id"]
    operation = x_client.operation("UserTweets")
    chrome = ChromeDevToolsClient(args.endpoint)

    cursor = None  # type: Optional[str]
    records_by_id = {}
    page_index = 0
    while len(records_by_id) < args.limit:
        page_index += 1
        variables = {
            "userId": user_id,
            "count": args.page_size,
            "includePromotedContent": False,
            "withQuickPromoteEligibilityTweetFields": False,
            "withVoice": False,
        }
        if cursor:
            variables["cursor"] = cursor
        url = build_graphql_url(operation, variables)
        data = chrome.fetch_json_from_x_tab(url, bearer_token=x_client.bearer)
        page_records = extract_tweets(data, args.screen_name)
        for record in page_records:
            records_by_id.setdefault(record.tweet_id, record)
            if len(records_by_id) >= args.limit:
                break

        next_cursor = extract_bottom_cursor(data)
        if not next_cursor:
            if len(records_by_id) < args.limit:
                raise RuntimeError(
                    f"X timeline returned no bottom cursor on page {page_index}; "
                    f"collected {len(records_by_id)} tweets, requested {args.limit}"
                )
            break
        if next_cursor == cursor:
            raise RuntimeError("X timeline bottom cursor did not advance")
        cursor = next_cursor

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        for record in records_by_id.values():
            payload = asdict(record)
            if not args.include_raw:
                payload["raw"] = None
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    print(f"wrote {len(records_by_id)} tweets to {out_path}")


def _cmd_report(args: argparse.Namespace) -> None:
    """根据帖子、长文和候选评分生成研究报告。"""

    tweets = load_tweets_jsonl(Path(args.tweets)) if args.tweets else []
    tweets = filter_tweets(tweets)
    article_text = None
    if args.article:
        article_payload = json.loads(Path(args.article).read_text(encoding="utf-8"))
        article_text = article_payload.get("plain_text")
    scored = []
    if args.candidates:
        scored = [score_candidate(item) for item in load_candidates_csv(Path(args.candidates))]
    content = render_research_report(tweets, article_text, scored)
    write_markdown(Path(args.out), content)
    print(f"wrote {args.out}")


def build_parser() -> argparse.ArgumentParser:
    """构造 CLI 参数解析器。"""

    parser = argparse.ArgumentParser(prog="sgod-stock")
    subparsers = parser.add_subparsers(dest="command")

    chrome_status = subparsers.add_parser("chrome-status")
    chrome_status.add_argument("--endpoint", default="http://127.0.0.1:9222")
    chrome_status.set_defaults(func=_cmd_chrome_status)

    fetch_article = subparsers.add_parser("fetch-article")
    fetch_article.add_argument("--tweet", required=True)
    fetch_article.add_argument("--out", required=True)
    fetch_article.add_argument("--include-raw", action="store_true")
    fetch_article.set_defaults(func=_cmd_fetch_article)

    fetch_tweets = subparsers.add_parser("fetch-user-tweets-auth")
    fetch_tweets.add_argument("--screen-name", default="aleabitoreddit")
    fetch_tweets.add_argument("--limit", type=int, default=1000)
    fetch_tweets.add_argument("--page-size", type=int, default=100)
    fetch_tweets.add_argument("--endpoint", default="http://127.0.0.1:9222")
    fetch_tweets.add_argument("--out", required=True)
    fetch_tweets.add_argument("--include-raw", action="store_true")
    fetch_tweets.set_defaults(func=_cmd_fetch_user_tweets_auth)

    score = subparsers.add_parser("score-candidates")
    score.add_argument("--candidates", required=True)
    score.add_argument("--out", required=True)
    score.set_defaults(func=_cmd_score_candidates)

    report = subparsers.add_parser("report")
    report.add_argument("--tweets")
    report.add_argument("--article")
    report.add_argument("--candidates")
    report.add_argument("--out", required=True)
    report.set_defaults(func=_cmd_report)

    return parser


def main() -> None:
    """CLI 主函数。"""

    parser = build_parser()
    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        raise SystemExit(2)
    try:
        args.func(args)
    except RuntimeError as exc:
        raise SystemExit(str(exc))


if __name__ == "__main__":
    main()
