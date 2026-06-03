# HETZ-1A — Server Access, DNS, Firewall and Merge-Readiness Preflight for Hetzner IP 178.105.238.18

## Objective
The objective of this preflight audit is to verify GitHub merge readiness, server SSH connectivity, DNS resolution, and firewall configurations for the target Hetzner server `178.105.238.18` prior to live deployment.

## Preflight Summary
* **Target IP**: `178.105.238.18` (typographical trailing pipe removed).
* **Git Merge Readiness**: **Blocked**. Branch `fix/cap-fm-uk-source-safety` (CAP-UK-0) and `chore/hetzner-deployment-readiness` (HETZ-0/HETZ-0B) are pushed to origin but have not yet been merged into `main`/`origin/main`.
* **SSH Connectivity**: **Blocked**. Tested connection using the local SSH key `~/.ssh/id_ed25519` for both `root` and `deploy` users; both returned `Permission denied (publickey,password)`.
* **DNS Resolution**: **Blocked**. No domain has been specified yet, so A record resolution to `178.105.238.18` cannot be verified.
* **Server baseline / Docker configuration**: **Blocked**. Read-only audit could not be performed due to failed SSH access.

## Proposed Resolution Paths
1. **GitHub PR Merge**: The repository owner must merge PR 1 (`fix/cap-fm-uk-source-safety`) and then PR 2 (`chore/hetzner-deployment-readiness`) on GitHub into the `main` branch.
2. **SSH Access Keys**: The repository owner must confirm the correct SSH user (`root`/`deploy`) and install the local public key `~/.ssh/id_ed25519.pub` onto the target server's `authorized_keys` file.
3. **Domain & DNS Setup**: Provide the target domain name (e.g. `radio.yourdomain.com`) and configure the A record pointing to `178.105.238.18`.

## Verification & Stop Condition
* Stop. Do not attempt deployment or configuration changes until merge, SSH access, and domain parameters are resolved.
