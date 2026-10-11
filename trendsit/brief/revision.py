"""작성자 수정(writer_revise) 결과를 이전 판에 합치기(v2 위치 문법, S6-1 5.3): 지적된 위치(최상위 칸 기준)만 합치고
그 밖의 변경은 되돌린다(write.py가 씀)."""

from __future__ import annotations

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
        else:
            notes.append(f"sections.paragraphs[{idx}]: 값 형식이 Para가 아님")
    elif field_ == "bars":
        if idx is None and (value is None or isinstance(value, BarGroup)):
            sec["bars"] = value.model_dump() if value else None
        elif idx is not None and isinstance(value, NumberItem) and sec.get("bars") and int(idx) < len(sec["bars"]["items"]):
            sec["bars"]["items"][int(idx)] = value.model_dump()
        else:
            notes.append("sections.bars: 값 형식이 맞지 않음")
    elif field_ == "table":
        if idx is None and (value is None or isinstance(value, Table)):
            sec["table"] = value.model_dump() if value else None
        elif idx is not None and isinstance(value, list) and sec.get("table"):
            rows = sec["table"]["rows"]
            if int(idx) < len(rows):
                rows[int(idx)] = value
            else:
                rows.append(value)
        else:
            notes.append("sections.table: 값 형식이 맞지 않음")
    elif field_ == "tiles":
        if idx is not None and isinstance(value, Tile):
            if int(idx) < len(sec["tiles"]):
                sec["tiles"][int(idx)] = value.model_dump()
            else:
                sec["tiles"].append(value.model_dump())
        else:
            notes.append("sections.tiles: 값 형식이 맞지 않음")
    elif field_ == "events":
        if idx is None and (value is None or isinstance(value, EventGroup)):
            sec["events"] = value.model_dump() if value else None
        elif idx is not None and isinstance(value, EventItem) and sec.get("events"):
            items = sec["events"]["items"]
            if int(idx) < len(items):
                items[int(idx)] = value.model_dump()
            else:
                items.append(value.model_dump())
        else:
            notes.append("sections.events: 값 형식이 맞지 않음")
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


def apply_revision(prev: TopicPage, rev: TopicPageRevision, allowed: set[str]) -> tuple[TopicPage, int, list[str]]:
    """지적된 위치(최상위 칸 기준)만 합친다. 그 밖의 변경은 되돌림(세어 반환). 삭제는 뒤 번호부터."""
    data = prev.model_dump()
    reverts, notes, deletes, sections_delete_n = 0, [], [], 0
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
            if ch.action == "delete" and idx is not None:
                if (reason := _delete_sub_item(data["sections"][i], field_, idx)) is not None:
                    notes.append(f"{ch.loc}: {reason}")
                continue
            data["sections"][i], sub_notes = _apply_section_sub(data["sections"][i], field_, idx, ch.value)
            notes += [f"{ch.loc}: {n}" for n in sub_notes]
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
        else:
            data[name].append(val.model_dump())
    for name, idx_s in sorted(deletes, key=lambda x: -x[1]):
        if idx_s < len(data[name]):
            data[name].pop(idx_s)
    try:
        return TopicPage.model_validate(data), reverts, notes
    except ValueError as e:
        return prev, reverts, [*notes, f"합친 판이 스키마에 맞지 않아 이 수정 버림: {str(e)[:100]}"]
