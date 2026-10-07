import json
import shutil

import pytest

from tests.conftest import FakeTransport, make_ctx, response
from trendsit.core import config
from trendsit.core.artifacts import RepoOnelinerInput
from trendsit.core.config import ROOT, ConfigError
from trendsit.core.role import DATA_RULE, RoleFailed, load_role, run_role

INPUT = RepoOnelinerInput(full_name="a/b", description="desc", topics=[], readme_head="# B\nA tool.")
GOOD = json.dumps({"basis": "A tool.", "oneliner": "테스트용 HTTP 클라이언트 라이브러리", "log": "README 근거", "attention": False},
                  ensure_ascii=False)


def test_loader_builds_prompt_and_hash(models):
    role = load_role("repo_oneliner", models)
    style = (ROOT / "skills/style_ko.md").read_text().strip()
    assert role.system_prompt.startswith(role.body)
    assert style in role.system_prompt
    assert role.system_prompt.endswith(DATA_RULE)
    assert len(role.prompt_hash) == 12 and int(role.prompt_hash, 16) >= 0
    assert load_role("repo_oneliner", models).prompt_hash == role.prompt_hash


def test_prompt_hash_changes_with_include(tmp_path, models):
    for d in ("roles", "skills"):
        shutil.copytree(ROOT / d, tmp_path / d)
    before = load_role("repo_oneliner", models, root=tmp_path).prompt_hash
    (tmp_path / "skills/style_ko.md").write_text("다른 지침")
    assert load_role("repo_oneliner", models, root=tmp_path).prompt_hash != before


@pytest.mark.parametrize("field,value,path", [
    ("output: RepoOneliner", "output: Nope", "output"),
    ("tools: []", "tools: [delete_everything]", "tools[0]"),
    ('task: "위 README로', 'tusk: "위 README로', "task"),
    ("  - 근거가 없으면 oneliner를", "  - 넷째 규칙\n  - 근거가 없으면 oneliner를", "core_rules"),
    ("max_tokens: 300", "max_tokens: -1", "max_tokens"),
    ("includes: [skills/style_ko.md]", "includes: [skills/none.md]", "includes[0]"),
])
def test_loader_rejects_bad_frontmatter(tmp_path, models, field, value, path):
    for d in ("roles", "skills"):
        shutil.copytree(ROOT / d, tmp_path / d)
    p = tmp_path / "roles/repo_oneliner.md"
    p.write_text(p.read_text().replace(field, value))
    with pytest.raises(ConfigError) as e:
        load_role("repo_oneliner", models, root=tmp_path)
    assert e.value.path == path




def test_run_role_retries_then_succeeds(tmp_path, models):
    t = FakeTransport([response("not json"), response(GOOD)])
    ctx = make_ctx(tmp_path, t)
    out = run_role(load_role("repo_oneliner", models), INPUT, ctx)
    assert out.oneliner.endswith("라이브러리")
    steps = ctx.db.steps_of(ctx.tracer.run_id)
    assert [s["error"] is not None for s in steps] == [True, False]
    assert "스키마 검증에 실패" in t.bodies[1]["messages"][-1]["content"]
    ok = steps[-1]
    assert ok["prompt_hash"] and ok["model"] and ok["tokens_in"] == 100 and ok["latency_ms"] is not None
    assert ok["text"] == "README 근거"


def test_run_role_too_long_output_is_retried(tmp_path, models):
    long = json.dumps({"basis": "A tool.", "oneliner": "가" * 61, "log": "x", "attention": False})
    t = FakeTransport([response(long), response(GOOD)])
    out = run_role(load_role("repo_oneliner", models), INPUT, make_ctx(tmp_path, t))
    assert len(out.oneliner) <= 60 and t.calls == 2


def test_run_role_gives_up_after_two_retries(tmp_path, models):
    t = FakeTransport([response("{}")] * 3)
    ctx = make_ctx(tmp_path, t)
    with pytest.raises(RoleFailed):
        run_role(load_role("repo_oneliner", models), INPUT, ctx)
    assert t.calls == 3
    assert all(s["error"] for s in ctx.db.steps_of(ctx.tracer.run_id))


def test_request_body_pins_provider_and_reasoning(tmp_path, models):
    t = FakeTransport([response(GOOD)])
    run_role(load_role("repo_oneliner", models), INPUT, make_ctx(tmp_path, t))
    body = t.bodies[0]
    assert body["model"] == models.models["generate"].id
    assert body["provider"]["allow_fallbacks"] is False and body["provider"]["order"] == ["deepinfra"]
    assert body["reasoning"] == {"enabled": False}
    assert body["usage"] == {"include": True}
    rf = body["response_format"]["json_schema"]
    assert rf["strict"] is True
    assert list(rf["schema"]["properties"]) == ["basis", "oneliner", "log", "attention"]
    assert rf["schema"]["additionalProperties"] is False
    assert body["messages"][1]["content"].startswith("<data>")
    assert '<document id="rp:a/b" source="GitHub README">' in body["messages"][1]["content"]


def test_unknown_config_alias_override(tmp_path, models):
    ctx = make_ctx(tmp_path, FakeTransport(), model="nope")
    with pytest.raises(Exception, match="없는 별칭"):
        run_role(load_role("repo_oneliner", models), INPUT, ctx)
    assert config.load("models.yaml")


def test_strict_schema_keeps_field_names_that_look_like_keywords():
    from pydantic import Field

    from trendsit.core.artifacts import RoleOutput
    from trendsit.core.llm import strict_json_schema

    class Card(RoleOutput):
        title: str = Field(max_length=10)
        format: str
        pattern: str | None = None

    s = strict_json_schema(Card)
    assert list(s["properties"]) == ["title", "format", "pattern", "log", "attention"]
    assert s["required"] == list(s["properties"])
    assert "maxLength" not in s["properties"]["title"] and "title" not in s["properties"]["title"]


def test_retry_message_states_length():
    from trendsit.core.artifacts import RepoOneliner
    from trendsit.core.llm import parse_json_output

    _, err = parse_json_output(json.dumps({"basis": "x" * 130, "oneliner": "a", "log": "l", "attention": False}),
                               RepoOneliner)
    assert "basis: 120자 이하여야 함(지금 130자)" in err
