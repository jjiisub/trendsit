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
from ..core.style import EVAL_ENDINGS, EVAL_WORDS, ends_as_sentence, is_haeyo
from .evidence import EvidenceItem

HL = re.compile(r"==(.+?)==")
GENERIC_START = re.compile(r"^최근\s.*(업계|분야|시장)에서는")
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
REF = re.compile(r"(?:it|og|vd|rp):[\w./#@:-]+")
_SENT = re.compile(r"(?<=[.!?다])\s+")


# 앞에서부터 맞춰 보므로 긴 낱말(분기, 개월)을 짧은 낱말(분, 개)보다 먼저 둔다
UNIT_KINDS = (("%", ("%", "퍼센트", "%p", "포인트")), ("ms", ("ms", "밀리초")), ("s", ("초", "s", "sec")),
              ("$", ("$", "달러", "usd")), ("원", ("원",)), ("배", ("배", "x", "×")), ("tok/s", ("tok/s", "토큰/초")),
              ("분기", ("분기",)), ("h", ("시간", "hours", "hour", "h")), ("min", ("분", "min", "minutes")),
              ("개월", ("개월",)), ("개", ("개",)), ("명", ("명",)), ("회", ("회",)), ("건", ("건",)))
# 근거에 없는 전망·평가형 마무리(리뷰 R3-d, W40 Decision API "주목된다", "것으로 보인다")
# 반영 확인 리뷰 F11: "…것이 쟁점이다", "핵심 변화다", "핵심 축으로 부상했다"(평가형 마무리). "쟁점은 …이다"는 허용(writer.md 예시)
SPECULATIVE = ("주목된다", "것으로 보인다", "것으로 전망된다", "지 주목", "것이 쟁점이다", "핵심 변화다", "핵심 축으로", "부상했다")
# 영문 이름 뒤 조사: 끝 발음에 받침이 있는데 받침 없는 조사(가·는·를·와). "Anthropic가" → "Anthropic이"(반영 확인 리뷰 G3)
BAD_PARTICLE = re.compile(r"(?<![A-Za-z])([A-Za-z]*[a-z][cktpmnl])(가|는|를|와)(?![가-힣])")
PER_MILLION = re.compile(r"100만\s?토큰당|per\s?(1M|million)|/\s?1M|MTok|million tokens", re.IGNORECASE)
BARE_PER_TOKEN = re.compile(r"(?<!만)(?<!만 )(?<!M )(?<!1M )토큰당")
_VAL = re.compile(r"(\$)?(?<![\d.])(\d+(?:[.,]\d+)?)\s?([%a-zA-Z가-힣/×]{0,6})")
CONCEPT_DESC_MIN = 15  # 이보다 짧은 개념 풀이는 풀이가 없는 것으로 보고 뺀다(G7: "베타 출시된 기능")
COUNT_UNITS = {"개", "명", "건", "회", "편", "종", "곳", "개국", "차원", "개월", "년"}
LABEL_UNIT = re.compile(r"\(([^()]+)\)\s*$")


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
            channels: set[str] | None = None, n_sources: int | None = None,
            translit: list[tuple[re.Pattern[str], str]] | None = None) -> tuple[TopicPage, list[dict[str, Any]]]:
    hl = cfg.write.highlights
    fixes: list[dict[str, Any]] = []
    # 00) points 개수 초과: 중요도 순이라 뒤에서 자른다. 잘린 포인트에 붙은 도식도 뺌(리뷰 R4, SIFT 소스 1개에 4개)
    if n_sources is not None:
        hi = cfg.write.points["multi_source" if n_sources > 1 else "single_source"][1]
        if len(page.points) > hi:
            fixes.append({"loc": "points", "rule": f"points {len(page.points)}개 → {hi}개(근거 소스 {n_sources}개, 뒤에서 자름)",
                          "before": [p.text for p in page.points[hi:]], "after": []})
            page = page.model_copy(update={"points": page.points[:hi],
                                           "numbers": [g for g in page.numbers if g.anchor <= hi],
                                           "events": [g for g in page.events if g.anchor <= hi]})
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
    # 0-0) 풀이가 없는 개념(짧은 풀이)은 뺀다(G7, writer.md "풀이가 없으면 넣지 않는다")
    thin = [c for c in page.concepts if len(plain(c.desc).strip()) < CONCEPT_DESC_MIN]
    if thin:
        fixes.append({"loc": "concepts", "rule": f"풀이가 {CONCEPT_DESC_MIN}자 미만인 개념 뺌", "before": [c.term for c in thin],
                      "after": []})
        page = page.model_copy(update={"concepts": [c for c in page.concepts if c not in thin]})
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
            # 단어 경계(영문·숫자가 앞뒤에 붙으면 다른 낱말: 'Aider'의 'AI' 같은 오치환 방지, 리뷰 지적 11)
            pat = rf"(?<![A-Za-z0-9]){re.escape(alias)}(?![A-Za-z0-9])"
            if alias and re.search(pat, new) and canon[alias] not in new:
                new = re.sub(pat, canon[alias], new)
        for tp, target in translit or []:  # 음차 표기 → 정본(띄어쓰기·하이픈 무관, F10)
            new = tp.sub(target, new)
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
    """대조용 근거 글. 글 카드의 주장 줄과 요약은 원문이 아니라 빼고(리뷰 R2), quote·수치·영상·레포 칸만."""
    out = []
    for i in ids:
        for it in pack.get(i, []):
            if it.kind == "summary" or (it.kind == "claim" and it.channel == "text"):
                continue
            out.append(f"{it.text} {it.value or ''}{it.unit or ''}")
    return " ".join(out)


