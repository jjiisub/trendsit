"""GitHub: 트렌딩 주간 페이지(실행 시점의 목록), 추적 레포 릴리스(releases.atom), README 앞부분(API)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any

import feedparser

from ..core.config import GithubConfig, KeywordsConfig, LinkKindsConfig, get_secret
from ..core.db import DB
from .fetch import Fetcher
from .keywords import KeywordMatcher
from .links import classify, extract_links, url_id
from .sites.common import KST, block_text, doc, text_of
from .text import TEXT_TTL, SourceFailed, iso_week, to_kst

README_HEAD = 3000
API = "https://api.github.com"
_NUM = re.compile(r"[\d,]+")


def _int(text: str) -> int | None:
    m = _NUM.search(text or "")
    return int(m.group().replace(",", "")) if m else None


def parse_trending(html: str) -> list[dict[str, Any]]:
    """레포마다 full_name, description, language, stars_total, forks, stars_this_week, rank."""
    rows = []
    for rank, art in enumerate(doc(html).xpath("//article[contains(@class,'Box-row')]"), start=1):
        href = next(iter(art.xpath(".//h2//a/@href")), "")
        full_name = href.strip("/")
        if full_name.count("/") != 1:
            continue
        desc = next(iter(art.xpath(".//p")), None)
        lang = next(iter(art.xpath(".//*[@itemprop='programmingLanguage']")), None)
        stars = next(iter(art.xpath(f".//a[@href='/{full_name}/stargazers']")), None)
        forks = next(iter(art.xpath(f".//a[@href='/{full_name}/forks']")), None)
        week = next((text_of(s) for s in art.xpath(".//span") if "stars this" in text_of(s)), "")
        rows.append({"full_name": full_name, "description": text_of(desc) or None,
                     "language": text_of(lang) or None, "stars_total": _int(text_of(stars)),
                     "forks": _int(text_of(forks)), "stars_this_week": _int(week), "rank": rank})
    return rows


@dataclass
class GithubStats:
    trending: int = 0
    page_rows: int = 0  # 페이지에 보인 레포 수(전부 저장했는지 리포트가 확인)
    trending_pass: int = 0
    trending_missing_week_stars: int = 0
    releases: int = 0
    releases_new: int = 0
    readmes: int = 0
    errors: list[str] = field(default_factory=list)


class GithubCollector:
    def __init__(self, db: DB, fetcher: Fetcher, cfg: GithubConfig, keywords: KeywordsConfig,
                 link_kinds: LinkKindsConfig, *, run_id: str):
        self.db, self.fetcher, self.cfg = db, fetcher, cfg
        self.matcher = KeywordMatcher(keywords)
        self.link_kinds = link_kinds
        self.run_id = run_id
        token = get_secret("GITHUB_TOKEN")
        self.api_headers = {"Accept": "application/vnd.github+json"} | (
            {"Authorization": f"Bearer {token}"} if token else {})

    # ---------- 트렌딩 ----------
    def trending(self, st: GithubStats) -> None:
        """실행 시점의 주간 목록을 실행 주차(한국 시간)로 저장. 0건이면 실패(페이지 구조 변경 의심)."""
        res = self.fetcher.fetch(self.cfg.trending.url, kind="page")
        if not res.ok:
            raise SourceFailed(f"트렌딩 페이지 실패: {res.error}")
        rows = parse_trending(res.text or "")  # 주간 페이지에 보이는 전부(S1 Q2)
        st.page_rows = len(rows)
        if not rows:
            raise SourceFailed("트렌딩 0건: 페이지 구조가 바뀌었을 수 있음")
        week = iso_week(datetime.now(KST).date())
        self.db.clear_trending(week)  # 같은 주에 다시 돌리면 이번 목록으로 바꾼다(빠진 레포 행이 남지 않게)
        for row in rows:
            # 스펙 5.5: 설명, 토픽, README로 판정(이름은 넣지 않음). 설명을 제목 자리에(트렌딩 페이지에는 토픽이 없음)
            m = self.matcher.match(row["description"], None)
            readme = None
            if m.filter_status == "pass":  # 키워드에 걸린 레포만 README를 받아 토픽, README까지 넣어 다시 판정
                meta = self.readme(row["full_name"], st)
                readme = meta.get("readme_head")
                m = self.matcher.match(row["description"], " ".join(meta.get("topics", [])), readme)
            self.db.upsert_repo(row["full_name"], description=row["description"], language=row["language"],
                                readme_head=readme)
            row |= {"score": m.score, "filter_status": m.filter_status, "filter_reason": m.filter_reason,
                    "keywords": m.keywords}
            self.db.save_trending(week, row, self.run_id)
            st.trending += 1
            st.trending_pass += int(m.filter_status == "pass")
            st.trending_missing_week_stars += int(row["stars_this_week"] is None)

    # ---------- README ----------
    def readme(self, full_name: str, st: GithubStats) -> dict[str, Any]:
        """GitHub API로 설명, 토픽, README 앞 3,000자. repo_oneliner 입력과 같은 형식."""
        out: dict[str, Any] = {}
        meta = self.fetcher.fetch(f"{API}/repos/{full_name}", kind="api", headers=self.api_headers)
        if meta.ok and meta.text:
            data = json.loads(meta.text)
            out |= {"description": data.get("description"), "topics": data.get("topics") or []}
        rd = self.fetcher.fetch(f"{API}/repos/{full_name}/readme", kind="api",
                                headers=self.api_headers | {"Accept": "application/vnd.github.raw"})
        if rd.ok and rd.text is not None:
            out["readme_head"] = rd.text[:README_HEAD]
            st.readmes += 1
        elif rd.status not in (404, None):
            st.errors.append(f"README {full_name}: {rd.error}")
        self.db.upsert_repo(full_name, description=out.get("description"), topics=out.get("topics"),
                            readme_head=out.get("readme_head"))
        return out

    # ---------- 추적 레포 릴리스 ----------
    def releases(self, since: date, until: date, st: GithubStats) -> None:
        for t in self.cfg.tracked:
            self.readme(t.repo, st)
            res = self.fetcher.fetch(f"https://github.com/{t.repo}/releases.atom", kind="feed")
            if not res.ok:
                st.errors.append(f"릴리스 {t.repo}: {res.error}")
                continue
            for e in feedparser.parse(res.text or "").entries:
                ts = e.get("updated_parsed") or e.get("published_parsed")
                when = to_kst(datetime(*ts[:6], tzinfo=UTC)) if ts else None
                if when is None or not since <= when.date() <= until:
                    continue
                st.releases += 1
                st.releases_new += int(self._save_release(t.repo, e, when))

    def _save_release(self, repo: str, e: Any, when: datetime) -> bool:
        link = e.get("link") or f"https://github.com/{repo}/releases"
        ext = url_id(link)
        if self.db.item_by_external("github_releases", ext) is not None:
            return False
        content = (e.get("content") or [{}])[0].get("value") or e.get("summary") or ""
        notes = block_text(doc(f"<div>{content}</div>")) if content else ""
        title = f"{repo} {e.get('title') or ''}".strip()
        m = self.matcher.match(title, notes)
        links = [x | {"role": "body", "kind": classify(x["url"], self.link_kinds)}
                 for x in extract_links(content, link)]
        item = {"source_id": "github_releases", "channel": "github", "kind": "release", "external_id": ext,
                "url": link, "title": title, "published_at": when.isoformat(timespec="seconds"),
                "published_estimated": False, "day": when.date().isoformat(), "week": iso_week(when.date()),
                "summary_feed": notes[:1000], "body_status": "ok" if notes else "short",
                "filter_status": m.filter_status, "filter_reason": m.filter_reason, "score": m.score,
                "run_id": self.run_id, "via": "rss"}
        self.db.save_item(item, text=notes, origin_summary=None,
                          expires_at=(datetime.now(KST) + TEXT_TTL).isoformat(timespec="seconds"),
                          links=links, keywords=m.keywords)
        return True
