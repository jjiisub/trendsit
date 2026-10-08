"""S3 설정(A3): deep.yaml 검증."""

import shutil

from tests.test_config import edit_yaml
from trendsit.core import config
from trendsit.core.config import ROOT


def copy_config(tmp_path):
    root = tmp_path / "root"
    shutil.copytree(ROOT / "config", root / "config")
    return root


def test_deep_yaml_passes_and_bad_values_point_to_path(tmp_path):
    assert config.check_all() == []
    d = config.load("deep.yaml")
    assert (d.default_text_depth, d.max_text_depth, d.plan_share) == (2, 3, 0.8)
    root = copy_config(tmp_path)
    edit_yaml(root / "config/deep.yaml", lambda x: x.__setitem__("max_text_depth", 5))
    assert [(e.file, e.path) for e in config.check_all(root / "config")] == [("deep.yaml", "max_text_depth")]
    root = copy_config(tmp_path / "b")
    edit_yaml(root / "config/deep.yaml", lambda x: x.__setitem__("default_text_depth", 3) or x.__setitem__("max_text_depth", 2))
    errs = config.check_all(root / "config")
    assert errs[0].file == "deep.yaml" and "default_text_depth" in errs[0].reason
