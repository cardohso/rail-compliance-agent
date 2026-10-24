"""Static checks of the Dockerfile and its workflow. They do NOT build the image: the docker
workflow does that on GitHub. They catch the mistakes that are cheap to make and costly to find."""

import re
import tomllib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = (ROOT / "Dockerfile").read_text(encoding="utf-8")
STAGES = re.split(r"(?m)^FROM ", DOCKERFILE)[1:]
RUNTIME = STAGES[-1]


def instructions(text):
    """Dockerfile instructions with line continuations joined."""
    joined = re.sub(r"\\\n\s*", " ", text)
    return [
        line.strip() for line in joined.splitlines() if line.strip() and not line.startswith("#")
    ]


def test_the_runtime_stage_runs_as_a_non_root_user_before_it_starts_anything():
    lines = instructions(RUNTIME)
    users = [i for i, line in enumerate(lines) if line.startswith("USER ")]
    assert users, "no USER in the runtime stage"
    assert lines[users[-1]].split()[1] not in {"root", "0"}
    cmd = next(i for i, line in enumerate(lines) if line.startswith("CMD "))
    assert users[-1] < cmd
    assert any("useradd" in line and "--uid 1000" in line for line in lines)


def test_there_is_a_healthcheck_that_needs_no_curl():
    health = [line for line in instructions(RUNTIME) if line.startswith("HEALTHCHECK")]
    assert health and "/health" in health[0] and "curl" not in health[0]


def test_no_secret_is_baked_into_the_image():
    for line in instructions(DOCKERFILE):
        assert not re.search(r"(?i)(api[_-]?key|token|password|secret)\s*=", line), line
    assert not re.search(r"(?m)^COPY\s+(--\S+\s+)*\.env", DOCKERFILE)
    ignore = (ROOT / ".dockerignore").read_text(encoding="utf-8").split()
    assert {".env", ".env.*", ".git", ".venv", "eval", "tests"} <= set(ignore)


def test_the_build_stage_copies_only_files_that_exist():
    for line in instructions(DOCKERFILE):
        if not line.startswith("COPY ") or "--from" in line:
            continue
        sources = [t for t in line.split()[1:-1] if not t.startswith("--")]
        for source in sources:
            assert (ROOT / source).exists(), f"{line}: {source} is not in the repo"


def test_the_runtime_image_does_not_carry_git_or_the_build_tools():
    assert "git" not in " ".join(instructions(RUNTIME)).replace("github", "")
    assert "apt-get" not in RUNTIME


def test_the_rail_assistant_commit_is_the_same_everywhere():
    """The `rail-rag` dependency, the corpus baked into the image and the corpus the eval
    workflow checks out must be one commit, or the index and the library disagree."""
    sources = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    pinned = sources["tool"]["uv"]["sources"]["rail-rag"]["rev"]
    in_dockerfile = re.search(r"ARG RAIL_RAG_REF=(\w+)", DOCKERFILE).group(1)
    workflow = yaml.safe_load((ROOT / ".github/workflows/eval.yml").read_text(encoding="utf-8"))
    in_eval = workflow["env"]["RAIL_RAG_REF"]
    assert pinned == in_dockerfile == in_eval
    assert len(pinned) == 40


def test_the_docker_workflow_probes_the_things_the_image_promises():
    workflow = (ROOT / ".github/workflows/docker.yml").read_text(encoding="utf-8")
    yaml.safe_load(workflow)
    for promise in (
        'id -u)" = "1000"',
        "Health.Status",
        "/health",
        "/check",
        "ready",
        "from_rail_rag",
    ):
        assert promise in workflow, promise
    assert "secrets." not in workflow  # a dummy key only; no real secret is used or pushed
