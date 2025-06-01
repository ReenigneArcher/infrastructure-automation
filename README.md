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
ansible-vault encrypt_string 'my_secret_value' --name 'my_secret_variable'
```

## Pre-requisites

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
