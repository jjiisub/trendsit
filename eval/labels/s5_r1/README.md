# S5 관문 B 1차 라벨(PR #9 리뷰, labeler opus-5.5, 잠정 D1-3)

- 대상: W40 run `20261009-200528-weekly-eafd`, W41 run `20261009-201517-weekly-2101`의 최종판(그 run의 토픽 페이지·판정)
- `judge_r1.json`: 같은 최종판의 judge 결과(Q1~Q4 + 원자 사실). 라벨과의 일치율 집계:
  `uv run python scripts/s5_gate_b.py --weeks x --agreement eval/labels/s5_r1/judge_r1.json` (라벨 파일은 이 폴더 것을 읽도록 `S5_LABELS=eval/labels/s5_r1`)
- 리뷰 반영 재실행 뒤 `eval/labels/*.csv`는 새 출력의 시트로 바뀐다. judge 채점표 보정(R5)은 이 폴더의 라벨로 잰다
