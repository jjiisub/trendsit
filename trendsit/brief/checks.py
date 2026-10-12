"""작성자 출력의 코드 검사(S6-1 5.5, LLM 0원). 검수자 앞에서 돈다.

1. 고칠 수 있는 형식은 직접 고친다(반려 아님): 형광 초과·공백·문장부호·별칭 표기 → 정본, slide가 후보 밖이면
   null, video_secs가 타임라인에 없으면 제거, sections 수 초과면 뒤에서 자름
2. 반려(라운드에 셈): 필수 칸·분량, refs 실재, 수치 대조, 시각 요소 칸 규칙, 문체(평가어·해요체)
3. 경고(검수자 입력): 시각 요소 남발·누락 의심, 같은 단락 중복. 반려 메시지는 위치·근거·힌트를 구체적으로
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any

from ..core.artifacts_brief import Issue, TopicPage
from ..core.artifacts_text import figures
from ..core.config_brief import BriefConfig
from ..core.numbers import number_values, same
from ..core.style import EVAL_ENDINGS, EVAL_WORDS, ends_as_sentence, is_haeyo
from .evidence import EvidenceItem

HL = re.compile(r"==(.+?)==")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
REF = re.compile(r"(?:it|og|vd|rp|sl):[\w./#@:-]+")
_SENT = re.compile(r"(?<=[.!?])\s+")  # 006-A3-2: "보다 "·"위한다 " 같은 문장 중간 "다"에서 쪼개지 않음(fulltext.sentences와 맞춤)
UNIT_WORDS = ("%", "퍼센트", "포인트", "밀리초", "초", "달러", "원", "배", "분기", "시간", "개월", "분", "개", "명", "회", "건")
_ASCII_UNIT = re.compile(r"(?<![\d.,A-Za-z])(\d+(?:\.\d+)?)(ms|[KMBT])(?![A-Za-z])")
_CURRENCY = re.compile(r"[$₩€£]\s?(\d+(?:\.\d+)?)")
_KO_UNIT = re.compile(r"(?<![\d.,])(\d+)\s?([가-힣%]+)")


def is_unit(text: str) -> bool:
    return (text or "").strip().startswith(UNIT_WORDS)


def _unit_figures(body: str) -> list[str]:
    """①: 단위 붙은 수 — 한국어 단위어(개·초·달러 등) + ms·K·M·B·T 접미사 + $·₩·€·£ 접두 통화(006-C1-2)."""
    out = [m.group(1) for m in _KO_UNIT.finditer(body) if is_unit(m.group(2))]
    out += [m.group(1) + m.group(2) for m in _ASCII_UNIT.finditer(body)]
    out += [m.group(1) for m in _CURRENCY.finditer(body)]
    return out


def sentences(text: str) -> list[str]:
    return [s for s in _SENT.split((text or "").strip()) if s.strip()]


def plain(text: str) -> str:
    return HL.sub(r"\1", text or "")


@dataclass
class RefSlot:
    loc: str
    field: str
    refs: list[str]


def page_refs(page: TopicPage) -> list[RefSlot]:
    """페이지의 근거 id 칸 전부(세밀한 위치). topic_evidence.field는 기존 CHECK 값 재사용
    (단락 → point, 타일·표·막대 항목 → number, 사건 → event, 표·막대 설명 글 속 id·슬라이드 인용 → context)."""
    out = [RefSlot(f"head_tiles[{i}]", "number", t.refs) for i, t in enumerate(page.head_tiles)]
    for i, s in enumerate(page.sections):
        out += [RefSlot(f"sections[{i}].paragraphs[{j}]", "point", p.refs) for j, p in enumerate(s.paragraphs)]
        if s.bars is not None:
            out.append(RefSlot(f"sections[{i}].bars", "context", REF.findall(s.bars.context)))
            out += [RefSlot(f"sections[{i}].bars.items[{k}]", "number", [it.ref]) for k, it in enumerate(s.bars.items)]
        if s.table is not None:
            out.append(RefSlot(f"sections[{i}].table", "number", s.table.refs))
        if s.visual == "tiles":
            out += [RefSlot(f"sections[{i}].tiles[{k}]", "number", t.refs) for k, t in enumerate(s.tiles)]
        if s.events is not None:
            out.append(RefSlot(f"sections[{i}].events", "context", REF.findall(s.events.context)))
            out += [RefSlot(f"sections[{i}].events.items[{k}]", "event", [it.ref] if it.ref else [])
                    for k, it in enumerate(s.events.items)]
        if s.slide:
            out.append(RefSlot(f"sections[{i}].slide", "context", [s.slide]))
    return out


@dataclass
class CheckResult:
    page: TopicPage
    autofix: list[dict[str, Any]] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.issues


def _issue(loc: str, type_: str, comment: str, hint: str = "", evidence_id: str | None = None) -> Issue:
    return Issue(loc=loc, type=type_, evidence_id=evidence_id, comment=comment, hint=hint)  # type: ignore[arg-type]


# ---------- 자동 수정 ----------
def _text_slots(page: TopicPage) -> list[tuple[str, str]]:
    """형광을 셀 순서(summary → 단락)와 위치 이름."""
    out = [("summary", page.summary)]
    for i, s in enumerate(page.sections):
        out += [(f"sections[{i}].paragraphs[{j}]", p.text) for j, p in enumerate(s.paragraphs)]
    return out


def _canon_slots(page: TopicPage) -> list[tuple[str, str]]:
    """정본 표기·공백 정리 대상(summary·단락·title·heading, 형광 상한 대상 + title·heading)."""
    slots = [*_text_slots(page), ("title", page.title)]
    return slots + [(f"sections[{i}].heading", s.heading) for i, s in enumerate(page.sections)]


def _set(page: TopicPage, loc: str, text: str) -> TopicPage:
    if loc in ("summary", "title"):
        return page.model_copy(update={loc: text})
    m = re.match(r"^sections\[(\d+)\]\.paragraphs\[(\d+)\]$", loc)
    if m:
        i, j = int(m[1]), int(m[2])
        secs = list(page.sections)
        paras = list(secs[i].paragraphs)
        paras[j] = paras[j].model_copy(update={"text": text})
        secs[i] = secs[i].model_copy(update={"paragraphs": paras})
        return page.model_copy(update={"sections": secs})
    m2 = re.match(r"^sections\[(\d+)\]\.heading$", loc)
    if m2:
        i = int(m2[1])
        secs = list(page.sections)
        secs[i] = secs[i].model_copy(update={"heading": text})
        return page.model_copy(update={"sections": secs})
    raise KeyError(loc)


def _cut_sections(page: TopicPage, hi: int, fixes: list[dict[str, Any]]) -> TopicPage:
    """sections 개수 초과: 중요도 순이라 뒤에서 자른다(그 절의 시각 요소도 함께)."""
    if len(page.sections) <= hi:
        return page
    fixes.append({"loc": "sections", "rule": f"sections {len(page.sections)}개 → {hi}개(뒤에서 자름)",
                  "before": [s.heading for s in page.sections[hi:]], "after": []})
    return page.model_copy(update={"sections": page.sections[:hi]})


def _fix_slide_and_video_secs(page: TopicPage, slide_candidates: list[str], timeline_secs: set[int],
                              fixes: list[dict[str, Any]]) -> TopicPage:
    """C-4: section.slide가 slide_candidates 밖이면 null로, video_secs가 타임라인에 없으면 그 값만 제거."""
    secs = list(page.sections)
    changed = False
    for i, s in enumerate(secs):
        upd: dict[str, Any] = {}
        if s.slide and s.slide not in slide_candidates:
            fixes.append({"loc": f"sections[{i}].slide", "rule": "slide_candidates 밖 → null", "before": s.slide, "after": None})
            upd = {"slide": None, "slide_caption": ""}
        kept = [v for v in s.video_secs if v in timeline_secs]
        if kept != s.video_secs:
            fixes.append({"loc": f"sections[{i}].video_secs", "rule": "타임라인 밖 sec 제거", "before": s.video_secs, "after": kept})
            upd["video_secs"] = kept
        if upd:
            secs[i] = s.model_copy(update=upd)
            changed = True
    return page.model_copy(update={"sections": secs}) if changed else page


def _canonical_names_and_spacing(page: TopicPage, canon: dict[str, str],
                                 translit: list[tuple[re.Pattern[str], str]], fixes: list[dict[str, Any]]) -> TopicPage:
    """별칭 → 정본(긴 표기부터), 음차 표기 → 정본, 그 뒤 공백·문장부호 정리(한 번에 돈다)."""
    for loc, text in _canon_slots(page):
        new = text
        for alias in sorted(canon, key=len, reverse=True):
            pat = rf"(?<![A-Za-z0-9]){re.escape(alias)}(?![A-Za-z0-9])"
            if alias and re.search(pat, new) and canon[alias] not in new:
                new = re.sub(pat, canon[alias], new)
        for tp, target in translit:
            new = tp.sub(target, new)
        if new != text:
            fixes.append({"loc": loc, "rule": "별칭 표기를 정본으로", "before": text, "after": new})
            page = _set(page, loc, new)
        new2 = re.sub(r"\s{2,}", " ", new).strip()
        new2 = re.sub(r"([.,])\1+", r"\1", re.sub(r"\s+([,.;:])", r"\1", new2))
        if new2 != new:
            fixes.append({"loc": loc, "rule": "공백·문장부호 정리", "before": new, "after": new2})
            page = _set(page, loc, new2)
    return page


def _cap_highlights(page: TopicPage, hl: Any, fixes: list[dict[str, Any]]) -> TopicPage:
    """형광: summary 상한, 단락당 상한, 페이지 상한. 넘치면 뒤쪽부터 제거."""
    total = 0
    for loc, text in _text_slots(page):
        cap = hl.summary if loc == "summary" else hl.per_paragraph
        marks = HL.findall(text)
        keep = max(0, min(cap, hl.page[1] - total))
        if len(marks) > keep:
            parts = HL.split(text)
            new = "".join(p if i % 2 == 0 else (f"=={p}==" if (i + 1) // 2 <= keep else p) for i, p in enumerate(parts))
            fixes.append({"loc": loc, "rule": f"형광 {len(marks)}개 → {keep}개(뒤쪽부터 제거)", "before": text, "after": new})
            page = _set(page, loc, new)
        total += min(len(marks), keep)
    return page


def autofix(page: TopicPage, cfg: BriefConfig, canon: dict[str, str], slide_candidates: list[str],
           timeline_secs: set[int], sections_hi: int,
           translit: list[tuple[re.Pattern[str], str]] | None = None) -> tuple[TopicPage, list[dict[str, Any]]]:
    fixes: list[dict[str, Any]] = []
    page = _cut_sections(page, sections_hi, fixes)
    page = _fix_slide_and_video_secs(page, slide_candidates, timeline_secs, fixes)
    page = _canonical_names_and_spacing(page, canon, translit or [], fixes)
    return _cap_highlights(page, cfg.write.highlights, fixes), fixes


# ---------- 반려 ----------
def _ev_text(ids: list[str], pack: dict[str, list[EvidenceItem]]) -> str:
    out = []
    for i in ids:
        for it in pack.get(i, []):
            if it.kind in ("summary", "context"):
                continue
            out.append(f"{it.text} {it.value or ''}{it.unit or ''}")
    return " ".join(out)


def _numbers_ok(text: str, ids: list[str], pack: dict[str, list[EvidenceItem]],
                with_units: bool = False) -> list[tuple[str, str]]:
    """본문 수치 중 근거에 같은 값이 없는 것과 근거의 비슷한 값(힌트). 값으로 비교(부분 문자열 아님)."""
    src = _ev_text(ids, pack)
    vals = number_values(src)
    out = []
    body = plain(text)
    found = figures(body) + (_unit_figures(body) if with_units else [])
    for f in dict.fromkeys(found):
        if re.search(rf"[A-Za-z]\s{re.escape(f)}(?![\d.]|\s?(%|배|x|×|점|달러|초|ms))", body):
            continue
        fvals = number_values(f)  # figures()는 순수 숫자, _unit_figures()는 K·M 등 접미사 포함(값으로 환산)
        if not fvals:
            continue
        v = fvals[0]
        if any(same(v, w) for w in vals):
            continue
        near = sorted(set(vals), key=lambda w: abs(w - v))[:3]
        out.append((f, ", ".join(f"{x:g}" for x in near)))
    return out


def _value_mismatch(value: str, ids: list[str], pack: dict[str, list[EvidenceItem]]) -> bool:
    """타일 value·표 셀처럼 수치 그 자체인 칸: number_values 전체를 근거 값과 대조(막대와 같은 방식, 006-C1-2).
    존재하지 않는 근거 id는 빼고 본다(그쪽은 wrong_ref가 이미 반려한다, 006-A1-2 재발 방지)."""
    known = [i for i in ids if i in pack]
    cell_vals = number_values(value)
    if not cell_vals or not known:
        return False
    vals = number_values(_ev_text(known, pack))
    return not any(same(v, w) for v in cell_vals for w in vals)


def _check_counts(page: TopicPage, cfg: BriefConfig, n_sources: int) -> list[Issue]:
    w = cfg.write
    issues: list[Issue] = []
    for name in ("title", "summary"):
        if not getattr(page, name).strip():
            issues.append(_issue(name, "format", f"{name}이 비어 있음", "필수 칸"))
    ns = len(sentences(plain(page.summary)))
    if not w.summary.sentences[0] <= ns <= w.summary.sentences[1]:
        issues.append(_issue("summary", "format", f"summary {ns}문장({w.summary.sentences[0]}~{w.summary.sentences[1]})",
                             "사건+쟁점 2문장 안팎"))
    if len(plain(page.summary)) > w.summary.chars_max:
        issues.append(_issue("summary", "format", f"summary {len(plain(page.summary))}자(최대 {w.summary.chars_max})", "짧게"))
    lo, hi = w.sections_for(n_sources)
    if not lo <= len(page.sections) <= hi:
        issues.append(_issue("sections", "format", f"sections {len(page.sections)}개(근거 소스 {n_sources}개면 {lo}~{hi}개)",
                             "중요도 순으로 개수 맞춤"))
    for i, s in enumerate(page.sections):
        loc = f"sections[{i}]"
        if not s.heading.strip():
            issues.append(_issue(f"{loc}.heading", "format", f"{loc}.heading이 비어 있음", "포인트 문장(명사형)"))
        elif len(s.heading) > w.heading_chars_max:
            issues.append(_issue(f"{loc}.heading", "format", f"heading {len(s.heading)}자(최대 {w.heading_chars_max})", "짧게"))
        if not w.paragraphs.per_section[0] <= len(s.paragraphs) <= w.paragraphs.per_section[1]:
            issues.append(_issue(loc, "format", f"{loc} paragraphs {len(s.paragraphs)}개"
                                 f"({w.paragraphs.per_section[0]}~{w.paragraphs.per_section[1]})", ""))
        for j, p in enumerate(s.paragraphs):
            ploc = f"{loc}.paragraphs[{j}]"
            ns2 = len(sentences(plain(p.text)))
            if ns2 > w.paragraphs.sentences_max:
                issues.append(_issue(ploc, "format", f"{ploc} {ns2}문장(최대 {w.paragraphs.sentences_max})", "간결하게"))
            if len(plain(p.text)) > w.paragraphs.chars_max:
                issues.append(_issue(ploc, "format", f"{ploc} {len(plain(p.text))}자(최대 {w.paragraphs.chars_max})", "짧게"))
            if not 1 <= len(p.refs) <= cfg.evidence.max_refs_per_paragraph:
                issues.append(_issue(ploc, "wrong_ref", f"{ploc} refs {len(p.refs)}개(1~{cfg.evidence.max_refs_per_paragraph})",
                                     "그 단락을 받치는 근거 id만"))
    n_visual = sum(1 for s in page.sections if s.visual != "none")
    n_slides = sum(1 for s in page.sections if s.slide)
    for loc3, label, n, hi, hint in (("head_tiles", "head_tiles", len(page.head_tiles), w.head_tiles_max, ""),
                                      ("sections", "visual≠none", n_visual, w.visuals_max, "꼭 필요한 절만"),
                                      ("sections", "slide", n_slides, w.slides_max, "")):
        if n > hi:
            issues.append(_issue(loc3, "format", f"{label} {n}개(최대 {hi})", hint))
    return issues


def _check_refs(page: TopicPage, pack: dict[str, list[EvidenceItem]]) -> list[Issue]:
    issues = []
    for slot in page_refs(page):
        issues += [_issue(slot.loc, "wrong_ref", f"{slot.loc}의 근거 id {r}가 이 토픽 근거 목록에 없음", "근거 목록의 id만", evidence_id=r)
                   for r in slot.refs if r not in pack]
    return issues


def _range_issue(loc: str, label: str, n: int, rng: tuple[int, int]) -> Issue | None:
    lo, hi = rng
    return None if lo <= n <= hi else _issue(loc, "format", f"{label} {n}개({lo}~{hi})", "")


def _check_visual_structure(page: TopicPage, cfg: BriefConfig) -> list[Issue]:
    """visual과 내용 일치, bars·table·tiles·events 항목 수 범위."""
    issues: list[Issue] = []
    w = cfg.write
    for i, s in enumerate(page.sections):
        loc = f"sections[{i}]"
        has = {"bars": s.bars is not None, "table": s.table is not None, "tiles": bool(s.tiles), "events": s.events is not None}
        want = {"bars": s.visual == "bars", "table": s.visual == "table", "tiles": s.visual == "tiles", "events": s.visual == "events"}
        if has != want:
            issues.append(_issue(loc, "format", f"{loc}.visual={s.visual}인데 칸 상태가 안 맞음(has={has})",
                                 "visual에 맞는 칸만 채우고 나머지는 비움"))
            continue
        ranged = [(f"{loc}.bars", "bars items", s.bars and len(s.bars.items), w.bars_items),
                  (f"{loc}.table", "table rows", s.table and len(s.table.rows), w.table.rows),
                  (f"{loc}.table", "table columns", s.table and len(s.table.columns), w.table.cols),
                  (f"{loc}.tiles", "tiles", s.visual == "tiles" and len(s.tiles), w.tiles_per_section),
                  (f"{loc}.events", "events items", s.events and len(s.events.items), (2, 6))]
        issues += [iss for rloc, label, n, rng in ranged if n and (iss := _range_issue(rloc, label, n, rng))]
        if s.bars is not None and not s.bars.unit.strip("() \t"):
            issues.append(_issue(f"{loc}.bars", "format", "bars 단위가 비어 있음", "근거의 단위 그대로"))
        if s.table is not None and (bad_rows := [k for k, row in enumerate(s.table.rows) if len(row) != len(s.table.columns)]):
            issues.append(_issue(f"{loc}.table", "format", f"table rows {bad_rows}의 길이가 columns와 다름", ""))
        for k, it in enumerate(s.events.items if s.events else []):
            if not DATE.match(it.date):
                issues.append(_issue(f"{loc}.events.items[{k}]", "format", f"날짜 '{it.date}'가 YYYY-MM-DD가 아님", ""))
            if not it.ref and not it.topic_id:
                issues.append(_issue(f"{loc}.events.items[{k}]", "wrong_ref", "사건에 근거 id나 지난 토픽 id가 없음", ""))
    return issues


def _number_slots(page: TopicPage) -> list[tuple[str, str, list[str] | None]]:
    """수치를 대조할 자유 문장 칸(위치, 글, 근거 id들). ids가 None인 칸(refs가 없는 heading·slide_caption 등)은
    토픽 근거 전체와 대조(①, 호출부가 all_ids로 채움). 표 셀·타일 값처럼 수치 그 자체인 칸은 여기 넣지 않고
    `_value_slots`가 number_values 전체 대조로 따로 본다(006-C1-2)."""
    slots: list[tuple[str, str, list[str] | None]] = []
    for i, s in enumerate(page.sections):
        slots.append((f"sections[{i}].heading", s.heading, None))
        if s.slide_caption:
            slots.append((f"sections[{i}].slide", s.slide_caption, None))
        if s.bars is not None:
            ids = [it.ref for it in s.bars.items] + REF.findall(s.bars.context)
            slots.append((f"sections[{i}].bars", s.bars.title, ids))
        if s.table is not None:
            slots.append((f"sections[{i}].table", s.table.title, s.table.refs))
        if s.events is not None:
            ids = [it.ref for it in s.events.items if it.ref] + REF.findall(s.events.context)
            slots.append((f"sections[{i}].events", s.events.title, ids))
    return slots


def _value_slots(page: TopicPage) -> list[tuple[str, str, list[str]]]:
    """수치 그 자체인 칸(타일 value, 표 셀 첫 열 제외, 막대 value): number_values 전체 대조(5.5 ①, 006-C1-2)."""
    slots: list[tuple[str, str, list[str]]] = [(f"head_tiles[{i}]", t.value, t.refs) for i, t in enumerate(page.head_tiles)]
    for i, s in enumerate(page.sections):
        if s.bars is not None:
            slots += [(f"sections[{i}].bars.items[{k}]", it.value, [it.ref]) for k, it in enumerate(s.bars.items)]
        if s.table is not None:
            slots += [(f"sections[{i}].table.rows[{k}]", cell, s.table.refs)
                     for k, row in enumerate(s.table.rows) for ci, cell in enumerate(row) if ci > 0]
        if s.visual == "tiles":
            slots += [(f"sections[{i}].tiles[{k}]", t.value, t.refs) for k, t in enumerate(s.tiles)]
    return slots


def _check_numbers(page: TopicPage, pack: dict[str, list[EvidenceItem]]) -> list[Issue]:
    issues = []
    all_ids = list(pack)
    for i, s in enumerate(page.sections):
        for j, p in enumerate(s.paragraphs):
            for f, near in _numbers_ok(p.text, p.refs, pack, with_units=True):
                issues.append(_issue(f"sections[{i}].paragraphs[{j}]", "number_mismatch",
                                     f"sections[{i}].paragraphs[{j}]의 '{f}'가 {', '.join(p.refs)}에 없음"
                                     + (f". 근거의 가까운 값은 {near}" if near else ""),
                                     "근거 표기 그대로", evidence_id=p.refs[0] if p.refs else None))
    for loc, text, ids in [("title", page.title, None), ("summary", page.summary, None), *_number_slots(page)]:
        ids = all_ids if ids is None else ids
        for f, near in _numbers_ok(text, ids, pack, with_units=True):
            issues.append(_issue(loc, "number_mismatch", f"{loc}의 '{f}'가 {'이 토픽 근거' if ids is all_ids else ', '.join(ids)}에 없음"
                                 + (f". 근거의 가까운 값은 {near}" if near else ""),
                                 "근거 표기 그대로(근거 값끼리 빼거나 나눈 값을 새로 만들지 않음)"))
    for loc, value, ids in _value_slots(page):
        if ids and _value_mismatch(value, ids, pack):
            issues.append(_issue(loc, "number_mismatch", f"{loc} 값 '{value}'가 {', '.join(ids)}에 없음",
                                 "근거 표기 그대로", evidence_id=ids[0]))
    return issues


def _check_style(page: TopicPage) -> list[Issue]:
    """문체: 명사형 칸(heading)이 문장으로 끝남, summary는 '~다', 해요체·평가어."""
    issues: list[Issue] = []
    for i, s in enumerate(page.sections):
        if ends_as_sentence(plain(s.heading)):
            issues.append(_issue(f"sections[{i}].heading", "format", f"heading이 문장으로 끝남('…{plain(s.heading)[-12:]}')",
                                 "명사형 끝(~함, ~임, 명사)"))
    for loc2, text2 in _text_slots(page):
        for sent in sentences(plain(text2)):
            if not sent.strip().rstrip(".").endswith("다"):
                issues.append(_issue(loc2, "format", f"{loc2}의 문장이 '~다'로 끝나지 않음('…{sent.strip()[-12:]}')",
                                     "문장마다 평서체 '~다'"))
    for loc, text in _canon_slots(page):
        t = plain(text)
        bad = ["해요체"] if any(is_haeyo(s) for s in sentences(t)) else []
        bad += [e for e in EVAL_ENDINGS if e in t]
        if loc.startswith("sections") and "paragraphs" in loc:
            bad += [e for e in EVAL_WORDS if e in t]
        if bad:
            issues.append(_issue(loc, "format", f"{loc} 금지 표현: {', '.join(bad)}",
                                 "평가어·해요체를 빼고 사실로 끝맺음. 그 문장만 고친 새 값을 낸다"))
    return issues


def check(page: TopicPage, pack: dict[str, list[EvidenceItem]], n_sources: int, cfg: BriefConfig) -> list[Issue]:
    return [*_check_counts(page, cfg, n_sources), *_check_refs(page, pack), *_check_numbers(page, pack),
            *_check_visual_structure(page, cfg), *_check_style(page)]


# ---------- 경고 ----------
def warnings(page: TopicPage, pack: dict[str, list[EvidenceItem]], cfg: BriefConfig) -> list[str]:
    out = []
    n_visual = sum(1 for s in page.sections if s.visual != "none")
    if page.sections and n_visual > len(page.sections) / 2:
        out.append(f"남발 의심: visual≠none {n_visual}/{len(page.sections)}절(절의 절반 넘음)")
    paras = [(i, j, plain(p.text)) for i, s in enumerate(page.sections) for j, p in enumerate(s.paragraphs)]
    for a in range(len(paras)):
        for b in range(a + 1, len(paras)):
            if SequenceMatcher(None, paras[a][2], paras[b][2]).ratio() >= cfg.review.duplicate_point_similarity:
                out.append(f"중복 의심: sections[{paras[a][0]}].paragraphs[{paras[a][1]}] ↔ "
                           f"sections[{paras[b][0]}].paragraphs[{paras[b][1]}]")
    summary_sents = sentences(plain(page.summary))
    for i, j, text in paras:
        for sent in sentences(text):
            if any(SequenceMatcher(None, su, sent).ratio() >= 0.8 for su in summary_sents):
                out.append(f"중복 의심: summary ↔ sections[{i}].paragraphs[{j}]")
                break
    tile_values = {plain(str(t.value)) for t in page.head_tiles}
    for i, s in enumerate(page.sections):
        if s.bars is not None and any(plain(str(it.value)) in tile_values for it in s.bars.items):
            out.append(f"반복 의심: head_tiles 수치가 sections[{i}].bars에 다시 나옴")
        if s.visual == "tiles" and any(plain(str(t.value)) in tile_values for t in s.tiles):
            out.append(f"반복 의심: head_tiles 수치가 sections[{i}].tiles에 다시 나옴")
        if s.table is not None and any(plain(cell) in tile_values for row in s.table.rows for cell in row[1:]):
            out.append(f"반복 의심: head_tiles 수치가 sections[{i}].table에 다시 나옴")
    return out


def run_checks(page: TopicPage, pack: dict[str, list[EvidenceItem]], n_sources: int, cfg: BriefConfig,
               canon: dict[str, str], slide_candidates: list[str], timeline_secs: set[int],
               translit: list[tuple[re.Pattern[str], str]] | None = None) -> CheckResult:
    sections_hi = cfg.write.sections_for(n_sources)[1]
    fixed, fixes = autofix(page, cfg, canon, slide_candidates, timeline_secs, sections_hi, translit)
    return CheckResult(fixed, fixes, check(fixed, pack, n_sources, cfg), warnings(fixed, pack, cfg))
