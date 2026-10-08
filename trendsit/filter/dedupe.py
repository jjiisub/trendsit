"""URL 중복 연결(S2 2a): 정규화 URL이 같은 글을 item_same_as로 잇는다. 지우거나 합치지 않는다.

- 글의 URL 열쇠: 자기 URL + 원문 후보 링크(role='origin_candidate', GeekNews 원문 링크 등)
- 열쇠를 하나라도 공유하면 같은 묶음(합집합-찾기). 예: GeekNews 원문 링크 = Simon Willison 글 URL
- 기준 항목은 원본에 가까운 쪽: filter.yaml origin_rank(공식 > 개인 블로그 > 언론 > 큐레이션) → 게시 시각 → id
- 1차 요약은 기준 항목만 한다. 나머지는 경유 기록(item_same_as.reason에 공유한 URL)
"""

from __future__ import annotations

from typing import Any

from ..collect.links import normalize_url
from ..core.config import FilterConfig
from ..core.db import DB


def source_rank(db: DB, cfg: FilterConfig) -> dict[str, int]:
    """소스 id → 순위(작을수록 원본에 가까움). sources.kind를 filter.yaml source_kind로 덮어쓴다."""
    out = {}
    for r in db.conn.execute("SELECT id, kind FROM sources"):
        kind = cfg.source_kind.get(r["id"], r["kind"])
        out[r["id"]] = cfg.origin_rank.index(kind) if kind in cfg.origin_rank else len(cfg.origin_rank)
    return out


def _find(parent: dict[int, int], x: int) -> int:
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


def link_same_urls(db: DB, item_ids: list[int], cfg: FilterConfig, rank_override: dict[str, int] | None = None) -> int:
    """주어진 글들 사이의 같은 URL을 연결해 저장한다(이 글들의 이전 연결은 지우고 다시). 연결한 항목 수를 돌려준다."""
    if not item_ids:
        return 0
    marks = ",".join("?" * len(item_ids))
    items = {r["id"]: r for r in db.conn.execute(
        f"SELECT id, source_id, url, published_at FROM items WHERE id IN ({marks})", item_ids)}
    keys: dict[int, set[str]] = {i: {normalize_url(r["url"])} if r["url"] else set() for i, r in items.items()}
    for r in db.conn.execute(
            f"SELECT item_id, url FROM links WHERE role='origin_candidate' AND item_id IN ({marks})", item_ids):
        keys[r["item_id"]].add(normalize_url(r["url"]))
    parent = {i: i for i in items}
    owner: dict[str, int] = {}
    shared: dict[frozenset[int], str] = {}
    for i in sorted(items):
        for k in sorted(keys[i]):
            if k in owner:
                a, b = _find(parent, owner[k]), _find(parent, i)
                if a != b:
                    parent[b] = a
                    shared[frozenset((owner[k], i))] = k
            else:
                owner[k] = i
    rank = {**source_rank(db, cfg), **(rank_override or {})}
    groups: dict[int, list[int]] = {}
    for i in items:
        groups.setdefault(_find(parent, i), []).append(i)

    def order(i: int) -> tuple[Any, ...]:
        r = items[i]
        return rank.get(r["source_id"], len(cfg.origin_rank)), r["published_at"] or "9999", i

    rows = []
    for members in groups.values():
        if len(members) < 2:
            continue
        canon = min(members, key=order)
        for m in members:
            if m == canon:
                continue
            url = next((k for k in sorted(keys[m]) if k in keys[canon]), None) or next(
                (v for p, v in shared.items() if m in p), "")
            rows.append((m, canon, f"same_url:{url}"))
    with db.conn:
        db.conn.execute(f"DELETE FROM item_same_as WHERE item_id IN ({marks})", item_ids)
        db.conn.executemany("INSERT INTO item_same_as(item_id, canonical_id, reason) VALUES (?,?,?)", rows)
    return len(rows)
