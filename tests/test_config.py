import shutil
from pathlib import Path

import pytest
import yaml

from trendsit.core import config
from trendsit.core.config import ROOT, ConfigError
from trendsit.core.role import check_roles


def copy_root(tmp_path: Path) -> Path:
    for d in ("config", "roles", "skills"):
        shutil.copytree(ROOT / d, tmp_path / d)
    return tmp_path


def edit_yaml(path: Path, fn) -> None:
    data = yaml.safe_load(path.read_text())
    fn(data)
    path.write_text(yaml.safe_dump(data, allow_unicode=True))


def test_real_config_passes():
    assert config.check_all() == []
    assert check_roles(config.load("models.yaml")) == []


def test_reasoning_off_parses_as_disabled():
    models = config.load("models.yaml")
    assert models.models["generate"].reasoning is False
    assert models.models["judge"].reasoning.max_tokens == 800


def test_keyword_format_error_points_to_path(tmp_path):
    root = copy_root(tmp_path)
    edit_yaml(root / "config/keywords.yaml", lambda d: d["keywords"][3].__setitem__("aliases", "RAG"))
    errors = config.check_all(root / "config")
    assert [(e.file, e.path) for e in errors] == [("keywords.yaml", "keywords[3].aliases")]


def test_negative_budget_points_to_path(tmp_path):
    root = copy_root(tmp_path)
    edit_yaml(root / "config/budget.yaml", lambda d: d["specs"].__setitem__("S0", -1))
    errors = config.check_all(root / "config")
    assert len(errors) == 1
    assert errors[0].file == "budget.yaml" and errors[0].path == "specs"
    assert "S0" in errors[0].reason


def test_missing_required_alias(tmp_path):
    root = copy_root(tmp_path)
    edit_yaml(root / "config/models.yaml", lambda d: d["models"].pop("judge"))
    errors = config.check_all(root / "config")
    assert errors[0].file == "models.yaml" and "judge" in errors[0].reason


def test_role_with_unknown_alias_fails(tmp_path):
    root = copy_root(tmp_path)
    p = root / "roles/repo_oneliner.md"
    p.write_text(p.read_text().replace("model: generate", "model: genrate"))
    errors = check_roles(config.load("models.yaml", root / "config"), root)
    assert [(e.file, e.path) for e in errors] == [("roles/repo_oneliner.md", "model")]
    assert "genrate" in errors[0].reason


def test_load_raises_first_error(tmp_path):
    root = copy_root(tmp_path)
    edit_yaml(root / "config/sources.yaml", lambda d: d["text"][0].__setitem__("fetch", "rss"))
    with pytest.raises(ConfigError) as e:
        config.load("sources.yaml", root / "config")
    assert e.value.path == "text[0].fetch"


def test_yaml_syntax_error_reports_line(tmp_path):
    root = copy_root(tmp_path)
    (root / "config/budget.yaml").write_text("phase: mvp\nspecs: {S0: 0.15\n")
    errors = config.check_all(root / "config")
    assert errors[0].file == "budget.yaml" and "YAML" in errors[0].reason


def test_reasoning_effort_and_max_tokens_exclusive(tmp_path):
    root = copy_root(tmp_path)
    edit_yaml(root / "config/models.yaml",
              lambda d: d["models"]["judge"].__setitem__("reasoning", {"effort": "low", "max_tokens": 800}))
    errors = config.check_all(root / "config")
    assert errors[0].path == "models.judge.reasoning" and "하나만" in errors[0].reason
