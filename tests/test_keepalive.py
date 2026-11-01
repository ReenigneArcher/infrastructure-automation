"""Check scheduled workflow discovery and API writes without contacting GitHub."""

import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch


REPOSITORY = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "keepalive", REPOSITORY / ".github/scripts/keepalive.py"
)
KEEPALIVE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(KEEPALIVE)
SCHEDULED = "on:\n  schedule:\n    - cron: '17 12 1 * *'\n"


class KeepaliveTest(unittest.TestCase):
    def run_keepalive(self, root, pages):
        response = subprocess.CompletedProcess([], 0, stdout=json.dumps(pages))
        with patch.object(KEEPALIVE.subprocess, "run", return_value=response) as run:
            KEEPALIVE.keepalive(root, "owner/repository")
        self.assertIn("--paginate", run.call_args_list[0].args[0])
        self.assertIn("--slurp", run.call_args_list[0].args[0])
        return [call.args[0][-1] for call in run.call_args_list[1:]]

    def workflow(self, workflow_id, filename, state="active"):
        return {
            "id": workflow_id,
            "path": f".github/workflows/{filename}",
            "state": state,
        }

    def test_current_scheduled_workflows_are_renewed_but_ci_is_skipped(self):
        page = {
            "workflows": [
                self.workflow(1, "daily.yml"),
                self.workflow(2, "keepalive.yml"),
                self.workflow(3, "ci.yml"),
            ]
        }
        self.assertEqual(
            self.run_keepalive(REPOSITORY, [page]),
            [
                "repos/owner/repository/actions/workflows/1/enable",
                "repos/owner/repository/actions/workflows/2/enable",
            ],
        )

    def test_future_workflows_are_discovered_across_pages_and_yaml_extensions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workflows = root / ".github/workflows"
            workflows.mkdir(parents=True)
            (workflows / "future.yml").write_text(SCHEDULED)
            (workflows / "future.yaml").write_text(
                "'on': {schedule: [{cron: '0 0 * * 1'}]}\n"
            )
            self.assertEqual(
                self.run_keepalive(
                    root,
                    [
                        {"workflows": [self.workflow(4, "future.yml")]},
                        {"workflows": [self.workflow(5, "future.yaml")]},
                    ],
                ),
                [
                    "repos/owner/repository/actions/workflows/4/enable",
                    "repos/owner/repository/actions/workflows/5/enable",
                ],
            )

    def test_only_inactivity_disabling_is_reversed(self):
        states = ["active", "disabled_inactivity", "disabled_manually", "deleted", "disabled_fork"]
        page = {
            "workflows": [
                self.workflow(index, "daily.yml", state)
                for index, state in enumerate(states)
            ]
        }
        self.assertEqual(
            self.run_keepalive(REPOSITORY, [page]),
            [
                "repos/owner/repository/actions/workflows/0/enable",
                "repos/owner/repository/actions/workflows/1/enable",
            ],
        )

    def test_comments_job_names_and_other_events_do_not_count_as_schedules(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workflows = root / ".github/workflows"
            workflows.mkdir(parents=True)
            fixtures = {
                "comment.yml": "# on: {schedule: [{cron: '0 0 * * *'}]}\non: push\n",
                "job.yml": "on: workflow_dispatch\njobs:\n  schedule: {}\n",
                "events.yaml": "on: [push, pull_request]\n",
                "empty.yml": "# No workflow\n",
                "notes.txt": SCHEDULED,
            }
            for filename, content in fixtures.items():
                (workflows / filename).write_text(content)
            page = {
                "workflows": [
                    self.workflow(index, filename)
                    for index, filename in enumerate([*fixtures, "missing.yml"])
                ]
            }
            self.assertEqual(self.run_keepalive(root, [page]), [])

    def test_api_listing_failure_is_not_silently_ignored(self):
        error = subprocess.CalledProcessError(1, ["gh", "api"])
        with patch.object(KEEPALIVE.subprocess, "run", side_effect=error) as run:
            with self.assertRaises(subprocess.CalledProcessError):
                KEEPALIVE.keepalive(REPOSITORY, "owner/repository")
        self.assertEqual(run.call_count, 1)

    def test_enable_failure_fails_the_job(self):
        response = subprocess.CompletedProcess(
            [], 0, stdout=json.dumps([{"workflows": [self.workflow(1, "daily.yml")]}])
        )
        error = subprocess.CalledProcessError(1, ["gh", "api", "--method", "PUT"])
        with patch.object(KEEPALIVE.subprocess, "run", side_effect=[response, error]) as run:
            with self.assertRaises(subprocess.CalledProcessError):
                KEEPALIVE.keepalive(REPOSITORY, "owner/repository")
        self.assertEqual(run.call_args.args[0][-3:-1], ["--method", "PUT"])
        self.assertTrue(run.call_args.kwargs["check"])


if __name__ == "__main__":
    unittest.main()
