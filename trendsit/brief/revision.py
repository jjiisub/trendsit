"""작성자 수정(writer_revise) 결과를 이전 판에 합치기(v2 위치 문법, S6-1 5.3): 지적된 위치(최상위 칸 기준)만 합치고
그 밖의 변경은 되돌린다(write.py가 씀)."""

from __future__ import annotations

import copy
import re

from ..core.artifacts_brief import (
    BarGroup,
    EventGroup,
    EventItem,
    NumberItem,
    Para,
    Section,
    Table,
    Tile,
    TopicPage,
    TopicPageRevision,
)

LOC = re.compile(r"^(title|summary)$|^(head_tiles|sections)\[(\d+)\]")
# sections[i].<하위>: heading/slide/video_secs(직접 칸), paragraphs[j]/tiles[j](목록 항목), bars/table/events(그룹 전체),
# bars.items[k]/table.rows[k]/events.items[k](그룹 안 항목)
SUB_LOC = re.compile(r"^sections\[(?P<i1>\d+)\]\.(?P<whole>heading|slide|slide_caption|video_secs|bars|table|events)$|"
                     r"^sections\[(?P<i2>\d+)\]\.(?P<list>paragraphs|tiles)\[(?P<idx2>\d+)\]$|"
                     r"^sections\[(?P<i3>\d+)\]\.(?P<nested>bars\.items|table\.rows|events\.items)\[(?P<idx3>\d+)\]$")
FIELD_TYPES: dict[str, type] = {"head_tiles": Tile, "sections": Section}
GROUP_TYPES: dict[str, tuple[str, type, type]] = {  # field_ -> (항목 칸 이름, 항목 값 타입, 그룹 전체 값 타입)
    "bars": ("items", NumberItem, BarGroup), "table": ("rows", list, Table), "events": ("items", EventItem, EventGroup)}


def _parse_sub(loc: str) -> tuple[int, str, int | None] | None:
    """sections[i].<하위>를 (절 번호, field_, idx) 로. field_는 heading/slide/video_secs/bars/table/events/paragraphs/tiles.
    bars.items·table.rows·events.items는 field_가 'bars'·'table'·'events'이고 idx가 항목 번호."""
    m = SUB_LOC.match(loc.strip())
    if not m:
        return None
    if m.group("whole") is not None:
        return int(m.group("i1")), m.group("whole"), None
    if m.group("list") is not None:
        return int(m.group("i2")), m.group("list"), int(m.group("idx2"))
    return int(m.group("i3")), m.group("nested").split(".")[0], int(m.group("idx3"))


def top_loc(loc: str) -> str:
    m = LOC.match(loc.strip())
    if not m:
        return loc.strip()
    return m.group(1) or f"{m.group(2)}[{m.group(3)}]"


def normalize_loc(page: TopicPage, loc: str) -> str:
    """모델이 위치를 1부터 세면(마지막 다음 번호) 0부터로 바로잡는다. 그 밖은 그대로."""
    m = LOC.match(loc.strip())
    if not m or m.group(1):
        return loc
    name, idx = m.group(2), int(m.group(3))
    n = len(getattr(page, name))
    if n and idx == n:
        return loc.replace(f"{name}[{idx}]", f"{name}[{idx - 1}]", 1)
    return loc


def _apply_group(sec: dict, field_: str, idx: int | None, value) -> list[str]:
    """bars·table·events 그룹 전체(idx None) 또는 그 안 항목(idx) 값 합치기(007-A2-19: 세 분기를 표로 합침)."""
    item_key, item_type, whole_type = GROUP_TYPES[field_]
    if idx is None and (value is None or isinstance(value, whole_type)):
        sec[field_] = value.model_dump() if value else None
        return []
    if idx is not None and sec.get(field_) and isinstance(value, item_type):
        items = sec[field_][item_key]
        dumped = value.model_dump() if hasattr(value, "model_dump") else value
        if int(idx) < len(items):
            items[int(idx)] = dumped
        else:
            items.append(dumped)
        return []
    return [f"sections.{field_}: 값 형식이 맞지 않음"]


def _apply_section_sub(sec: dict, field_: str, idx: int | None, value) -> tuple[dict, list[str]]:
    """sections[i].<field_>[idx] 하위 값 합치기. 실패하면 notes에 이유."""
    notes: list[str] = []
    if field_ == "heading" and isinstance(value, str):
        sec["heading"] = value
    elif field_ == "slide" and (value is None or isinstance(value, str)):
        sec["slide"] = value
    elif field_ == "slide_caption" and isinstance(value, str):
        sec["slide_caption"] = value
    elif field_ == "video_secs" and isinstance(value, list):
        sec["video_secs"] = value
    elif field_ == "paragraphs":
        if idx is None:
            notes.append("paragraphs 전체 교체는 받지 않음")
        elif isinstance(value, Para) and int(idx) < len(sec["paragraphs"]):
            sec["paragraphs"][int(idx)] = value.model_dump()
        elif isinstance(value, Para):
            sec["paragraphs"].append(value.model_dump())
        elif isinstance(value, str) and int(idx) < len(sec["paragraphs"]):  # v1.2 5.3: 문자열 value는 기존 refs 유지·text만 교체
            sec["paragraphs"][int(idx)]["text"] = value
        else:
            notes.append(f"sections.paragraphs[{idx}]: 값 형식이 Para가 아님")
    elif field_ == "tiles":
        if idx is not None and isinstance(value, Tile):
            if int(idx) < len(sec["tiles"]):
                sec["tiles"][int(idx)] = value.model_dump()
            else:
                sec["tiles"].append(value.model_dump())
        else:
            notes.append("sections.tiles: 값 형식이 맞지 않음")
    elif field_ in GROUP_TYPES:
        notes += _apply_group(sec, field_, idx, value)
    else:
        notes.append(f"알 수 없는 하위 위치 sections.{field_}")
    return sec, notes


