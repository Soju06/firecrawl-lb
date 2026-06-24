from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.release_versions import assert_project_versions, update_project_versions


def _write_minimal_release_files(root: Path, version: str, uv_version: str | None = None) -> None:
    (root / "app").mkdir()
    (root / "frontend").mkdir()
    (root / "deploy" / "helm" / "firecrawl-lb").mkdir(parents=True)

    (root / "pyproject.toml").write_text(f'[project]\nname = "firecrawl-lb"\nversion = "{version}"\n', encoding="utf-8")
    (root / "app" / "__init__.py").write_text(f'__version__ = "{version}"\n', encoding="utf-8")
    (root / "frontend" / "package.json").write_text(
        json.dumps({"name": "firecrawl-lb-dashboard", "version": version}) + "\n",
        encoding="utf-8",
    )
    (root / "deploy" / "helm" / "firecrawl-lb" / "Chart.yaml").write_text(
        f"apiVersion: v2\nname: firecrawl-lb\nversion: {version}\nappVersion: {version}\n",
        encoding="utf-8",
    )
    (root / "uv.lock").write_text(
        f'[[package]]\nname = "firecrawl-lb"\nversion = "{uv_version or version}"\nsource = {{ editable = "." }}\n',
        encoding="utf-8",
    )


def test_assert_project_versions_accepts_pep440_normalized_uv_lock_for_beta(tmp_path: Path) -> None:
    _write_minimal_release_files(tmp_path, "1.20.0-beta.2", uv_version="1.20.0b2")

    assert_project_versions(tmp_path, "1.20.0-beta.2")


def test_update_project_versions_writes_uv_lock_pep440_prerelease(tmp_path: Path) -> None:
    _write_minimal_release_files(tmp_path, "1.19.0")

    update_project_versions(tmp_path, "1.20.0-beta.2")

    assert 'version = "1.20.0-beta.2"' in (tmp_path / "pyproject.toml").read_text(encoding="utf-8")
    assert '__version__ = "1.20.0-beta.2"' in (tmp_path / "app" / "__init__.py").read_text(encoding="utf-8")
    package_json = json.loads((tmp_path / "frontend" / "package.json").read_text(encoding="utf-8"))
    assert package_json["version"] == "1.20.0-beta.2"
    assert "version: 1.20.0-beta.2" in (tmp_path / "deploy" / "helm" / "firecrawl-lb" / "Chart.yaml").read_text(
        encoding="utf-8"
    )
    assert 'version = "1.20.0b2"' in (tmp_path / "uv.lock").read_text(encoding="utf-8")


def test_assert_project_versions_rejects_wrong_uv_lock_version(tmp_path: Path) -> None:
    _write_minimal_release_files(tmp_path, "1.20.0-beta.2", uv_version="1.20.0b1")

    with pytest.raises(ValueError, match="uv.lock='1.20.0b1'"):
        assert_project_versions(tmp_path, "1.20.0-beta.2")
