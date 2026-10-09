"""유튜브: 채널 RSS(최근 15편) → (부족하면 yt-dlp 채널 목록) → 메타데이터(yt-dlp, 다운로드 없음) → 칠판.

메타데이터(길이, 수동 자막 언어, 자동 자막 유무, 챕터)는 편집장 계획(S3)의 처리 깊이 판단 재료.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from typing import Any

import feedparser

from ..core.config import KeywordsConfig, LinkKindsConfig, VideoSource
from ..core.db import DB
from .fetch import Fetcher
from .keywords import KeywordMatcher
from .links import classify, extract_links
from .sites.common import KST
from .text import TEXT_TTL, SourceFailed, SourceStats, iso_week, to_kst

WATCH = "https://www.youtube.com/watch?v={id}"
YtDlp = Callable[[list[str]], dict[str, Any] | None]


def run_ytdlp(args: list[str]) -> dict[str, Any] | None:
    """yt-dlp를 JSON 모드로 실행(다운로드 없음). 없거나 실패하면 None."""
    exe = shutil.which("yt-dlp")
    if exe is None:
        return None
    proc = subprocess.run([exe, "-J", "--skip-download", "--no-warnings", *args], capture_output=True,
                          text=True, timeout=180)
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    return json.loads(proc.stdout)


def parse_channel_rss(text: str) -> list[dict[str, Any]]:
    feed = feedparser.parse(text)
    out = []
    for e in feed.entries:
        vid = e.get("yt_videoid")
        if not vid:
            continue
        ts = e.get("published_parsed")
        thumbs = e.get("media_thumbnail") or [{}]
        out.append({"video_id": vid, "title": e.get("title"), "description": e.get("summary") or "",
                    "published": datetime(*ts[:6], tzinfo=UTC) if ts else None,
                    "thumbnail": thumbs[0].get("url")})
    return out


def video_meta(info: dict[str, Any] | None) -> dict[str, Any]:
    if not info:
        return {"meta_status": "failed"}
    return {"duration_sec": info.get("duration"), "manual_sub_langs": sorted((info.get("subtitles") or {}).keys()),
            "has_auto_sub": int(bool(info.get("automatic_captions"))),
            "chapters": [{"start": c.get("start_time"), "title": c.get("title")} for c in info.get("chapters") or []],
            "meta_status": "ok", "timestamp": info.get("timestamp"), "description": info.get("description"),
            "title": info.get("title")}


class YoutubeCollector:
    def __init__(self, db: DB, fetcher: Fetcher, keywords: KeywordsConfig, link_kinds: LinkKindsConfig, *,
                 run_id: str, ytdlp: YtDlp = run_ytdlp, with_meta: bool = True, max_items: int | None = None):
        self.db, self.fetcher = db, fetcher
        self.matcher = KeywordMatcher(keywords)
        self.link_kinds = link_kinds
        self.run_id = run_id
        self.ytdlp = ytdlp
        self.with_meta = with_meta
        self.max_items = max_items
        self._range: tuple[date, date] = (date.min, date.max)

    def collect(self, src: VideoSource, since: date, until: date) -> SourceStats:
        st = SourceStats(src.id)
        self._range = (since, until)
        res = self.fetcher.fetch(src.feed, kind="feed")
        rss_failed = not res.ok
        if rss_failed:  # RSS가 404를 이어 낸 적이 있다(2026-10-09). 채널 목록이 있으면 그것으로 대체
            if src.backfill.method != "channel_listing":
                raise SourceFailed(f"채널 RSS 실패: {res.error}")
            st.notes.append(f"채널 RSS 실패({res.error}): 채널 목록으로 대체")
        videos = {} if rss_failed else {v["video_id"]: v | {"via": "rss"} for v in parse_channel_rss(res.text or "")}
        dated = [to_kst(v["published"]).date() for v in videos.values() if v["published"]]
        oldest = min(dated) if dated else None
        st.rss_oldest = oldest.isoformat() if oldest else None
        if oldest is None or since <= oldest:  # RSS의 가장 오래된 날은 일부만 담을 수 있다
            if src.backfill.method == "channel_listing":
                listing = self.ytdlp(["--flat-playlist", "--playlist-end", str(src.backfill.max_videos),
                                      "--extractor-args", "youtubetab:approximate_date",
                                      f"https://www.youtube.com/channel/{src.channel_id}/videos"])
                st.backfill_pages += 1
                if listing is None:
                    if rss_failed:
                        raise SourceFailed(f"채널 RSS 실패: {res.error}, 채널 목록도 실패")
                    st.covered = False
                    st.notes.append("yt-dlp 채널 목록 실패(설치 안 됨 또는 차단). RSS 범위만")
                else:
                    for e in listing.get("entries") or []:
                        ts = e.get("timestamp")
                        videos.setdefault(e["id"], {
                            "video_id": e["id"], "title": e.get("title"), "description": e.get("description") or "",
                            "published": datetime.fromtimestamp(ts, UTC) if ts else None,
                            "thumbnail": None, "via": "backfill", "approximate": True})
            else:
                st.covered = False
                st.notes.append(f"RSS 가장 오래된 영상 {oldest}, 요청 시작 {since}: 백필 없음")

        # 채널 목록의 시각은 대략값이라 기간 앞뒤 3일까지 후보로 받고, 정확한 시각을 얻은 뒤 기간을 다시 본다
        margin = timedelta(days=3)

        def near(v: dict[str, Any]) -> bool:
            if not v["published"]:
                return False
            d = to_kst(v["published"]).date()
            return (since - margin <= d <= until + margin) if v.get("approximate") else (since <= d <= until)

        in_range = [v for v in videos.values() if near(v)]
        st.n_in_range = len(in_range)
        if self.max_items:
            in_range = in_range[: self.max_items]
        for v in in_range:
            self._save(src, v, st)
        if self.with_meta and shutil.which("yt-dlp") is None and self.ytdlp is run_ytdlp:
            st.notes.append("yt-dlp 없음: 메타데이터 null")
        return st

    def _save(self, src: VideoSource, v: dict[str, Any], st: SourceStats) -> None:
        existing = self.db.item_by_external(src.id, v["video_id"])
        # 이미 있으면 건너뛴다. 메타데이터를 못 받았던 영상만 다시 시도
        if existing is not None and self.db.video_meta_status(existing["id"]) != "failed":
            st.n_skipped += 1
            return
        st.n_seen += 1
        meta = video_meta(self.ytdlp([WATCH.format(id=v["video_id"])])) if self.with_meta else {"meta_status": "skipped"}
        if meta.get("timestamp"):  # 채널 목록의 대략 시각보다 정확
            v["published"] = datetime.fromtimestamp(meta["timestamp"], UTC)
            v["approximate"] = False
        since, until = self._range
        d = to_kst(v["published"]).date()
        if not since <= d <= until:  # 정확한 시각으로 다시 보니 기간 밖
            st.n_out_of_range += 1
            return
        if meta.get("meta_status") == "failed":
            st.errors.append(f"메타데이터 실패: {v['video_id']}")
        description = meta.get("description") or v.get("description") or ""
        title = meta.get("title") or v.get("title")
        when = to_kst(v["published"]) or datetime.now(KST)
        m = self.matcher.match(title, None, description)
        links = [x | {"role": "body", "kind": classify(x["url"], self.link_kinds)}
                 for x in extract_links(_linkify(description), WATCH.format(id=v["video_id"]))]
        item = {"source_id": src.id, "channel": "video", "kind": "video", "external_id": v["video_id"],
                "url": WATCH.format(id=v["video_id"]), "title": title,
                "published_at": when.isoformat(timespec="seconds"),
                "published_estimated": bool(v.get("approximate")) and not meta.get("timestamp"),
                "day": when.date().isoformat(), "week": iso_week(when.date()), "summary_feed": description[:1000],
                "body_status": "ok" if description else "short", "filter_status": m.filter_status,
                "filter_reason": m.filter_reason, "score": m.score, "run_id": self.run_id, "via": v["via"]}
        video = {"video_id": v["video_id"]} | {k: meta.get(k) for k in
                                               ("duration_sec", "manual_sub_langs", "has_auto_sub", "chapters",
                                                "meta_status")}
        self.db.save_item(item, text=description or None, origin_summary=None,
                          expires_at=(datetime.now(KST) + TEXT_TTL).isoformat(timespec="seconds"),
                          links=links, keywords=m.keywords, video=video,
                          replace_id=existing["id"] if existing is not None else None)
        if existing is None:
            st.n_new += 1
            st.n_backfilled += int(v["via"] == "backfill")
        status = item["body_status"]
        st.body[status] = st.body.get(status, 0) + 1


def _linkify(text: str) -> str:
    """설명란의 맨 URL을 <a>로(링크 추출기가 읽을 수 있게)."""
    return re.sub(r"(https?://[^\s<>\"]+)", r'<a href="\1">\1</a>', text or "")
