# SSH & Networking Guide

This document explains how the Media Sync Tool authenticates to your LAN targets (Forge/Comfy) and ephemeral cloud VMs (VastAI), how host keys are trusted, how permissions are handled on a QNAP NAS, and what to check when things don’t connect.

---

## 1) Network Topology & Ports

- **NAS (QNAP)** runs the Docker container that hosts the API.
- **Forge** and **ComfyUI** run on the same LAN host `10.0.78.108` but with **custom SSH ports**:
  - Forge: `2222`
  - ComfyUI: `2223`
- **VastAI** instances are **ephemeral**, with changing public IPs and default SSH port `22` (user typically `ubuntu` or `root` depending on image).

> The container connects **outbound** to these targets via SSH+rsync. Ensure the NAS can reach those ports.

---

## 2) Project-local SSH (No system `~/.ssh`)

To keep secrets out of system homes and avoid QNAP permission quirks, SSH material lives in your repo:

```
vast_api/
  .ssh/
    id_ed25519          # private key (secret)
    id_ed25519.pub      # public key
    config              # SSH host aliases
    known_hosts         # LAN host keys (static; RO in container)
    vast_known_hosts    # Cloud host keys (dynamic; RW in container)
```

Why this layout?

- Reproducible, **self-contained** config tied to the project.
- Easy to mount keys **read-only** in the container.
- Separate, **writable** host-key cache for ephemeral cloud hosts.

---

## 3) Permissions (QNAP-friendly, SSH-approved)

These are crucial; SSH will refuse “too open” files.

```bash
# Directory listable by group so SMB user can see non-secrets
chmod 750 .ssh

# Private key is owner-only
chmod 600 .ssh/id_ed25519

# Public/non-secret files are readable
chmod 644 .ssh/id_ed25519.pub .ssh/known_hosts .ssh/config

# VastAI hostkey cache is writable (container appends keys)
chmod 664 .ssh/vast_known_hosts
```

**QNAP notes**
- POSIX ACLs may be **disabled** on your share (so `setfacl` fails). Use **Unix groups** instead.
- Most SMB users are in group **`everyone`**; you can `chgrp everyone` to make non-secrets visible via SMB.
- Never `777` anything under `.ssh`. SSH will reject it.

---

## 4) Docker mounts (RO keys, RW hostkey cache)

`docker-compose.yml`:

```yaml
services:
  media-sync-api:
    build: .
    container_name: media-sync-api
    ports: ["5000:5000"]
    volumes:
      # SSH (project-local)
      - ./.ssh/id_ed25519:/root/.ssh/id_ed25519:ro
      - ./.ssh/id_ed25519.pub:/root/.ssh/id_ed25519.pub:ro
      - ./.ssh/known_hosts:/root/.ssh/known_hosts:ro
      - ./.ssh/config:/root/.ssh/config:ro
      - ./.ssh/vast_known_hosts:/root/.ssh/vast_known_hosts    # RW

      # QNAP media share
      - /share/sd/SecretFolder:/media

      # VastAI API key
      - ./api_key.txt:/app/api_key.txt:ro

    environment:
      - PYTHONUNBUFFERED=1
      - PUID=0
      - PGID=0

    restart: unless-stopped
```

- Keys & static trust data are **read-only**.
- `vast_known_hosts` is **writable** so the app can append new cloud host keys safely.
- `/share/sd/SecretFolder` is mounted to **`/media`** for your sync jobs (using `PUID=0`, `PGID=0` so the container can read/write there).

---

## 5) SSH config (aliases + trust policy)

`.ssh/config`:

```
# Forge (LAN)
Host forge
  HostName 10.0.78.108
  Port 2222
  User root
  IdentityFile /root/.ssh/id_ed25519
  IdentitiesOnly yes
  UserKnownHostsFile /root/.ssh/known_hosts
  StrictHostKeyChecking yes

# ComfyUI (LAN)
Host comfy
  HostName 10.0.78.108
  Port 2223
  User root
  IdentityFile /root/.ssh/id_ed25519
  IdentitiesOnly yes
  UserKnownHostsFile /root/.ssh/known_hosts
  StrictHostKeyChecking yes

# VastAI (cloud, ephemeral)
Host vast-*
  User ubuntu
  IdentityFile /root/.ssh/id_ed25519
  IdentitiesOnly yes
  UserKnownHostsFile /root/.ssh/vast_known_hosts
  StrictHostKeyChecking accept-new
```

**Why two hostkey files?**
- LAN hosts are **stable** → we pre-seed `known_hosts` once and enforce `StrictHostKeyChecking yes`.
- Cloud hosts change often → we store their keys in `vast_known_hosts` and use `accept-new` so first connect appends the key automatically (still prevents MITM after first trust).

