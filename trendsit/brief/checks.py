"""작성자 출력의 코드 검사(S5_TASK 5.7, LLM 0원). 검수자 앞에서 돈다.

1. 고칠 수 있는 형식은 직접 고친다(반려하지 않음): 형광 개수 초과(뒤쪽부터 제거), 공백·문장부호, 별칭 표기 → 정본
2. 반려(라운드에 셈): 필수 칸·분량, refs 실재, 수치 대조, 도식 칸 규칙, concepts·contributions 조건, 금지어
3. 경고(검수자 입력으로): 도식 누락·남발 의심, 같은 point 중복
반려 메시지는 위치·근거·힌트를 구체적으로(예: "points[2]의 '15%'가 it:812#q2에 없음. 근거의 값은 1.5%").
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
from ..core.style import EVAL_ENDINGS, ends_as_sentence, is_haeyo
from .evidence import EvidenceItem

HL = re.compile(r"==(.+?)==")
GENERIC_START = re.compile(r"^최근\s.*(업계|분야|시장)에서는")
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
REF = re.compile(r"(?:it|og|vd|rp):[\w./#@:-]+")
_SENT = re.compile(r"(?<=[.!?다])\s+")


UNIT_KINDS = (("%", ("%", "퍼센트", "%p", "포인트")), ("ms", ("ms", "밀리초")), ("s", ("초", "s", "sec")),
              ("$", ("$", "달러", "usd")), ("원", ("원",)), ("배", ("배", "x", "×")), ("tok/s", ("tok/s", "토큰/초")))


def unit_kind(text: str) -> str | None:
    """단위 표기의 종류. 앞에서부터 본다('$/1M tokens' → $, '초' → s). 한 글자 영문 단위(s, x)는 단독일 때만."""
    t = (text or "").strip().lower()
    if not t:
        return None
    for kind, words in UNIT_KINDS:
        for w in words:
            if len(w) == 1 and w.isascii() and w.isalpha():
                if t == w:
                    return kind
            elif t.startswith(w):
                return kind
    return None


def evidence_unit(value: str, src: str) -> str | None:
    """근거 글에서 값(숫자) 바로 앞뒤에 붙은 단위 종류. 못 찾으면 None(대조하지 않음)."""
    num = re.sub(r"[^\d.]", "", value or "")
    if not num:
        return None
    for m in re.finditer(rf"(\$?)(?<![\d.]){re.escape(num)}(?![\d])\s?([%a-zA-Z가-힣/×]{{0,6}})", src):
        if m.group(1):
            return "$"
        k = unit_kind(m.group(2))
        if k:
            return k
    return None


def sentences(text: str) -> list[str]:
    return [s for s in _SENT.split((text or "").strip()) if s.strip()]


def plain(text: str) -> str:
    return HL.sub(r"\1", text or "")


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
    """형광을 셀 순서(summary → overview → points)와 위치 이름."""
    out = [("summary", page.summary), ("overview", page.overview)]
    out += [(f"points[{i}]", p.text) for i, p in enumerate(page.points)]
    return out


def _set(page: TopicPage, loc: str, text: str) -> TopicPage:
    if loc in ("summary", "overview", "title"):
        return page.model_copy(update={loc: text})
    i = int(loc[loc.index("[") + 1:-1])
    pts = list(page.points)
    pts[i] = pts[i].model_copy(update={"text": text})
    return page.model_copy(update={"points": pts})


def autofix(page: TopicPage, cfg: BriefConfig, canon: dict[str, str],
            channels: set[str] | None = None) -> tuple[TopicPage, list[dict[str, Any]]]:
    hl = cfg.write.highlights
    fixes: list[dict[str, Any]] = []
    # 0) contributions: 근거 채널이 2개 이상일 때만, 그 채널만, 채널마다 1문장(넘치는 것은 뺌)
    if channels is not None and page.contributions:
        keep, seen = [], set()
        for c in page.contributions:
            if len(channels) >= 2 and c.channel in channels and c.channel not in seen:
                keep.append(c)
                seen.add(c.channel)
        if keep != page.contributions:
            fixes.append({"loc": "contributions", "rule": f"근거 채널 {sorted(channels)}에 맞게 contributions 정리",
                          "before": [c.model_dump() for c in page.contributions], "after": [c.model_dump() for c in keep]})
            page = page.model_copy(update={"contributions": keep})
    # 0-1) 도식 그리는 조건(skills/diagrams.md): 맞지 않는 그룹은 빼고 포인트 문장만 남김
    #   numbers: 값 3개 이상 / 또는 값 2개 + baseline + summary에 그 값이나 라벨이 나옴. events: 3개 이상 / 또는 2개 + flow_is_point
    def drawable(g: Any) -> bool:
        if len(g.items) >= 3:
            return True
        if len(g.items) == 2 and any(it.baseline for it in g.items):
            return any(it.value in page.summary or it.label in page.summary for it in g.items)
        return False

    nums = [g for g in page.numbers if drawable(g)]
    evs = [g for g in page.events if len(g.items) >= 3 or (len(g.items) == 2 and g.flow_is_point)]
    if len(nums) != len(page.numbers) or len(evs) != len(page.events):
        fixes.append({"loc": "numbers/events", "rule": "그리는 조건에 맞지 않는 도식 뺌(값 2개·사건 2개 등)",
                      "before": [g.title for g in [*page.numbers, *page.events]],
                      "after": [g.title for g in [*nums, *evs]]})
        page = page.model_copy(update={"numbers": nums, "events": evs})
    # 1) 별칭 → 정본(긴 표기부터, 단어 경계가 애매한 한글은 그대로 치환)
    for loc, text in [*_text_slots(page), ("title", page.title)]:
        new = text
        for alias in sorted(canon, key=len, reverse=True):
            if alias and alias in new and canon[alias] not in new:
                new = new.replace(alias, canon[alias])
        if new != text:
            fixes.append({"loc": loc, "rule": "별칭 표기를 정본으로", "before": text, "after": new})
            page = _set(page, loc, new)
    # 2) 공백·문장부호: 겹친 공백, 문장부호 앞 공백, 같은 부호 반복
    for loc, text in [*_text_slots(page), ("title", page.title)]:
        new = re.sub(r"\s{2,}", " ", text).strip()
        new = re.sub(r"\s+([,.;:])", r"\1", new)
        new = re.sub(r"([.,])\1+", r"\1", new)
        if new != text:
            fixes.append({"loc": loc, "rule": "공백·문장부호 정리", "before": text, "after": new})
            page = _set(page, loc, new)
    # 3) 형광: 칸별 상한(summary 1, overview 1, 포인트당 1), 페이지 상한(page 최대값). 넘치면 뒤쪽부터 제거
    limits = {"summary": hl.summary, "overview": hl.overview}
    total = 0
    for loc, text in _text_slots(page):
        cap = limits.get(loc, hl.per_point)
        marks = HL.findall(text)
        keep = max(0, min(cap, hl.page[1] - total))
        if len(marks) > keep:
            parts = HL.split(text)  # 짝수 칸: 일반 글, 홀수 칸: 형광 안 글
            new = "".join(p if i % 2 == 0 else (f"=={p}==" if (i + 1) // 2 <= keep else p) for i, p in enumerate(parts))
            fixes.append({"loc": loc, "rule": f"형광 {len(marks)}개 → {keep}개(뒤쪽부터 제거)", "before": text, "after": new})
            page = _set(page, loc, new)
        total += min(len(marks), keep)
    return page, fixes


# ---------- 반려 ----------
def _ev_text(ids: list[str], pack: dict[str, list[EvidenceItem]]) -> str:
    out = []
    for i in ids:
        for it in pack.get(i, []):
            out.append(f"{it.text} {it.value or ''}{it.unit or ''}")
    return " ".join(out)


def _numbers_ok(text: str, ids: list[str], pack: dict[str, list[EvidenceItem]]) -> list[tuple[str, str]]:
    """본문 수치(figures 규칙) 중 근거에 같은 값이 없는 것과 근거의 비슷한 값(힌트)."""
    src = _ev_text(ids, pack)
    vals = number_values(src)
    out = []
    for f in figures(plain(text)):
        try:
            v = float(f.replace(",", ""))
        except ValueError:
            continue
        if f in src.replace(",", "") or any(same(v, w) for w in vals):
            continue
        near = sorted(set(vals), key=lambda w: abs(w - v))[:3]
        out.append((f, ", ".join(f"{x:g}" for x in near)))
    return out


def check(page: TopicPage, pack: dict[str, list[EvidenceItem]], n_sources: int, cfg: BriefConfig) -> list[Issue]:
    w = cfg.write
    issues: list[Issue] = []
    for name in ("title", "summary", "overview"):
        if not getattr(page, name).strip():
            issues.append(_issue(name, "format", f"{name}이 비어 있음", "필수 칸"))
    ns = len(sentences(plain(page.summary)))
    if ns > w.summary_sentences[1]:
        issues.append(_issue("summary", "format", f"summary {ns}문장(최대 {w.summary_sentences[1]})", "결론 문장만 남김"))
    no = len(sentences(plain(page.overview)))
    if page.overview.strip() and not w.overview_sentences[0] <= no <= w.overview_sentences[1]:
        issues.append(_issue("overview", "format", f"overview {no}문장({w.overview_sentences[0]}~{w.overview_sentences[1]})",
                             "1문단"))
    lo, hi = w.points["multi_source" if n_sources > 1 else "single_source"]
    if not lo <= len(page.points) <= hi:
        issues.append(_issue("points", "format", f"points {len(page.points)}개(근거 소스 {n_sources}개면 {lo}~{hi}개)",
                             "중요도 순으로 개수 맞춤"))
    for i, p in enumerate(page.points):
        loc = f"points[{i}]"
        if len(plain(p.text).split()) <= 3:
            issues.append(_issue(loc, "format", f"{loc}이 너무 짧음('{p.text}')", "1~2문장 80자 안팎"))
        if not 1 <= len(p.refs) <= cfg.evidence.max_refs_per_point:
            issues.append(_issue(loc, "wrong_ref", f"{loc} refs {len(p.refs)}개(1~{cfg.evidence.max_refs_per_point})",
                                 "그 문장을 받치는 근거 id만"))
    # refs 실재
    def refs_exist(loc: str, ids: list[str]) -> None:
        for r in ids:
            if r not in pack:
                issues.append(_issue(loc, "wrong_ref", f"{loc}의 근거 id {r}가 이 토픽 근거 목록에 없음",
                                     "근거 목록의 id만", evidence_id=r))
    for i, p in enumerate(page.points):
        refs_exist(f"points[{i}]", p.refs)
    for g_i, g in enumerate(page.numbers):
        refs_exist(f"numbers[{g_i}]", [it.ref for it in g.items])
        refs_exist(f"numbers[{g_i}].context", REF.findall(g.context))
    for g_i, g in enumerate(page.events):
        refs_exist(f"events[{g_i}]", [it.ref for it in g.items if it.ref])
        refs_exist(f"events[{g_i}].context", REF.findall(g.context))
    for c_i, c in enumerate(page.contributions):
        refs_exist(f"contributions[{c_i}]", c.refs)
    # 수치 대조(단위 환산 없이 값 비교)
    for i, p in enumerate(page.points):
        for f, near in _numbers_ok(p.text, p.refs, pack):
            issues.append(_issue(f"points[{i}]", "number_mismatch",
                                 f"points[{i}]의 '{f}'가 {', '.join(p.refs)}에 없음" + (f". 근거의 가까운 값은 {near}" if near else ""),
                                 "근거 표기 그대로", evidence_id=p.refs[0] if p.refs else None))
    all_ids = list(pack)
    for name in ("summary", "overview"):
        for f, near in _numbers_ok(getattr(page, name), all_ids, pack):
            issues.append(_issue(name, "number_mismatch", f"{name}의 '{f}'가 이 토픽 근거에 없음"
                                 + (f". 근거의 가까운 값은 {near}" if near else ""), "근거 표기 그대로"))
    for g_i, g in enumerate(page.numbers):
        for it_i, it in enumerate(g.items):
            vals = number_values(_ev_text([it.ref], pack))
            if it.ref in pack and not any(same(v, w_) for v in number_values(it.value) for w_ in vals) \
                    and it.value.replace(",", "") not in _ev_text([it.ref], pack).replace(",", ""):
                issues.append(_issue(f"numbers[{g_i}].items[{it_i}]", "number_mismatch",
                                     f"numbers[{g_i}].items[{it_i}] 값 '{it.value}'가 {it.ref}에 없음", "근거 표기 그대로",
                                     evidence_id=it.ref))
    # 도식 칸
    n_points = len(page.points)
    anchors = [g.anchor for g in page.numbers] + [g.anchor for g in page.events]
    for name, groups, cap in (("numbers", page.numbers, w.diagrams.numbers_groups_max),
                              ("events", page.events, w.diagrams.events_groups_max)):
        if len(groups) > cap:
            issues.append(_issue(name, "overuse", f"{name} {len(groups)}그룹(최대 {cap})", "가장 중요한 것만"))
        for g_i, g in enumerate(groups):
            loc = f"{name}[{g_i}]"
            if not 1 <= g.anchor <= n_points:
                issues.append(_issue(loc, "format", f"{loc} anchor {g.anchor}가 포인트 번호(1~{n_points})가 아님",
                                     "붙을 포인트 번호"))
            if not g.title.strip() or not g.context.strip():
                issues.append(_issue(loc, "format", f"{loc} title·context 필요", "무엇을 어떤 조건에서 비교했는지 1~2문장"))
            if not 2 <= len(g.items) <= 6:
                issues.append(_issue(loc, "format", f"{loc} 항목 {len(g.items)}개(2~6)", ""))
    if len(anchors) != len(set(anchors)):
        issues.append(_issue("numbers", "format", f"한 포인트에 도식 둘 이상(anchor {anchors})", "한 포인트에 도식 하나"))
    # 막대 값의 단위를 근거 표기와 대조: 근거에서 그 값 바로 뒤 단위가 그룹 단위와 다르면 반려(W40 judge: ms 그룹에 1.6초, $ 그룹에 %)
    for g_i, g in enumerate(page.numbers):
        gu = unit_kind(g.unit)
        for it_i, it in enumerate(g.items):
            ev_unit = evidence_unit(it.value, _ev_text([it.ref], pack))
            if gu and ev_unit and ev_unit != gu:
                issues.append(_issue(f"numbers[{g_i}].items[{it_i}]", "number_mismatch",
                                     f"numbers[{g_i}].items[{it_i}] 값 {it.value}의 근거 단위는 {ev_unit}인데 그룹 단위는 {g.unit}",
                                     "같은 단위 값만 한 그룹에(다르면 그룹을 나누거나 문장으로)", evidence_id=it.ref))
    for g_i, g in enumerate(page.numbers):
        mixed = {re.sub(r"[\d.,\s]", "", it.value) for it in g.items} - {"", g.unit}
        if len(mixed) > 1:
            issues.append(_issue(f"numbers[{g_i}]", "format", f"numbers[{g_i}] 단위가 섞임({sorted(mixed)})", "한 그룹 한 단위"))
    for g_i, g in enumerate(page.events):
        for it_i, it in enumerate(g.items):
            if not DATE.match(it.date):
                issues.append(_issue(f"events[{g_i}].items[{it_i}]", "format", f"날짜 '{it.date}'가 YYYY-MM-DD가 아님", ""))
            if not it.ref and not it.topic_id:
                issues.append(_issue(f"events[{g_i}].items[{it_i}]", "wrong_ref", "사건에 근거 id나 지난 토픽 id가 없음", ""))
    if len(page.concepts) > w.concepts_max:
        issues.append(_issue("concepts", "format", f"concepts {len(page.concepts)}개(최대 {w.concepts_max})", ""))
    # 명사형 칸: 포인트, 소스별 기여, 개념 풀이(skills/style_ko.md). 요약·개요는 "~다"
    for loc, text in [*[(f"points[{i}]", p.text) for i, p in enumerate(page.points)],
                      *[(f"contributions[{i}]", c.text) for i, c in enumerate(page.contributions)],
                      *[(f"concepts[{i}]", c.desc) for i, c in enumerate(page.concepts)]]:
        if ends_as_sentence(plain(text)):
            issues.append(_issue(loc, "format", f"{loc}이 문장으로 끝남('…{plain(text)[-12:]}')", "명사형 끝(~함, ~임, 명사)"))
    for name in ("summary", "overview"):
        t = plain(getattr(page, name)).strip()
        if t and not t.rstrip(".").endswith("다"):
            issues.append(_issue(name, "format", f"{name}이 '~다'로 끝나지 않음('…{t[-12:]}')", "평서체 '~다'"))
    # 금지어(모델 md에는 넣지 않음)
    texts = [("title", page.title), ("summary", page.summary), ("overview", page.overview)]
    texts += [(f"points[{i}]", p.text) for i, p in enumerate(page.points)]
    texts += [(f"contributions[{i}]", c.text) for i, c in enumerate(page.contributions)]
    texts += [(f"concepts[{i}]", c.desc) for i, c in enumerate(page.concepts)]
    for loc, text in texts:
        t = plain(text)
        bad = []
        if any(is_haeyo(s) for s in sentences(t)):
            bad.append("해요체")
        bad += [e for e in EVAL_ENDINGS if e in t]
        if GENERIC_START.search(t):
            bad.append("일반론 시작")
        if "!" in t:
            bad.append("감탄")
        if t.rstrip().endswith("?"):
            bad.append("질문형 끝")
        if EMOJI.search(t):
            bad.append("이모지")
        if bad:
            issues.append(_issue(loc, "format", f"{loc} 금지 표현: {', '.join(bad)}", "담백한 서술로"))
    return issues


# ---------- 경고 ----------
def warnings(page: TopicPage, pack: dict[str, list[EvidenceItem]], cfg: BriefConfig) -> list[str]:
    out = []
    by_unit: dict[str, int] = {}
    for items in pack.values():
        for it in items:
            if it.kind in ("number", "slide_fact") and it.value:
                u = (it.unit or re.sub(r"[\d.,\s]", "", it.value) or "-").strip()
                by_unit[u] = by_unit.get(u, 0) + 1
    if not page.numbers and any(n >= 3 for u, n in by_unit.items() if u != "-"):
        out.append("누락 의심: numbers가 비었는데 근거에 같은 단위 값 3개 이상(" +
                   ", ".join(f"{u} {n}" for u, n in by_unit.items() if n >= 3) + ")")
    dates = {d for items in pack.values() for it in items for d in re.findall(r"\d{4}-\d{2}-\d{2}", it.text)}
    dates |= {it.source.get("date") for items in pack.values() for it in items if it.source.get("date")}
    if not page.events and len(dates) >= 3:
        out.append(f"누락 의심: events가 비었는데 근거에 날짜 다른 사건 후보 {len(dates)}개")
    for g_i, g in enumerate(page.numbers):
        if len(g.items) == 2 and not any(it.baseline for it in g.items):
            out.append(f"남발 의심: numbers[{g_i}] 값 2개인데 baseline 없음")
    for g_i, g in enumerate(page.events):
        if len(g.items) == 2 and not g.flow_is_point:
            out.append(f"남발 의심: events[{g_i}] 사건 2개인데 flow_is_point 없음")
    pts = [plain(p.text) for p in page.points]
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            if SequenceMatcher(None, pts[i], pts[j]).ratio() >= cfg.review.duplicate_point_similarity:
                out.append(f"중복 의심: points[{i}] ↔ points[{j}]")
    return out


def run_checks(page: TopicPage, pack: dict[str, list[EvidenceItem]], n_sources: int, cfg: BriefConfig,
               canon: dict[str, str]) -> CheckResult:
    fixed, fixes = autofix(page, cfg, canon, {it.channel for items in pack.values() for it in items})
    return CheckResult(fixed, fixes, check(fixed, pack, n_sources, cfg), warnings(fixed, pack, cfg))
