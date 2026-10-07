"""입력과 도구 결과를 user 메시지의 <data> 자료로 바꾼다.

- 문서형 칸(Document, list[Document])은 문서별 태그: <document id="rp:a/b" source="GitHub README">본문</document>
- 짧은 칸은 `이름: 값` 줄. 입력 전체를 JSON으로 덤프하지 않는다
- 자료 안의 `<`는 모두 `&lt;`로 바꾼다. 태그 이름 목록에 기대지 않으므로 </DATA>, </document > 같은 변형도 밖으로 못 나간다
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from .artifacts import Document


def escape(text: Any) -> str:
    return str(text).replace("<", "&lt;")


def _attr(value: Any) -> str:
    return escape(value).replace('"', "&quot;")


def render_document(doc: Document) -> str:
    attrs = [f'id="{_attr(doc.id)}"', f'source="{_attr(doc.source)}"']
    if doc.title:
        attrs.append(f'title="{_attr(doc.title)}"')
    if doc.url:
        attrs.append(f'url="{_attr(doc.url)}"')
    return f"<document {' '.join(attrs)}>\n{escape(doc.text)}\n</document>"


def _scalar(value: Any) -> str:
    if value is None or value == "" or value == []:
        return "(없음)"
    if isinstance(value, bool):
        return "true" if value else "false"
    return escape(value)


def _lines(name: str, value: Any) -> list[str]:
    if isinstance(value, Document):
        return [render_document(value)]
    if isinstance(value, list) and value and all(isinstance(v, Document) for v in value):
        return [render_document(v) for v in value]
    if isinstance(value, BaseModel):
        value = value.model_dump()
    if isinstance(value, dict):
        out: list[str] = []
        for k, v in value.items():
            out += _lines(f"{name}.{k}" if name else str(k), v)
        return out or [f"{name}: (없음)"]
    if isinstance(value, list) and value and all(isinstance(v, dict | BaseModel) for v in value):
        out = []
        for i, v in enumerate(value, 1):
            out += _lines(f"{name}[{i}]", v)
        return out
    if isinstance(value, list):
        return [f"{name}: {', '.join(_scalar(v) for v in value) if value else '(없음)'}"]
    text = _scalar(value)
    if "\n" in text:  # 여러 줄 값은 이름 줄 아래에 그대로
        return [f"{name}:", text]
    return [f"{name}: {text}"]


def render_body(obj: Any) -> str:
    """<data> 안쪽 내용."""
    if isinstance(obj, str):
        return escape(obj)
    if isinstance(obj, Document):
        return render_document(obj)
    if isinstance(obj, BaseModel):
        out: list[str] = []
        for name in type(obj).model_fields:
            out += _lines(name, getattr(obj, name))
        return "\n".join(out)
    return "\n".join(_lines("", obj))


def render_data(obj: Any) -> str:
    return f"<data>\n{render_body(obj)}\n</data>"
