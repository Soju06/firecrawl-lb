from __future__ import annotations

import json
import re
import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

LEGACY_IDENTITY_RE = re.compile(r"choi138|kidjustinchoi|aaiyer|aaiyer0|justinchoi", re.IGNORECASE)
LEGACY_BRAND_RE = re.compile(
    r"codex-lb|codex_lb|CODEX_LB|ChatGPT|OpenAI|opencode|OpenCode|OpenClaw|"
    r"backend-api/codex|/backend-api|\.codex-lb|/var/lib/codex-lb|"
    r"ghcr\.io/soju06/codex-lb|charts/codex-lb",
    re.IGNORECASE,
)
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

TEXT_FILE_RE = re.compile(
    r"\.(py|toml|ya?ml|json|md|txt|sh|ts|tsx|js|jsx|css|html|dockerignore|gitignore)$|"
    r"(^|/)(Dockerfile.*|Makefile|LICENSE|AGENTS\.md)$"
)

SKIP_PATHS = {
    "uv.lock",  # package hashes and wheel URLs can contain denylist-looking digit sequences
    "frontend/bun.lock",
}

ALLOW_RESIDUE_PATHS = {
    "tests/unit/test_public_metadata_residue.py",  # this file contains the denylist fixtures themselves
}

ALLOW_EMAIL_PATHS = {
    "tests/unit/test_check_all_contributors.py",  # fixture-only email parsing tests
    "tests/unit/test_public_metadata_residue.py",  # this file contains the regex fixture itself
}


def _git_tracked_files() -> list[Path]:
    proc = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    return [ROOT / line for line in proc.stdout.splitlines()]


def _tracked_text_files() -> list[Path]:
    paths: list[Path] = []
    for path in _git_tracked_files():
        rel = path.relative_to(ROOT).as_posix()
        if not path.exists():
            continue
        if rel in SKIP_PATHS:
            continue
        if TEXT_FILE_RE.search(rel):
            paths.append(path)
    return paths


def test_tracked_files_do_not_contain_legacy_codex_lb_identity_or_brand_residue() -> None:
    findings: list[str] = []
    for path in _tracked_text_files():
        rel = path.relative_to(ROOT).as_posix()
        if rel in ALLOW_RESIDUE_PATHS:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for line_no, line in enumerate(text.splitlines(), start=1):
            if LEGACY_IDENTITY_RE.search(line) or LEGACY_BRAND_RE.search(line):
                findings.append(f"{rel}:{line_no}: {line.strip()}")

    assert findings == []


def test_public_package_metadata_has_only_firecrawl_lb_identity() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = pyproject["project"]

    assert project["name"] == "firecrawl-lb"
    assert project["authors"] == [{"name": "Soju06"}]
    assert project["maintainers"] == [{"name": "Soju06"}]
    assert "email" not in json.dumps(project["authors"] + project["maintainers"])

    chart = (ROOT / "deploy" / "helm" / "firecrawl-lb" / "Chart.yaml").read_text(encoding="utf-8")
    assert "maintainers:\n  - name: Soju06\n" in chart
    assert "email:" not in chart


def test_tracked_public_files_do_not_expose_personal_emails() -> None:
    findings: list[str] = []
    for path in _tracked_text_files():
        rel = path.relative_to(ROOT).as_posix()
        if rel in ALLOW_EMAIL_PATHS:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for line_no, line in enumerate(text.splitlines(), start=1):
            if EMAIL_RE.search(line):
                findings.append(f"{rel}:{line_no}: {line.strip()}")

    assert findings == []
