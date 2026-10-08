"""라벨 파일의 labeler 칸: make_labels가 보존하고, agreement가 누가 라벨을 달았는지(사람이 아니면 잠정) 알려 준다."""

from __future__ import annotations

import csv
import json

from eval import run_eval


def _setup(tmp_path, monkeypatch):
    role = "repo_oneliner"
    (tmp_path / "eval" / "fixtures" / role).mkdir(parents=True)
    (tmp_path / "eval" / "fixtures" / role / "a.json").write_text("{}", encoding="utf-8")
    rep_dir = tmp_path / "reports" / "eval"
    rep_dir.mkdir(parents=True)
    report = {"role": role, "spec": "S0", "model_alias": "generate", "at": "2026-10-08T00:00:00", "limit": None,
              "stopped": None, "summary": {"n": 1}, "path": "reports/eval/r.json",
              "results": [{"id": "a", "input": {"full_name": "x/y"}, "output": {"oneliner": "도구", "log": "", "attention": False},
                           "llm": {"verdicts": {"Q1": {"verdict": "pass"}, "Q2": {"verdict": "fail"}, "Q3": {"verdict": "pass"}}}}]}
    (rep_dir / "r.json").write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
    for name, value in (("FIXTURES", tmp_path / "eval" / "fixtures"), ("REPORTS", tmp_path / "reports"),
                        ("LABELS", tmp_path / "eval" / "labels"), ("ROOT", tmp_path)):
        monkeypatch.setattr(run_eval, name, value)
    return role


def test_labeler_kept_and_reported(tmp_path, monkeypatch):
    role = _setup(tmp_path, monkeypatch)
    path = run_eval.make_labels(role, "S0")
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    assert "labeler" in rows[0]
    rows[0] |= {"Q1_pass": "pass", "Q2_pass": "pass", "Q3_pass": "pass", "labeler": "opus-5.5"}
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    run_eval.make_labels(role, "S0")  # 다시 만들어도 출력이 같으면 라벨과 labeler 보존
    row = next(csv.DictReader(path.open(encoding="utf-8")))
    assert row["labeler"] == "opus-5.5" and row["Q1_pass"] == "pass"
    a = run_eval.agreement(role, "S0")
    assert a["labelers"] == ["opus-5.5"] and a["provisional"] is True
    assert a["questions"]["Q2"]["agree"] == 0 and a["total"]["agree"] == 2
