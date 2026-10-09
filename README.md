# Infrastructure Automation using Ansible

This repository contains Ansible playbooks for automating MY homelab infrastructure.

## Features

- [ ] Disks
  - [x] Alert when disks are above 80% full
  - [x] Alert when disks are failing SMART tests
  - [ ] Try to correct when disks have errors
- [ ] Network
  - [ ] Alert when web services are down
  - [ ] Restart web services when they are down
- [ ] Backup
- [ ] Docker
  - [ ] Alert when Docker containers are down
  - [ ] Restart Docker containers when they are down
- [ ] Proxmox
  - [ ] Check VM health
- [ ] General
  - [ ] Keep packages up to date
  - [ ] Alert when packages are out of date
  - [ ] Alert when hosts are not reachable

## Inventory

The inventory is a submodule of a private repository, for security purposes. The structure of the inventory submodule
should look something like this:

```
inventory/
├── group_vars
│   └── all.yml
├── host_vars
│   ├── host1.yml
│   └── host2.yml
├── android.yml
├── linux.yml
├── macos.yml
└── windows.yml
```

The `group_vars/all.yml` should look something like the following:

```yaml
ansible_user: ansible
ansible_password: !vault |
  $ANSIBLE_VAULT;1.1;AES256 
  1234...6789
discord_webhook_url: !vault |
  $ANSIBLE_VAULT;1.1;AES256 
  1234...6789
```

`ansible_user` and `ansible_password` are the credentials used to connect to the hosts.

You could also put the variables inside other group_vars files, or in the host_vars files, depending on your needs.

If a variable is defined at multiple levels, ansible will use the most specific one.

## Secrets

Secrets are encrypting using Ansible Vault with a vault password file, which should be stored at `./vault-password`
when developing locally. The password should be saved to a GitHub secret named `ANSIBLE_VAULT_PASSWORD`
when running the playbooks in GitHub Actions. Be sure the local and GitHub secrets are the same otherwise the
decryption will fail.

Below is an example of creating a secret:

```bash
uv run --locked --no-build --no-sync ansible-vault encrypt_string 'my_secret_value' --name 'my_secret_variable'
```

## Pre-requisites

### Python Environment

Python dependencies are declared in `pyproject.toml` and pinned in `uv.lock`. Install
[uv](https://docs.astral.sh/uv/getting-started/installation/), then set up the environment from the repository root:

```bash
uv sync --locked --no-build
uv run --locked --no-build --no-sync ansible-galaxy collection install -r requirements.yml
```

The project uses Python 3.14 and Ansible core 2.20. Managed Linux and macOS hosts need Python 3.9 or newer.
Ansible requires Linux or macOS as its controller; on Windows, use WSL or the provided Dockerfile.
The default sync includes the Ansible and YAML linters in the `dev` dependency group;
add `--no-dev` for an environment containing only runtime dependencies.

The Dockerfile uses the official `ghcr.io/astral-sh/uv` image with Python 3.14 and installs from the same lockfile.
Its virtual environment lives outside `/app` so mounting the checkout does not hide installed dependencies.

On a Linux or macOS host, run Ansible commands through the locked environment:

```bash
uv run --locked --no-build --no-sync ansible-playbook playbooks/common/daily/disk_space.yml
uv run --locked --no-build --no-sync ansible-vault encrypt_string 'my_secret_value' --name 'my_secret_variable'
```

Inside the container, the virtual environment is already on `PATH`, so Ansible commands work directly
without activating the environment or adding `uv run`:

```bash
ansible-playbook playbooks/common/daily/disk_space.yml
ansible-vault encrypt_string 'my_secret_value' --name 'my_secret_variable'
```

After changing Python dependencies, run `uv lock` and commit both `pyproject.toml` and `uv.lock`.
Ansible Galaxy collections remain declared in `requirements.yml` and are installed separately.

### Windows Clients

You must install OpenSSH Server available through optional features in Windows settings. After installation run the
following commands in PowerShell as Administrator.

```powershell
Start-Service sshd
Set-Service -Name sshd -StartupType 'Automatic'
Start-Service ssh-agent
Set-Service -Name ssh-agent -StartupType 'Automatic'
```

Verify the SSH server is running by checking the listening port:

```powershell
netstat -nao | find /i '":22"'
```

## Workflows

There are GitHub workflows that run the playbooks on a schedule, and they connect to the homelab network via
OpenVPN.

CI follows the shared LizardByte workflow pattern: SHA-pinned Python and uv setup actions, a cached
`uv sync --locked --no-build` installation, and `uv run --locked --no-build --no-sync` commands. It also builds
the Docker image, checks an Ansible connection to localhost, and validates playbook syntax using a temporary
inventory.

The keepalive workflow runs on the first day of each month at 12:17 UTC and can also be run manually. It updates
`.github/keepalive.txt` and commits the timestamp to the default branch using `GITHUB_TOKEN` to keep scheduled
workflows active during periods without other repository activity. The default branch must allow these bot commits.
