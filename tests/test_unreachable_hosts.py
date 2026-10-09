"""Check offline-host handling with real Ansible execution and local fixtures."""

import os
from pathlib import Path
import socket
import subprocess
import tempfile
import unittest

import yaml


REPOSITORY = Path(__file__).resolve().parents[1]
SSH_SETUP = REPOSITORY / "playbooks/windows/setup/ssh_default_shell.yml"


class UnreachableHostsTest(unittest.TestCase):
    def test_all_plays_ignore_unreachable_hosts(self):
        for path in sorted((REPOSITORY / "playbooks").rglob("*.yml")):
            for play in yaml.safe_load(path.read_text()):
                if "import_playbook" in play:
                    continue
                with self.subTest(playbook=str(path), play=play.get("name")):
                    self.assertIs(play.get("ignore_unreachable"), True)

    def run_setup(self, *, reachable=False, execution_fails=False):
        with tempfile.TemporaryDirectory() as directory, socket.socket() as port:
            root = Path(directory)
            # Reserving an unlistened local port makes SSH fail immediately.
            port.bind(("127.0.0.1", 0))
            hosts = {
                "offline": {
                    "ansible_connection": "ssh",
                    "ansible_shell_type": "powershell",
                    "ansible_host": "127.0.0.1",
                    "ansible_port": port.getsockname()[1],
                    "ansible_ssh_args": "-o ConnectTimeout=1 -o ConnectionAttempts=1",
                }
            }
            if reachable:
                hosts["reachable"] = {
                    "ansible_connection": "local",
                    "ansible_shell_type": "sh",
                }
            inventory = root / "inventory.yml"
            inventory.write_text(yaml.safe_dump({"windows": {"hosts": hosts}}))
            config = root / "ansible.cfg"
            config.write_text("[defaults]\nhost_key_checking=False\nnocows=True\n")

            # Preserve the playbook's control flow while replacing Windows-only
            # registry writes and verification with assertions on the controller.
            plays = yaml.safe_load(SSH_SETUP.read_text())
            for task in plays[0]["tasks"]:
                if "ansible.windows.win_regedit" in task:
                    del task["ansible.windows.win_regedit"]
                    task["ansible.builtin.assert"] = {
                        "that": ["ansible_shell_type == 'cmd'"],
                        "success_msg": "Registry step reached",
                    }
                if "ansible.windows.win_ping" in task:
                    del task["ansible.windows.win_ping"]
                    task["ansible.builtin.assert"] = {
                        "that": ["ansible_shell_type == 'powershell'"],
                        "success_msg": "Windows verification reached",
                    }
            playbook = root / "setup.yml"
            playbook.write_text(yaml.safe_dump(plays, sort_keys=False))

            binaries = root / "bin"
            binaries.mkdir()
            powershell = binaries / "powershell.exe"
            powershell.write_text(
                "#!/bin/sh\nexit 1\n"
                if execution_fails
                else "#!/bin/sh\n"
                "printf '%s\\n' '{\"shell_type\":\"cmd\","
                "\"powershell_path\":\"powershell.exe\"}'\n"
            )
            powershell.chmod(0o755)
            return subprocess.run(
                ["ansible-playbook", "-i", str(inventory), str(playbook)],
                cwd=root,
                env={
                    **os.environ,
                    "ANSIBLE_CONFIG": str(config),
                    "ANSIBLE_FORCE_COLOR": "false",
                    "ANSIBLE_NO_LOG": "false",
                    "PATH": str(binaries) + os.pathsep + os.environ["PATH"],
                },
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )

    def test_offline_host_exits_successfully_without_parsing_probe_output(self):
        result = self.run_setup()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertRegex(result.stdout, r"offline\s+.*ignored=1")
        self.assertNotIn("TASK [Match the connection", result.stdout)

    def test_offline_host_does_not_prevent_reachable_host_setup(self):
        result = self.run_setup(reachable=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Windows verification reached", result.stdout)
        self.assertRegex(result.stdout, r"offline\s+.*failed=0.*ignored=1")
        self.assertRegex(result.stdout, r"reachable\s+.*failed=0.*ignored=0")

    def test_execution_failures_still_fail_the_playbook(self):
        result = self.run_setup(reachable=True, execution_fails=True)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertRegex(result.stdout, r"reachable\s+.*failed=1")


if __name__ == "__main__":
    unittest.main()
