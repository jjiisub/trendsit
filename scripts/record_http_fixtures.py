"""수집 테스트용 HTTP 픽스처 녹화: 실제 네트워크로 좁은 기간을 한 번 수집하며 오간 응답을 저장한다.

사용: uv run python scripts/record_http_fixtures.py <이름> --since YYYY-MM-DD --until YYYY-MM-DD [--max-items N]
결과: tests/fixtures/http/<이름>/index.json(URL → 파일, 상태, 형식) + 본문 파일(gzip), ytdlp.json(yt-dlp 출력 요약)
- 피드는 기간 앞뒤 3일 밖 항목을 지우되 기간보다 오래된 항목 1개는 남긴다(RSS가 기간을 덮는지 판정이 녹화 때와 같게)
- HTML은 script, style, svg, 주석을 지워 크기를 줄인다(본문 구조는 그대로)
테스트는 이 파일만으로 수집을 재현한다(네트워크 없음).
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import shutil
import tempfile
from datetime import UTC, date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import feedparser
import httpx

from trendsit.collect import youtube
from trendsit.collect.fetch import Fetcher
from trendsit.collect.run import collect

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "fixtures" / "http"


class Recorder(httpx.BaseTransport):
    """실제로 보내고 응답을 기록한다. existing(--extend)이 있으면 이미 녹화한 URL은 네트워크 없이 그 응답을 쓴다."""

    def __init__(self, existing: dict[str, dict[str, Any]] | None = None) -> None:
        self.inner = httpx.HTTPTransport()
        self.records: list[dict[str, Any]] = []
        self.existing = existing or {}

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        old = self.existing.get(str(request.url))
        if old is not None:
            headers = {"content-type": old["content_type"]} | ({"location": old["location"]} if old["location"] else {})
            return httpx.Response(old["status"], headers=headers, content=old["body"], request=request)
        resp = self.inner.handle_request(request)
        body = resp.read()
        self.records.append({"url": str(request.url), "status": resp.status_code,
                             "content_type": resp.headers.get("content-type", ""),
                             "location": resp.headers.get("location"), "body": body})
        # 본문은 이미 압축을 푼 상태라 압축·길이 헤더는 빼고 넘긴다
        headers = [(k, v) for k, v in resp.headers.items()
                   if k.lower() not in ("content-encoding", "content-length", "transfer-encoding")]
        return httpx.Response(resp.status_code, headers=headers, content=body, request=request)


def trim_feed(text: str, since: date, until: date) -> str:
    """기간 앞뒤 3일 안 항목 + 기간보다 오래된 항목 1개만 남긴다."""
    tag = "entry" if "<entry" in text else "item"
    blocks = list(re.finditer(rf"<{tag}[\s>].*?</{tag}>", text, re.S))
    if not blocks:
        return text
    lo, hi = since - timedelta(days=3), until + timedelta(days=3)
    keep, older_kept = [], False
    for m in blocks:
        parsed = feedparser.parse(f"<rss><channel>{m.group()}</channel></rss>" if tag == "item"
                                  else f'<feed xmlns="http://www.w3.org/2005/Atom">{m.group()}</feed>')
        e = parsed.entries[0] if parsed.entries else {}
        ts = e.get("published_parsed") or e.get("updated_parsed")
        d = datetime(*ts[:6], tzinfo=UTC).astimezone(timezone(timedelta(hours=9))).date() if ts else None
        if d is None or lo <= d <= hi:
            keep.append(m)
        elif d < lo and not older_kept:
            keep.append(m)
            older_kept = True
    head, tail = text[: blocks[0].start()], text[blocks[-1].end():]
    return head + "\n".join(m.group() for m in keep) + tail


def trim_html(text: str) -> str:
    for pat in (r"<script\b.*?</script>", r"<style\b.*?</style>", r"<svg\b.*?</svg>", r"<!--.*?-->",
                r"<noscript\b.*?</noscript>"):
        text = re.sub(pat, "", text, flags=re.S | re.I)
    return re.sub(r"\n\s*\n+", "\n", text)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("--since", required=True)
    ap.add_argument("--until", required=True)
    ap.add_argument("--max-items", type=int, default=3)
    ap.add_argument("--source")
    ap.add_argument("--extend", action="store_true",
                    help="이미 녹화한 응답은 그대로 쓰고, 코드가 새로 요청하는 URL만 실제로 받아 보탠다")
    args = ap.parse_args()
    since, until = date.fromisoformat(args.since), date.fromisoformat(args.until)

    out = OUT / args.name
    existing: dict[str, dict[str, Any]] = {}
    old_index: dict[str, Any] = {}
    old_yt: dict[str, Any] = {}
    if args.extend and (out / "index.json").exists():
        old_index = json.loads((out / "index.json").read_text(encoding="utf-8"))
        for url, meta in old_index.items():
            existing[url] = meta | {"body": gzip.decompress((out / meta["file"]).read_bytes())}
        if (out / "ytdlp.json").exists():
            old_yt = json.loads((out / "ytdlp.json").read_text(encoding="utf-8"))
    rec = Recorder(existing)
    yt_calls: dict[str, Any] = {}

    def ytdlp(cli_args: list[str]) -> dict[str, Any] | None:
        key = " ".join(cli_args)
        if key in old_yt:
            yt_calls[key] = old_yt[key]
            return old_yt[key]
        out = youtube.run_ytdlp(cli_args)
        if out is not None:  # 필요한 칸만(원본은 수 MB)
            keep = ("id", "title", "description", "duration", "timestamp", "upload_date", "chapters")
            slim = {k: out.get(k) for k in keep if k in out}
            slim["subtitles"] = {k: [] for k in (out.get("subtitles") or {})}
            slim["automatic_captions"] = {k: [] for k in list(out.get("automatic_captions") or {})[:3]}
            if "entries" in out:
                slim["entries"] = [{k: e.get(k) for k in ("id", "title", "timestamp", "description")}
                                   for e in out["entries"]]
            out = slim
        yt_calls[" ".join(cli_args)] = out
        return out

    tmp = Path(tempfile.mkdtemp())
    fetcher = Fetcher(None, use_cache=False, transport=rec)
    res = collect(since, until, only=args.source, data_dir=tmp, fetcher=fetcher, ytdlp=ytdlp,
                  max_items=args.max_items)
    keep_files = {}
    if args.extend:
        for meta in old_index.values():
            keep_files[meta["file"]] = (out / meta["file"]).read_bytes()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    index = {}
    for url, meta in old_index.items():  # --extend: 이전 녹화 유지
        (out / meta["file"]).write_bytes(keep_files[meta["file"]])
        index[url] = meta
    for r in rec.records:
        ctype = r["content_type"].split(";")[0].strip().lower()
        body = r["body"].decode("utf-8", errors="replace")
        if any(x in ctype for x in ("xml", "rss", "atom")) or r["url"].endswith((".atom", ".xml")):
            body = trim_feed(body, since, until)
        elif "html" in ctype:
            body = trim_html(body)
        fname = hashlib.sha256(r["url"].encode()).hexdigest()[:20] + ".gz"
        (out / fname).write_bytes(gzip.compress(body.encode("utf-8"), mtime=0))
        index[r["url"]] = {"file": fname, "status": r["status"], "content_type": r["content_type"],
                           "location": r["location"]}
    meta = {"since": args.since, "until": args.until, "max_items": args.max_items, "source": args.source,
            "recorded_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "result": {k: {x: v.get(x) for x in ("status", "n_new", "n_backfilled", "backfill_pages", "trending",
                                                   "releases") if x in v} for k, v in res.sources.items()}}
    (out / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "ytdlp.json").write_text(json.dumps(yt_calls, ensure_ascii=False), encoding="utf-8")
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    size = sum(p.stat().st_size for p in out.iterdir())
    print(f"{out.relative_to(ROOT)}: 응답 {len(index)}개, {size // 1024}KB")
    print(json.dumps(meta["result"], ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
