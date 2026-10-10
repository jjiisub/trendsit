"""S4 채점: video_summary 코드 채점(셀 수 있는 것)과 관문 B 문턱값(S4_TASK 7장). graders.py 끝의 _load가 읽는다."""

from __future__ import annotations

import re
from typing import Any

from trendsit.core.artifacts_video import VideoSummary, same_spelling

from . import graders
from .graders import EVAL_ENDINGS, check, ends_as_sentence

NO_CONTENT = "내용 없음"
_VD = re.compile(r"^vd:(\d+)@(\d+)$")


def _norm(text: str) -> str:
    return " ".join(text.lower().split())


def code_video_summary(inp: dict[str, Any], out: dict[str, Any], expect: dict[str, Any]) -> list[dict[str, Any]]:
    """원래 출력(enforce 전) 기준. enforce가 고쳐 저장하더라도 모델이 규칙을 지켰는지를 잰다."""
    item, lo = inp["item_id"], inp["span_start"]
    hi = min(inp["span_end"], inp["duration_sec"])
    usable = inp["transcript_quality"] == "ok" and bool(inp["transcript"]["text"].strip())
    slide_ids = {d["id"] for d in inp["slides"]}
    transcript = _norm(inp["transcript"]["text"]) if usable else ""
    screens = [_norm(d["text"]) for d in inp["slides"]]

    def in_span(eid: str) -> bool:
        m = _VD.match(eid)
        return bool(m) and int(m.group(1)) == item and lo <= int(m.group(2)) <= hi

    points = out["key_points"]
    evidence = [e for kp in points for e in kp["evidence"]]
    bad_ev = [e for e in evidence if not in_span(e)]
    checks = [
        check("근거 id 형식과 구간", not bad_ev, ", ".join(bad_ev[:5])),
        # 근거 상한(MAX_EVIDENCE)은 enforce가 자르는 코드 소유 규칙(S5 P4-6). 넘친 건수는 모델 일치율(key_points)로 기록
        check("포인트마다 근거 1개 이상", all(len(kp["evidence"]) >= 1 for kp in points),
              str([len(kp["evidence"]) for kp in points])),
        check("타임라인 초가 구간 안", all(lo <= t["sec"] <= hi for t in out["timeline"]),
              str([t["sec"] for t in out["timeline"] if not lo <= t["sec"] <= hi])),
        check("포인트·타임라인 라벨 명사형",
              not [x for x in [kp["text"] for kp in points] + [t["label"] for t in out["timeline"]]
                   if ends_as_sentence(x)],
              "; ".join(x for x in [kp["text"] for kp in points] + [t["label"] for t in out["timeline"]]
                        if ends_as_sentence(x))[:120]),
        check("포인트·라벨 평가형 마무리 없음",
              not [x for x in [kp["text"] for kp in points] + [t["label"] for t in out["timeline"]]
                   if any(e in x for e in EVAL_ENDINGS)], ""),
        check("표기 쌍 양쪽 표기가 자료에 있고 서로 다름",
              all(_norm(p["spoken"]) in transcript and any(_norm(p["screen"]) in s for s in screens)
                  and not same_spelling(p["spoken"], p["screen"]) for p in out["name_pairs"]),
              str(out["name_pairs"])[:120]),
    ]
    if not usable:
        transcript_only = [e for e in evidence if e not in slide_ids]
        checks.append(check("전사 품질 미달이면 판독 근거만", not transcript_only, ", ".join(transcript_only[:5])))
        checks.append(check("전사 품질 미달이면 attention", out["attention"] is True, f"attention={out['attention']}"))
    if not usable and not inp["slides"]:
        checks.append(check("근거 없으면 내용 없음", out["summary"].strip() == NO_CONTENT and not points,
                            out["summary"][:60]))
    else:
        checks.append(check("요약은 ~다 문장", out["summary"].strip() == NO_CONTENT
                            or out["summary"].strip().rstrip(".").endswith("다"), out["summary"][-20:]))
    if usable:
        checks.append(check("포인트 3~6개", 3 <= len(points) <= 6, f"{len(points)}개"))
    return checks


graders.ROLE_CHECKS["video_summary"] = code_video_summary
# 문체(해요체, 평가형 마무리)는 요약 칸만. chapters와 name_pairs는 업로더·화면 표기를 그대로 옮긴 칸이고,
# 포인트·라벨은 위의 명사형·평가형 검사가 본다
graders.ROLE_STYLE_FIELDS["video_summary"] = ("summary",)
# 표기 쌍은 코드 소유 칸(S4 설계 결정 D2-1): 규칙(spoken은 전사에, screen은 판독에, 둘이 다름)이 문자열로 확정되므로
# 통과 판정은 enforce 후 값으로. 원래 출력 점수는 모델 품질로 따로 기록
graders.ENFORCED_FIELDS["video_summary"] = VideoSummary.ENFORCED_FIELDS
graders.THRESHOLDS["video_summary"] = {"questions": {"Q1": 0.8, "Q2": 0.8, "Q3": 0.8}, "code_pass_all": True}
