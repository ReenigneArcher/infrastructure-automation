"""Exercise schedule discovery using the composite action's actual shell script."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest

import yaml


REPOSITORY = Path(__file__).resolve().parents[1]
SETUP_PLAYBOOKS = [
    "./playbooks/windows/setup/ssh_default_shell.yml",
    "./playbooks/linux/setup/packages.yml",
    "./playbooks/common/setup/security/ssh.yml",
]


class AnsibleScheduleTest(unittest.TestCase):
    def discover_playbooks(self, schedule, filenames=None):
        action = yaml.safe_load(
            (REPOSITORY / ".github/actions/ansible/action.yml").read_text()
        )
        discovery = next(
            step["run"]
            for step in action["runs"]["steps"]
            if step.get("id") == "find-playbooks"
        )
        script = discovery.replace("${{ inputs.schedule_type }}", schedule)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            if filenames is None:
                filenames = [
                    "playbooks/common/daily/disk_space.yml",
                    "playbooks/common/daily/disk_health.yml",
                    "playbooks/common/weekly/packages.yml",
                    "playbooks/common/setup/README.md",
                    "playbooks/linux/setup_notes/packages.yml",
                    *SETUP_PLAYBOOKS,
                ]
            (root / "playbooks").mkdir()
            for filename in filenames:
                path = root / filename
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
            output = root / "github-output"
            subprocess.run(
                ["bash", "-e", "-o", "pipefail", "-c", script],
                cwd=root,
                env={**os.environ, "GITHUB_OUTPUT": str(output)},
                capture_output=True,
                text=True,
                check=True,
            )
            lines = output.read_text().splitlines()
            return [line for line in lines[1:-1] if line]

    def test_daily_runs_all_setup_playbooks_before_scheduled_playbooks(self):
        self.assertEqual(
            self.discover_playbooks("daily"),
            sorted(SETUP_PLAYBOOKS)
            + [
                "./playbooks/common/daily/disk_health.yml",
                "./playbooks/common/daily/disk_space.yml",
            ],
        )

    def test_weekly_runs_setup_and_only_its_scheduled_playbooks(self):
        self.assertEqual(
            self.discover_playbooks("weekly"),
            sorted(SETUP_PLAYBOOKS)
            + ["./playbooks/common/weekly/packages.yml"],
        )

    def test_schedule_without_matching_playbooks_still_runs_setup(self):
        self.assertEqual(
            self.discover_playbooks("monthly"), sorted(SETUP_PLAYBOOKS)
        )

    def test_setup_schedule_does_not_duplicate_setup_playbooks(self):
        self.assertEqual(
            self.discover_playbooks("setup"), sorted(SETUP_PLAYBOOKS)
        )

    def test_setup_nested_in_schedule_runs_only_once_and_first(self):
        setup = "./playbooks/common/daily/setup/ssh.yml"
        scheduled = "./playbooks/common/daily/disks.yml"
        self.assertEqual(
            self.discover_playbooks("daily", [scheduled, setup]),
            [setup, scheduled],
        )

    def test_schedule_without_setup_runs_matching_playbooks(self):
        scheduled = "./playbooks/common/weekly/packages.yml"
        self.assertEqual(
            self.discover_playbooks("weekly", [scheduled]), [scheduled]
        )

    def test_repository_without_playbooks_stays_empty(self):
        self.assertEqual(self.discover_playbooks("monthly", []), [])


if __name__ == "__main__":
    unittest.main()
