import json
from pathlib import Path

import pytest

from rail_compliance import cli
from rail_compliance.agent import ComplianceAgent
from rail_compliance.config import REPO_ROOT, Settings
from rail_compliance.factory import make_search_backend
from rail_compliance.llm import ConfigError
from rail_compliance.retry import LLMUnavailable
from rail_compliance.tools.search import CachingBackend, LiveBackend, ReplayBackend
from tests.fakes import ScriptedAgentLLM
from tests.test_agent import DONE, FakeExtractor, FakeSearch

EXAMPLE = REPO_ROOT / "examples" / "01_compliant_emu.json"


def fake_build(settings, **kwargs):
    # every parameter the example supplies ends with the model replying "done": needs_human
    script = [DONE] * 7
    return ComplianceAgent(ScriptedAgentLLM(script), FakeExtractor([]), FakeSearch())


def test_cli_writes_json_and_markdown_reports(tmp_path, capsys):
    code = cli.main(["check", str(EXAMPLE), "--out", str(tmp_path)], build=fake_build)
    assert code == 0
    report = json.loads((tmp_path / "01_compliant_emu.json").read_text("utf-8"))
    assert report["spec_name"].startswith("Regional EMU")
    md = (tmp_path / "01_compliant_emu.md").read_text("utf-8")
    assert md.startswith("# Compliance report")
    assert "Not legal advice" in md
    out = capsys.readouterr().out
    assert "wheelchair_spaces" in out
    assert "tool calls" in out


def test_cli_reports_an_invalid_spec_by_file_name(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text('{"name": "x"}', encoding="utf-8")
    assert cli.main(["check", str(bad), "--out", str(tmp_path)], build=fake_build) == 2
    assert "bad.json" in capsys.readouterr().out


@pytest.mark.parametrize("exc", [ConfigError("no key"), LLMUnavailable("quota")])
def test_cli_turns_expected_failures_into_exit_code_2(tmp_path, capsys, exc):
    def failing(settings, **kwargs):
        raise exc

    assert cli.main(["check", str(EXAMPLE), "--out", str(tmp_path)], build=failing) == 2
    assert str(exc) in capsys.readouterr().out


def test_relative_paths_in_settings_are_relative_to_the_repo():
    s = Settings(_env_file=None, rail_rag_data_dir="../rail-regulation-rag/data")
    assert s.rail_rag_data_dir.is_absolute()
    assert s.rail_rag_data_dir == (REPO_ROOT / "../rail-regulation-rag/data").resolve()
    assert Settings(_env_file=None, search_cache_dir=Path("/tmp/x")).search_cache_dir == Path(
        "/tmp/x"
    )


def test_live_backend_is_cached_by_default_and_plain_without_cache():
    s = Settings(_env_file=None, search_backend="live")
    assert isinstance(make_search_backend(s), CachingBackend)
    assert isinstance(make_search_backend(s, use_cache=False), LiveBackend)


def test_replay_needs_a_file(tmp_path):
    s = Settings(_env_file=None, search_backend="replay")
    with pytest.raises(ConfigError, match="--replay"):
        make_search_backend(s)
    recorded = tmp_path / "r.json"
    recorded.write_text("{}", encoding="utf-8")
    assert isinstance(make_search_backend(s, replay_file=recorded), ReplayBackend)


def test_the_default_request_rate_stays_under_the_free_tier_limit_of_15_a_minute():
    assert 0 < Settings(_env_file=None).llm_requests_per_minute <= 14