def _delete_sub_item(sec: dict, field_: str, idx: int) -> str | None:
    """sections[i].<field_>[idx] 항목 하나 삭제. 실패하면 notes용 이유 문자열."""
    arr_name = {"paragraphs": "paragraphs", "tiles": "tiles"}.get(field_)
    if arr_name:
        if idx < len(sec[arr_name]):
            sec[arr_name].pop(idx)
            return None
        return "위치 없음"
    group = {"bars": "items", "table": "rows", "events": "items"}.get(field_)
    if group and sec.get(field_):
        items = sec[field_][group]
        if idx < len(items):
            items.pop(idx)
            return None
        return "위치 없음"
    return "삭제 대상 없음"


def _apply_sub_change(data: dict, i: int, field_: str, idx: int | None, action: str, value, loc: str) -> list[str]:
    """sections[i]의 하위 변경 하나를 적용하고 즉시 검증한다(007-A1-5): 적용 결과가 스키마를 깨면 그 변경만
    되돌리고(나머지 변경은 영향 없음) note를 남긴다."""
    before = data["sections"][i]
    sec = copy.deepcopy(before)
    if action == "delete" and idx is not None:
        if (reason := _delete_sub_item(sec, field_, idx)) is not None:
            return [f"{loc}: {reason}"]
    else:
        sec, notes = _apply_section_sub(sec, field_, idx, value)
        if notes:
            return [f"{loc}: {n}" for n in notes]
    data["sections"][i] = sec
    try:
        TopicPage.model_validate(data)
        return []
    except ValueError:
        data["sections"][i] = before
        return [f"{loc}: 적용하면 스키마가 깨져 이 변경만 되돌림"]


def apply_revision(prev: TopicPage, rev: TopicPageRevision, allowed: set[str]) -> tuple[TopicPage, int, list[str]]:
    """지적된 위치(최상위 칸 기준)만 합친다. 그 밖의 변경은 되돌림(세어 반환). 삭제는 뒤 번호부터."""
    data = prev.model_dump()
    reverts, notes, deletes, adds, sections_delete_n = 0, [], [], [], 0
    for ch in rev.changed:
        raw_loc = ch.loc if ch.action == "add" else normalize_loc(prev, ch.loc)
        loc = top_loc(raw_loc)
        # "Section 전체 add"(5.3): loc 자체가 그대로 sections[i]/head_tiles[i](하위 경로 없음)인 새 항목 추가만
        # 지적 없이도 허용. sections[i].<하위> 변경은 그 절(sections[i])이 지적됐을 때만 받는다
        is_whole_add = ch.action == "add" and raw_loc == loc and bool(re.fullmatch(r"(head_tiles|sections)\[\d+\]", loc))
        if loc not in allowed and not is_whole_add:
            reverts += 1
            notes.append(f"지적 안 된 위치 {ch.loc} 변경 되돌림")
            continue
        sub = _parse_sub(normalize_loc(prev, ch.loc))
        if sub is None and raw_loc != loc:  # v1.2 5.3: 문법 밖 하위 경로(sections[i].tiles 등)는 절 전체 delete로 새지 않게 버림
            notes.append(f"알 수 없는 위치 {ch.loc}")
            continue
        m = LOC.match(loc)
        if m and m.group(1):  # title / summary
            if ch.action == "edit" and isinstance(ch.value, str):
                data[m.group(1)] = ch.value
            continue
        if sub:  # sections[i].<하위>
            i, field_, idx = sub
            if i >= len(data["sections"]):
                notes.append(f"{ch.loc}: 위치 없음")
                continue
            notes += _apply_sub_change(data, i, field_, idx, ch.action, ch.value, ch.loc)
            continue
        if not m:
            notes.append(f"알 수 없는 위치 {ch.loc}")
            continue
        name, idx_s = m.group(2), int(m.group(3))
        if ch.action == "delete":
            if name == "sections" and len(data["sections"]) - sections_delete_n <= 1:
                notes.append("sections 전체 삭제는 받지 않음")
                continue
            sections_delete_n += name == "sections"
            deletes.append((name, idx_s))
            continue
        if not isinstance(ch.value, FIELD_TYPES[name]):
            notes.append(f"{ch.loc}: 값 형식이 {FIELD_TYPES[name].__name__}가 아님")
            continue
        val = ch.value
        if isinstance(val, Section):
            val = val.model_copy(update={"check": False})  # check는 코드 소유
        if ch.action == "edit" and idx_s < len(data[name]):
            data[name][idx_s] = val.model_dump()
        else:  # 007-A1-6/C1-1: add는 i 위치에 넣되, 다른 변경이 원래 번호를 쓰므로 insert는 맨 뒤로 미룬다
            adds.append((name, idx_s, val.model_dump()))
    for name, idx_s in sorted(deletes, key=lambda x: -x[1]):
        if idx_s < len(data[name]):
            data[name].pop(idx_s)
    for name, idx_s, dumped in sorted(adds, key=lambda x: x[1]):
        data[name].insert(min(idx_s, len(data[name])), dumped)
    try:
        return TopicPage.model_validate(data), reverts, notes
    except ValueError as e:
        return prev, reverts, [*notes, f"합친 판이 스키마에 맞지 않아 이 수정 버림: {str(e)[:100]}"]
