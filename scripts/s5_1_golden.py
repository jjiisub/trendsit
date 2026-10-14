"""골든 회귀(S6-1 5.11 B1, D-31): v2 픽스처(tests/fixtures/s6_1/topic_v2.json)에 코드 검사(checks.py)를 다시
돌려 JSON으로 남긴다. 실DB·LLM·임베딩 호출 없음. 이후 스펙은 이 결과가 reports/S6-1/golden.json과 완전히
같은지로 회귀를 잰다(옛 실DB 전후 비교 방식은 D-31로 폐기).

실행: uv run python scripts/s5_1_golden.py --out <path> [--fixture tests/fixtures/s6_1/topic_v2.json] [--golden <golden.json>]
종료 코드: 0 성공(또는 --golden과 일치), 1 --golden과 다름.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from trendsit.brief import checks  # noqa: E402
from trendsit.brief.evidence import EvidenceItem  # noqa: E402
from trendsit.core import config  # noqa: E402
from trendsit.core.artifacts_brief import TopicPage  # noqa: E402

DEFAULT_FIXTURE = ROOT / "tests" / "fixtures" / "s6_1" / "topic_v2.json"


def run(fixture: Path) -> list[dict]:
    cfg = config.load("brief.yaml")
    entries = json.loads(fixture.read_text(encoding="utf-8"))
    pages = []
    for e in entries:
        page = TopicPage.model_validate(e["page"])
        pack = {k: [EvidenceItem(**it) for it in v] for k, v in e["pack"].items()}
        n_sources = e["n_sources"]
        cr = checks.run_checks(page, pack, n_sources, cfg, {}, e.get("slide_candidates", []), set(e.get("timeline_secs", [])))
        pages.append({
            "topic_id": e["topic_id"],
            "issues": [{"loc": i.loc, "type": i.type, "comment": i.comment} for i in cr.issues],
            "autofix": [{"loc": f["loc"], "rule": f["rule"]} for f in cr.autofix],
            "warnings": cr.warnings})
    return pages


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--fixture", default=str(DEFAULT_FIXTURE))
    ap.add_argument("--golden")
    args = ap.parse_args()
    pages = run(Path(args.fixture))
    text = json.dumps({"pages": pages}, ensure_ascii=False, sort_keys=True, indent=1) + "\n"
    Path(args.out).write_text(text, encoding="utf-8")
    if args.golden:
        golden = Path(args.golden).read_text(encoding="utf-8")
        if text != golden:
            print("golden.json과 다름(코드 검사 결과가 바뀜)", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