---

## 6) First-time trust (host keys)

**LAN (one-time on host)**
```bash
ssh-keyscan -p 2222 10.0.78.108 >> .ssh/known_hosts   # Forge
ssh-keyscan -p 2223 10.0.78.108 >> .ssh/known_hosts   # ComfyUI
```

**Cloud (on each new instance)**
- Either rely on `StrictHostKeyChecking accept-new` (SSH will append on first connect), **or**
- Pre-seed explicitly:
  ```bash
  ssh-keyscan -p 22 "$VAST_IP" >> .ssh/vast_known_hosts
  ```

---

## 7) Passwordless auth (copy your public key once)

```bash
# Forge
ssh-copy-id -i .ssh/id_ed25519.pub "-p 2222 root@10.0.78.108"

# ComfyUI
ssh-copy-id -i .ssh/id_ed25519.pub "-p 2223 root@10.0.78.108"

# VastAI (after it boots and you know IP/user)
ssh-copy-id -i .ssh/id_ed25519.pub "ubuntu@$VAST_IP"
```

> Best practice for VastAI is to **inject the public key at instance creation** when possible.

---

## 8) Sanity tests

**From the host (NAS):**
```bash
# Should print ok without prompting (after ssh-copy-id)
ssh -i .ssh/id_ed25519 -p 2222 root@10.0.78.108 echo forge-ok
ssh -i .ssh/id_ed25519 -p 2223 root@10.0.78.108 echo comfy-ok
```

**From the container:**
```bash
docker compose up -d --build
docker compose exec media-sync-api ssh -F /root/.ssh/config forge  echo ok
docker compose exec media-sync-api ssh -F /root/.ssh/config comfy  echo ok
# Cloud (replace):
docker compose exec media-sync-api ssh -F /root/.ssh/config vast-$VAST_IP echo ok
```

---

## 9) Common pitfalls & fixes

- **“Permission denied (publickey)”**
  - Public key not installed on target → re-run `ssh-copy-id`.
  - Wrong user (`root` vs `ubuntu`) → match the target’s default user.
  - Private key perms wrong → ensure `chmod 600 .ssh/id_ed25519`.

- **“The authenticity of host can’t be established…”**
  - `known_hosts` missing → run `ssh-keyscan` (LAN) or use `accept-new` (cloud).
  - For container, ensure your mounts match this doc (RO vs RW).

- **QNAP SMB user can’t see `.ssh`**
  - No ACLs? Use group perms: `chgrp everyone .ssh` and `chmod 750 .ssh`; make non-secrets `640/644`. Keep the private key `600`.

- **Rsync hangs or times out**
  - Firewall or port mismatch. Verify port (2222/2223/22), and that the NAS can reach the host (`telnet 10.0.78.108 2222` or `nc -vz 10.0.78.108 2222`).

- **Cloud VM rotates IP**
  - That’s normal. `vast_known_hosts` will accumulate entries. You can prune stale lines if needed.

---

## 10) Quick checklist

- [ ] `.ssh` exists with correct perms (`750`).
- [ ] `id_ed25519` = `600`; `id_ed25519.pub`, `known_hosts`, `config` = `644`; `vast_known_hosts` = `664`.
- [ ] `docker-compose.yml` mounts: keys/config/known_hosts **RO**; `vast_known_hosts` **RW**; `/share/sd/SecretFolder:/media`.
- [ ] `ssh-copy-id` done for Forge/Comfy and (when applicable) VastAI.
- [ ] `known_hosts` pre-seeded for LAN; `accept-new` set for VastAI.
- [ ] Test `ssh -F /root/.ssh/config forge echo ok` inside the container.

---

## 11) Appendix

### A. Bootstrap script (optional)

Use `setup_ssh.sh` (in the repo) to create the directory, generate keys, and set perms automatically. It also writes a default `config` as shown above.

```bash
bash setup_ssh.sh
```

### B. Using explicit SSH options (without config)

For VastAI from code you can always pass:

```
-o UserKnownHostsFile=/root/.ssh/vast_known_hosts -o StrictHostKeyChecking=accept-new
```

And for LAN:

```
-o UserKnownHostsFile=/root/.ssh/known_hosts -o StrictHostKeyChecking=yes
```

This mirrors the config file behavior.

---

**Security reminders**
- Keep the private key **out of SMB** if you can. If you must keep it there, keep perms strict (`600`) and directory `750`.
- Never check `id_ed25519` into Git.
- Consider restricting the API with a firewall and/or reverse proxy with HTTPS if exposed beyond your LAN.