def _numbers_ok(text: str, ids: list[str], pack: dict[str, list[EvidenceItem]]) -> list[tuple[str, str]]:
    """본문 수치(figures 규칙) 중 근거에 같은 값이 없는 것과 근거의 비슷한 값(힌트). 부분 문자열이 아니라 값으로 비교
    ('3.7'이 '13.75' 안에 있다고 통과하지 않게, 리뷰 R3-c)."""
    src = _ev_text(ids, pack)
    vals = number_values(src)
    out = []
    for f in figures(plain(text)):
        try:
            v = float(f.replace(",", ""))
        except ValueError:
            continue
        if any(same(v, w) for w in vals):
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
    # 근거 채널이 2개 이상이면 채널마다 1문장(리뷰 R12, OpenRig: github 한 줄뿐이고 text 빠짐)
    channels = {it.channel for items in pack.values() for it in items}
    missing = sorted(channels - {c.channel for c in page.contributions}) if len(channels) >= 2 else []
    if missing:
        issues.append(_issue("contributions", "format", f"근거 채널 {sorted(channels)} 중 {missing}의 contributions 문장이 없음",
                             "채널마다 그 채널 근거가 더한 것 1문장(근거 id 포함)"))
    # 수치 대조(단위 환산 없이 값 비교)
    for i, p in enumerate(page.points):
        for f, near in _numbers_ok(p.text, p.refs, pack):
            issues.append(_issue(f"points[{i}]", "number_mismatch",
                                 f"points[{i}]의 '{f}'가 {', '.join(p.refs)}에 없음" + (f". 근거의 가까운 값은 {near}" if near else ""),
                                 "근거 표기 그대로", evidence_id=p.refs[0] if p.refs else None))
    # refs가 없는 칸(제목, 요약, 개요, 개념)은 토픽 근거 전체, 도식 제목·context·사건 글과 기여는 그 칸의 근거로(리뷰 R3-c:
    # 도식 제목 "3.7%p 높음" 같은 파생 수치가 대조 밖이었음)
    all_ids = list(pack)
    slots: list[tuple[str, str, list[str]]] = [(n, getattr(page, n), all_ids) for n in ("title", "summary", "overview")]
    slots += [(f"concepts[{i}]", c.desc, all_ids) for i, c in enumerate(page.concepts)]
    for g_i, g in enumerate(page.numbers):
        ids = [it.ref for it in g.items] + REF.findall(g.context)
        slots += [(f"numbers[{g_i}].title", g.title, ids), (f"numbers[{g_i}].context", REF.sub("", g.context), ids)]
    for g_i, g in enumerate(page.events):
        ids = [it.ref for it in g.items if it.ref] + REF.findall(g.context)
        slots += [(f"events[{g_i}].title", g.title, ids), (f"events[{g_i}].context", REF.sub("", g.context), ids)]
        slots += [(f"events[{g_i}].items[{j}]", it.text, [it.ref]) for j, it in enumerate(g.items) if it.ref]
    slots += [(f"contributions[{i}]", c.text, c.refs) for i, c in enumerate(page.contributions)]
    for loc, text, ids in slots:
        for f, near in _numbers_ok(text, ids, pack):
            issues.append(_issue(loc, "number_mismatch", f"{loc}의 '{f}'가 {'이 토픽 근거' if ids is all_ids else ', '.join(ids)}에 없음"
                                 + (f". 근거의 가까운 값은 {near}" if near else ""),
                                 "근거 표기 그대로(근거 값끼리 빼거나 나눈 값을 새로 만들지 않음)"))
    for g_i, g in enumerate(page.numbers):
        for it_i, it in enumerate(g.items):
            vals = number_values(_ev_text([it.ref], pack))
            if it.ref in pack and not any(same(v, w_) for v in number_values(it.value) for w_ in vals):
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
    # "100만 토큰당" 근거를 "토큰당"으로 줄인 단위 왜곡(G3: Haiku "입력/출력 토큰당 $0.50/$2.50")
    for loc, text, ids in [*slots[:3], *[(f"points[{i}]", p.text, p.refs) for i, p in enumerate(page.points)]]:
        if BARE_PER_TOKEN.search(plain(text)) and PER_MILLION.search(_ev_text(ids, pack)):
            issues.append(_issue(loc, "number_mismatch", f"{loc}의 '토큰당'은 근거에서 '100만 토큰당'(per 1M)",
                                 "근거 기준 그대로 '100만 토큰당'"))
    # 막대 값의 단위를 근거 표기와 대조: 근거에서 그 값 바로 뒤 단위가 그룹 단위와 다르면 반려(W40 judge: ms 그룹에 1.6초, $ 그룹에 %)
    for g_i, g in enumerate(page.numbers):
        if not g.unit.strip("() \t"):  # 빈 단위(Jeff·Jeeves 정확도 "()", 리뷰 R3-b)
            issues.append(_issue(f"numbers[{g_i}]", "format", f"numbers[{g_i}] 단위가 비어 있음",
                                 "근거의 단위 그대로(단위 없는 비율·점수면 '점수', '비율'처럼 무엇인지)"))
        gu = unit_kind(g.unit)
        for it_i, it in enumerate(g.items):
            m = LABEL_UNIT.search(it.label)  # 라벨 끝 괄호 단위("CPU 시간(시간)")도 그룹 단위와 대조
            lu = unit_kind(m.group(1)) if m else None
            if gu and lu and lu != gu:
                issues.append(_issue(f"numbers[{g_i}].items[{it_i}]", "number_mismatch",
                                     f"numbers[{g_i}].items[{it_i}] 라벨 단위 '{m.group(1)}'가 그룹 단위 {g.unit}와 다름",  # type: ignore[union-attr]
                                     "같은 단위 값만 한 그룹에(다르면 그룹을 나누거나 문장으로)", evidence_id=it.ref))
                continue
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
    # 요약·개요는 문장마다 "~다"(마지막 문장만 보던 것을 고침, 반영 확인 리뷰 F1: Solar 개요 "…제공함. …낮음. …전환된다.")
    for name in ("summary", "overview"):
        for sent in sentences(plain(getattr(page, name))):
            if not sent.strip().rstrip(".").endswith("다"):
                issues.append(_issue(name, "format", f"{name}의 문장이 '~다'로 끝나지 않음('…{sent.strip()[-12:]}')",
                                     "요약·개요는 문장마다 평서체 '~다'(명사형 '~함', '~음' 아님)"))
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
        bad += [e for e in (*EVAL_ENDINGS, *SPECULATIVE) if e in t]
        if loc.startswith("points"):
            bad += [e for e in EVAL_WORDS if e in t]
        if GENERIC_START.search(t):
            bad.append("일반론 시작")
        if "!" in t:
            bad.append("감탄")
        if t.rstrip().endswith("?"):
            bad.append("질문형 끝")
        if EMOJI.search(t):
            bad.append("이모지")
        if (m := BAD_PARTICLE.search(t)):
            bad.append(f"조사 '{m.group(0)}'(영문 이름 끝 받침이면 이/은/을/과)")
        if bad:
            hint = "담백한 서술로"
            if any(e in t for e in SPECULATIVE):
                hint = ("근거 밖 전망·평가 마무리를 빼고 근거의 사실로 끝맺음(예: '…가속화할 것으로 보인다' → 그 문장 삭제, "
                        "'…자리잡을지 주목된다' → '…를 공개했다'). 그 문장만 고친 새 값을 낸다")
            elif any(e in t for e in EVAL_ENDINGS) or any(e in t for e in EVAL_WORDS):
                hint = ("평가어를 빼고 사실로 끝맺음(예: '…확장하는 것이 핵심이다' → '…확장하는 구조다', "
                        "'…가 눈에 띈다' → '…를 기록했다'). 그 문장만 고친 새 값을 낸다")
            elif "해요체" in bad:
                hint = "'~요'를 '~다'(요약·개요) 또는 명사형(포인트)으로"
            issues.append(_issue(loc, "format", f"{loc} 금지 표현: {', '.join(bad)}", hint))
    return issues


