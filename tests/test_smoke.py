import tomllib
from pathlib import Path

import rail_compliance

ROOT = Path(__file__).resolve().parents[1]


def test_version_matches_pyproject():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert rail_compliance.__version__ == project["version"]
