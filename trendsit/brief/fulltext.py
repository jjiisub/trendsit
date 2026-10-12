"""원문 조립(S6-1 5.2, D-27): 글 원문 문장·전사 25초 묶음·슬라이드 판독·레포 사실을 근거 id가 붙은 줄로.

evidence.py가 이 함수들로 Member.items(EvidenceItem)을 만든다. 여기서는 DB 조회 + 글자 나누기만 하고
pack·cap·Document 조립은 evidence.py·write.py가 한다(COMMON 9장: 무거운 의존성을 들이지 않음, 표준 라이브러리만).
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

from ..core import config
from ..core.db import DB

if TYPE_CHECKING:
    from .evidence import EvidenceItem

# 문장 경계: 줄바꿈 단위 우선, 줄 안에서는 .?!(또는 '다.') 뒤 공백. 소수점(3.7)·약어 뒤에 공백이 없으면 안 쪼갠다
# (구현 시점 기본값 9장: 완벽한 한국어 문장 분리기는 아니다)
_SENT_SPLIT = re.compile(r'(?<=[.!?])\s+(?=[A-Za-z0-9가-힣"\'(「『])')


def sentences(text: str) -> list[str]:
    out: list[str] = []
    for line in (text or "").splitlines():
        line = line.strip()
        if not line:
            continue
        out += [p.strip() for p in _SENT_SPLIT.split(line) if p.strip()]
    return out


def cap_sentences(sents: list[str], max_chars: int) -> list[str]:
    """문장 경계에서 글자 수 상한까지 자른다(최소 1문장은 남김)."""
    kept: list[str] = []
    total = 0
    for s in sents:
        if kept and total + len(s) > max_chars:
            break
        kept.append(s)
        total += len(s)
    return kept


def article_lines(db: DB, item_id: int, text_chars: int) -> tuple[list[tuple[str, str]], bool]:
    """글 원문 → [(근거 id, 문장)]. item_texts가 없거나 만료(NULL)면 (빈 목록, True=원문 없음)."""
    r = db.conn.execute("SELECT text FROM item_texts WHERE item_id=?", (item_id,)).fetchone()
    if r is None or not r["text"]:
        return [], True
    sents = cap_sentences(sentences(r["text"]), text_chars)
    return [(f"it:{item_id}#s{i}", s) for i, s in enumerate(sents, 1)], False


def repo_fact_lines(full_name: str, card: dict[str, Any]) -> list[tuple[str, str]]:
    """레포 사실 → [(근거 id, 사실)]: evidence[].fact 순서대로, 마지막에 뜨는 이유·릴리스 한 줄."""
    out = [(f"rp:{full_name}#f{i}", e.get("fact", "")) for i, e in enumerate(card.get("evidence") or [], 1)]
    n = len(out) + 1
    if card.get("why_trending"):
        out.append((f"rp:{full_name}#f{n}", f"뜨는 이유: {card['why_trending']}"))
        n += 1
    rel = card.get("release")
    if rel:
        out.append((f"rp:{full_name}#f{n}", f"릴리스 {rel['tag']} ({rel['date']}): {rel['line']}"))
    return out


def slide_read_lines(db: DB, item_id: int, video_id: str) -> list[tuple[str, str]]:
    """슬라이드 판독(frame_kind=slide만) → [(sl:{item_id}@{sec}, "제목 | 글자(500자) | 수치 | 표 있음/없음")]."""
    rows = db.conn.execute("SELECT t, reading_json FROM video_frames WHERE video_id=? ORDER BY t", (video_id,)).fetchall()
    out: list[tuple[str, str]] = []
    for r in rows:
        if not r["reading_json"]:
            continue
        d = json.loads(r["reading_json"])
        if d.get("frame_kind") != "slide":
            continue
        sec = round(r["t"])
        nums = "; ".join(f"{n.get('what', '')}: {n.get('value', '')}{n.get('unit', '')}" for n in d.get("numbers") or [])
        out.append((f"sl:{item_id}@{sec}", f"{d.get('title') or ''} | {(d.get('ocr_text') or '')[:500]} | {nums} | "
                                            f"표 {'있음' if d.get('table') else '없음'}"))
    return out


def transcript_group_lines(db: DB, item_id: int, video_id: str, transcript_chars: int) -> list[tuple[str, str]]:
    """전사 25초 묶음(video_segments start 기준) → [(vd:{item_id}@{묶음 시작 초}, 묶은 문장들)], transcript_chars까지."""
    rows = db.conn.execute('SELECT start, text FROM video_segments WHERE video_id=? ORDER BY idx', (video_id,)).fetchall()
    groups: dict[int, list[str]] = {}
    for r in rows:
        if not r["text"]:
            continue
        bucket = int(r["start"] // 25) * 25
        groups.setdefault(bucket, []).append(r["text"])
    out: list[tuple[str, str]] = []
    total = 0
    for sec in sorted(groups):
        text = " ".join(groups[sec]).strip()
        if not text:
            continue
        if out and total + len(text) > transcript_chars:
            break
        out.append((f"vd:{item_id}@{sec}", text))
        total += len(text)
    return out


def video_context_text(digest: dict[str, Any]) -> str:
    """요약 1줄 + 타임라인(둘 다 근거 id 없음, 참고용): 작성자가 video_secs를 고르는 자리."""
    lines = ["요약: " + (digest.get("summary") or ""), "타임라인:"]
    lines += [f"  {m['sec']}초 {m['label']}" + (" (슬라이드)" if m.get("slide") else "") for m in digest.get("timeline") or []]
    return "\n".join(lines)


def raw_evidence(db: DB, eid: str, items: list[EvidenceItem]) -> str:
    """검수자용 근거 원문(5.2, write.py가 씀): it:#s → 그 문장 ± 1문장, vd:@sec(transcript) → 그 묶음 그대로,
    vd:@sec(slide_fact) → 기존 ±30초 전사 창, sl: → 판독 글자 전체, rp:#f → 그 사실 그대로."""
    kind = items[0].kind if items else None
    fallback = items[0].text if items else ""
    if m := re.match(r"^it:(\d+)#s(\d+)$", eid):
        item_id, n = int(m[1]), int(m[2])
        row = db.conn.execute("SELECT text FROM item_texts WHERE item_id=?", (item_id,)).fetchone()
        sents = sentences(row["text"]) if row and row["text"] else []
        if sents and 1 <= n <= len(sents):
            return " ".join(sents[max(0, n - 2): n + 1])
        return fallback
    if m := re.match(r"^sl:(\d+)@(\d+)$", eid):
        video_id = db.conn.execute("SELECT video_id FROM videos WHERE item_id=?", (int(m[1]),)).fetchone()
        if video_id:
            fr = db.conn.execute("SELECT reading_json FROM video_frames WHERE video_id=? AND ABS(t-?)<=0.5 "
                                 "ORDER BY ABS(t-?) LIMIT 1", (video_id[0], float(m[2]), float(m[2]))).fetchone()
            if fr and fr["reading_json"]:
                return json.loads(fr["reading_json"]).get("ocr_text") or fallback  # 006-A2-20: OCR 빈 슬라이드(수치만)도 작성자가 받은 판독 줄로
        return fallback
    if kind == "slide_fact" and (m := re.match(r"^vd:(\d+)@(\d+)$", eid)):
        item_id, sec_i = int(m[1]), int(m[2])
        window_sec = config.load("video.yaml").align_window_sec
        vid = db.conn.execute("SELECT video_id FROM videos WHERE item_id=?", (item_id,)).fetchone()
        window_text = ""
        if vid:
            segs = db.conn.execute('SELECT text FROM video_segments WHERE video_id=? AND "end">=? AND start<=? ORDER BY idx',
                                   (vid[0], sec_i - window_sec, sec_i + window_sec)).fetchall()
            window_text = " ".join(s["text"] for s in segs if s["text"])
        # 006-A2-8: slide_fact와 전사 묶음이 같은 vd:@sec id로 겹칠 수 있다(명세 5.2 id 형식 그대로, sec가 25의
        # 배수면 충돌). 겹친 묶음(items[1:])의 원문도 잃지 않게 이어 붙인다
        other = " ".join(it.text for it in items[1:] if it.kind != "slide_fact" and it.text)
        combined = " ".join(x for x in (window_text, other) if x)
        return combined or fallback
    return fallback
