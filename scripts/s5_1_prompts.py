"""프롬프트 스냅숏(S5-1a 5.1): 역할마다 system 문자열, 출력 스키마, 픽스처 입력별 초기 메시지의 sha256.

실행: uv run python scripts/s5_1_prompts.py [--out <path>] [--diff <before.json>]
--diff는 지금 값과 비교해 첫 차이를 출력한다(같으면 종료 코드 0, 다르면 1). LLM 호출 없음.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from trendsit.core import config  # noqa: E402
from trendsit.core.role import initial_messages, load_role, role_files  # noqa: E402


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def snapshot() -> dict[str, Any]:
    models = config.load("models.yaml")
    out: dict[str, Any] = {}
    for path in role_files(ROOT):
        role = load_role(path, models, ROOT)
        fixtures = {}
        for fx in sorted((ROOT / "eval" / "fixtures" / path.stem).glob("*.json")):
            try:
                inp = role.input_cls.model_validate(json.loads(fx.read_text(encoding="utf-8"))["input"])
            except ValidationError:
                fixtures[fx.name] = "invalid"
                continue
            fixtures[fx.name] = sha(json.dumps(initial_messages(role, inp), ensure_ascii=False, sort_keys=True))
        schema = json.dumps(role.output_cls.model_json_schema(), ensure_ascii=False, sort_keys=True)
        out[path.stem] = {"system": sha(role.system_prompt), "schema": sha(schema), "fixtures": fixtures}
    return out


def first_diff(a: Any, b: Any, path: str = "") -> str | None:
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(a.keys() | b.keys()):
            if k not in a or k not in b:
                return f"{path}/{k}: {'전에만 있음' if k in a else '지금만 있음'}"
            if (d := first_diff(a[k], b[k], f"{path}/{k}")) is not None:
                return d
        return None
    return None if a == b else f"{path}: {a} → {b}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    ap.add_argument("--diff")
    args = ap.parse_args()
    snap = snapshot()
    text = json.dumps(snap, ensure_ascii=False, sort_keys=True, indent=1) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    if args.diff:
        d = first_diff(json.loads(Path(args.diff).read_text(encoding="utf-8")), snap)
        if d is not None:
            print(f"프롬프트 차이: {d}", file=sys.stderr)
            return 1
    elif not args.out:
        print(text, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
