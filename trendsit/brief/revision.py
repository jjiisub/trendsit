"""작성자 수정(writer_revise) 결과를 이전 판에 합치기: 지적된 위치(최상위 칸 기준)만 합치고 그 밖의 변경은 되돌린다(write.py가 씀)."""

from __future__ import annotations

import re

from ..core.artifacts_brief import (
    Concept,
    Contribution,
    EventGroup,
    EventItem,
    NumberGroup,
    NumberItem,
    Point,
    TopicPage,
    TopicPageRevision,
)

LOC = re.compile(r"^(title|summary|overview)$|^(points|numbers|events|contributions|concepts)\[(\d+)\]")
LIST_LOC = re.compile(r"^(points|numbers|events|contributions|concepts)$")
SUB_LOC = re.compile(r"^(numbers|events)\[(\d+)\]\.(items|context|title|unit)(?:\[(\d+)\])?$")
FIELD_TYPES: dict[str, type] = {"points": Point, "numbers": NumberGroup, "events": EventGroup,
                                "contributions": Contribution, "concepts": Concept}


def top_loc(loc: str) -> str:
    m = LOC.match(loc.strip())
    if not m:
        return loc.strip()
    return m.group(1) or f"{m.group(2)}[{m.group(3)}]"


def normalize_loc(page: TopicPage, loc: str) -> str:
    """모델이 위치를 1부터 세면(마지막 다음 번호, 예: 항목 2개인데 [2]) 0부터로 바로잡는다. 그 밖은 그대로."""
    m = LOC.match(loc.strip())
    if not m or m.group(1):
        return loc
    name, idx = m.group(2), int(m.group(3))
    n = len(getattr(page, name))
    if n and idx == n:
        return loc.replace(f"{name}[{idx}]", f"{name}[{idx - 1}]", 1)
    return loc


def apply_revision(prev: TopicPage, rev: TopicPageRevision, allowed: set[str]) -> tuple[TopicPage, int, list[str]]:
    """지적된 위치(최상위 칸 기준)만 합친다. 그 밖의 변경은 되돌림(세어 반환). 삭제는 뒤 번호부터."""
    data = prev.model_dump()
    reverts, notes, deletes = 0, [], []
    for ch in rev.changed:
        loc = top_loc(ch.loc if ch.action == "add" else normalize_loc(prev, ch.loc))
        whole = {a for a in allowed if LIST_LOC.match(a)}  # 목록 전체가 지적되면 그 목록의 항목 변경은 허용
        if loc not in allowed and loc.split("[")[0] not in whole and not (
                ch.action == "add" and loc.split("[")[0] in {a.split("[")[0] for a in allowed}):
            reverts += 1
            notes.append(f"지적 안 된 위치 {ch.loc} 변경 되돌림")
            continue
        if LIST_LOC.match(loc) and ch.action == "add":  # 목록 위치에 더하기(번호 없이 "contributions"): 끝에 붙임(G6)
            loc = f"{loc}[{len(data[loc])}]"
        m = LOC.match(loc)
        if not m and LIST_LOC.match(loc) and ch.action == "delete":
            if loc == "points":  # 포인트 전체 삭제는 받지 않음(필수 칸)
                notes.append("points 전체 삭제는 받지 않음")
                continue
            data[loc] = []  # 칸 전체 비우기(예: numbers 그룹을 문장으로 옮길 때)
            continue
        if not m:
            notes.append(f"알 수 없는 위치 {ch.loc}")
            continue
        sub = SUB_LOC.match(normalize_loc(prev, ch.loc).strip())
        if sub and not m.group(1):  # 하위 위치: numbers[i].items[j] / numbers[i].context·title / events[i].items[j]
            name, i, field_, j = sub.group(1), int(sub.group(2)), sub.group(3), sub.group(4)
            if i >= len(data[name]):
                notes.append(f"{ch.loc}: 위치 없음")
                continue
            group = data[name][i]
            if j is not None and field_ == "items":
                k = int(j)
                if ch.action == "delete" and k < len(group["items"]):
                    group["items"].pop(k)
                elif isinstance(ch.value, NumberItem if name == "numbers" else EventItem) and k < len(group["items"]):
                    group["items"][k] = ch.value.model_dump()
                else:
                    notes.append(f"{ch.loc}: 값 형식이 항목이 아님")
            elif j is None and field_ in ("context", "title", "unit") and isinstance(ch.value, str):
                group[field_] = ch.value
            else:
                notes.append(f"{ch.loc}: 바꿀 수 없는 하위 위치")
            continue
        if m.group(1):
            if ch.action == "edit" and isinstance(ch.value, str):
                data[m.group(1)] = ch.value
            continue
        name, idx = m.group(2), int(m.group(3))
        if ch.action == "delete":
            deletes.append((name, idx))
            continue
        val = ch.value
        if isinstance(val, str) and name == "points":
            val = Point(text=val, refs=data[name][idx]["refs"] if idx < len(data[name]) else [])
        if name == "contributions" and isinstance(val, Point):
            # 채널 없이 낸 기여 문장(OpenRig 재실행: 두 채널을 한 문장에, 반영 확인 리뷰 G6). refs가 한 채널이면 그 채널로
            chans = {"video" if r.startswith("vd:") else "github" if r.startswith("rp:") else "text" for r in val.refs}
            if len(chans) == 1:
                val = Contribution(channel=chans.pop(), text=val.text, refs=val.refs)  # type: ignore[arg-type]
            else:
                notes.append(f"{ch.loc}: 기여 문장이 채널 {sorted(chans)}를 한 문장에 섞음(채널마다 1문장)")
                continue
        if not isinstance(val, FIELD_TYPES[name]):
            notes.append(f"{ch.loc}: 값 형식이 {FIELD_TYPES[name].__name__}가 아님")
            continue
        if ch.action == "edit" and idx < len(data[name]):
            data[name][idx] = val.model_dump()
        else:
            data[name].append(val.model_dump())
    for name, idx in sorted(deletes, key=lambda x: -x[1]):
        if idx < len(data[name]):
            data[name].pop(idx)
    try:
        return TopicPage.model_validate(data), reverts, notes
    except ValueError as e:  # 하위 위치에 형식이 다른 값: 이 수정은 버림
        return prev, reverts, [*notes, f"합친 판이 스키마에 맞지 않아 이 수정 버림: {str(e)[:100]}"]