# ---------- 경고 ----------
# angle 핵심 낱말 뽑기: 조사를 떼고 2글자 이상, 어느 토픽에나 나오는 일반어는 뺀다
_PARTICLE = re.compile(r"(으로|에서|에게|과의|와의|의|와|과|을|를|이|가|은|는|에|로|도|만)$")
_GENERIC = {"모델", "출시", "공개", "발표", "기능", "성능", "가격", "비용", "사용", "지원", "변화", "영향", "전략", "방식",
            "구조", "비교", "중심", "관점", "의미", "축", "대한", "통한", "위한", "가능한", "새로운"}


def angle_words(angle: str) -> set[str]:
    words = set()
    for w in re.findall(r"[A-Za-z][\w.\-]*|[가-힣]+", angle or ""):
        w = _PARTICLE.sub("", w) if re.match(r"[가-힣]", w) else w
        if len(w) >= 2 and w not in _GENERIC:
            words.add(w.lower())
    return words


def warnings(page: TopicPage, pack: dict[str, list[EvidenceItem]], cfg: BriefConfig, angle: str = "") -> list[str]:
    out = []
    # angle 핵심 낱말이 summary 첫 문장과 첫 두 point에 하나도 없으면 경고 → 검수자가 missing_key로 본다(F7, 설계 결정
    # C-23: 첫 point는 이번 주 사건이어도 되고 angle 핵심은 요약 첫 문장 또는 첫 두 point 안). 반려가 아니라 경고로만
    words = angle_words(angle)
    head = " ".join([*(sentences(plain(page.summary))[:1]), *(plain(p.text) for p in page.points[:2])]).lower()
    if words and page.points and not any(w in head for w in words):
        out.append(f"핵심 의심: 다룰 축(angle '{angle}')의 낱말({', '.join(sorted(words))})이 summary 첫 문장과 첫 두 point에 없음")
    # 같은 비교 대상 = 같은 근거 문장(id) 안의 같은 단위 값. 개수 단위(개·명 등)와 단위 없는 값은 비교 막대 대상으로 보지
    # 않는다(반영 확인 리뷰 F3: 글쓴이 환경의 "스킬 약 50개·에이전트 약 20개"가 "약개 3"으로, 차원 768/512/256이 셈에 들어감)
    by_unit: dict[tuple[str, str], int] = {}
    for eid, items in pack.items():
        for it in items:
            if it.kind in ("number", "slide_fact") and it.value:
                raw = it.unit or re.sub(r"[\d.,\s]", "", it.value)
                u = re.sub(r"^(약|최대|최소|평균|~|±)+", "", raw.strip()).strip()
                if u and u not in COUNT_UNITS:
                    by_unit[(eid, u)] = by_unit.get((eid, u), 0) + 1
    many = [(e, u, n) for (e, u), n in by_unit.items() if n >= 3]
    if not page.numbers and many:
        out.append("누락 의심(같은 근거 문장의 같은 단위 값 3개 이상, 같은 지표 비교인지 확인): " +
                   ", ".join(f"{e} {u} {n}개" for e, u, n in many))
    # 한 point 안에 같은 단위 값 3개 이상인데 그 point에 붙은 도식이 없으면 누락 의심(G2: textGrain 92→66→17%,
    # Haiku 구간 가격). 차원·개수 단위는 빼는 F3 조건 그대로
    anchored = {g.anchor for g in [*page.numbers, *page.events]}
    for i, p in enumerate(page.points):
        kinds: dict[str, list[str]] = {}
        for m in _VAL.finditer(plain(p.text)):
            k = "$" if m.group(1) else unit_kind(m.group(3))
            if k and k not in COUNT_UNITS and k not in ("개", "명", "회", "건", "개월", "분기"):
                kinds.setdefault(k, []).append(m.group(2))
        many_p = {k: v for k, v in kinds.items() if len(v) >= 3}
        if many_p and (i + 1) not in anchored:
            out.append(f"누락 의심: points[{i}] 안에 같은 단위 값 3개 이상(" +
                       ", ".join(f"{k} {'/'.join(v)}" for k, v in many_p.items()) + "), 같은 지표면 numbers")
    dates = {d for items in pack.values() for it in items for d in re.findall(r"\d{4}-\d{2}-\d{2}", it.text)}
    dates |= {it.source.get("date") for items in pack.values() for it in items if it.source.get("date")}
    if not page.events and len(dates) >= 3:
        out.append(f"누락 의심: events가 비었는데 근거에 날짜 다른 사건 후보 {len(dates)}개")
    for g_i, g in enumerate(page.numbers):
        if unit_kind(g.unit):
            for it_i, it in enumerate(g.items):
                if it.ref in pack and evidence_unit(it.value, _ev_text([it.ref], pack)) is None:
                    out.append(f"단위 확인 필요: numbers[{g_i}].items[{it_i}] 값 {it.value}의 근거 단위를 찾지 못함"
                               f"(그룹 단위 {g.unit})")
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
               canon: dict[str, str], translit: list[tuple[re.Pattern[str], str]] | None = None,
               angle: str = "") -> CheckResult:
    fixed, fixes = autofix(page, cfg, canon, {it.channel for items in pack.values() for it in items}, n_sources, translit)
    return CheckResult(fixed, fixes, check(fixed, pack, n_sources, cfg), warnings(fixed, pack, cfg, angle))
