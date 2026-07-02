from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

RELEASE_PR_WORKFLOWS = [
    ROOT / ".github" / "workflows" / "release-please.yml",
    ROOT / ".github" / "workflows" / "prepare-beta-release.yml",
]


def test_release_pr_workflows_fail_closed_when_token_is_missing() -> None:
    for workflow in RELEASE_PR_WORKFLOWS:
        text = workflow.read_text(encoding="utf-8")
        assert "RELEASE_PLEASE_TOKEN is required" in text, workflow
        assert "exit 1" in text, workflow
        assert "release-please is a no-op" not in text, workflow
        assert "beta release PR sync is a no-op" not in text, workflow
