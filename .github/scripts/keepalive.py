"""Keep scheduled GitHub Actions workflows active without repository commits."""

import json
import os
from pathlib import Path
import subprocess

import yaml


def scheduled_workflows(root):
    """Discover scheduled workflow paths from the checked-out default branch."""
    paths = set()
    for path in sorted((root / ".github/workflows").iterdir()):
        if not path.is_file() or path.suffix not in {".yml", ".yaml"}:
            continue
        # BaseLoader preserves GitHub's `on` key instead of treating it as True.
        workflow = yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
        events = workflow.get("on", {}) if isinstance(workflow, dict) else {}
        if isinstance(events, dict) and events.get("schedule"):
            paths.add(path.relative_to(root).as_posix())
    return paths


def keepalive(root, repository):
    paths = scheduled_workflows(root)
    endpoint = f"repos/{repository}/actions/workflows"
    result = subprocess.run(
        ["gh", "api", "--paginate", "--slurp", f"{endpoint}?per_page=100"],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    for page in json.loads(result.stdout):
        for workflow in page["workflows"]:
            if workflow["path"] not in paths:
                continue
            # Preserve intentional disabling while recovering inactivity pauses.
            if workflow["state"] not in {"active", "disabled_inactivity"}:
                continue
            print(f"Keeping scheduled workflow active: {workflow['path']}", flush=True)
            subprocess.run(
                ["gh", "api", "--method", "PUT", f"{endpoint}/{workflow['id']}/enable"],
                check=True,
            )


if __name__ == "__main__":
    keepalive(Path(__file__).resolve().parents[2], os.environ["GITHUB_REPOSITORY"])
