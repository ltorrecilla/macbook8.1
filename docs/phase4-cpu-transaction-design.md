# Phase 4 — CPU installer transactional rollback design

**Status:** design proposal only; do not deploy to the MacBook yet. On 2026-10-23, [PR #27](https://github.com/ltorrecilla/macbook8.1/pull/27) merged after [passing CI](https://github.com/ltorrecilla/macbook8.1/actions/runs/39983786942). Its fixtures show that stage failures are reported, not that the prior state is restored.

## Critical distinction: fresh install vs upgrade

| Starting state | Required failure outcome | Safety concern |
|---|---|---|
| No prior owned files or service | Remove *only* files created during failed attempt; do not affect unrelated files | Interrupted install may already have enabled a service or applied a CPU cap |
| Existing owned service/helper/config with valid marker | Restore prior bytes, modes and previously enabled/running state after stage failure | Unconditionally deleting files would break a working installation |
| Existing legacy installation without marker | Preserve all bytes and do not silently adopt changed configuration | Adoption must be explicit and checksummed |
| Unowned, modified, or symlinked service/helper/config | Refuse before any writes | Never overwrite or delete third-party data |
| Failure after service enable/restart | Attempt to stop only newly started service, restore files, daemon-reload and previous service state | Rollback itself can fail; show a recovery report rather than claim success |

## Proposed implementation sequence

1. Preflight all model, kernel/sysfs, file-ownership and configuration checks **before writes**.
2. Save a manifest of which managed paths exist, their checksums, modes and the service enable/active state. Stage backups in a private root-owned directory on the same filesystem; protect against symlinks and races.
3. Stage new helper, unit, config and marker in temporary files; validate checksums and source before promotion. The marker and config must be treated as a pair.
4. Use an explicit state machine rather than a blanket EXIT trap that can destroy working files. Track each committed mutation and service action in a local journal.
5. On failure, restore only the entries whose identities still match what this invocation wrote; never overwrite files subsequently modified by another actor. Restore previous unit enable/active state.
6. Preserve evidence if rollback fails; output the exact file paths and safe manual recovery steps, and return nonzero.
7. On success, remove staging and backups only after post-start validation, and record the new installed version.

## Required isolated tests before changing production installer

- [ ] Fresh install fails during each copy/config/marker/systemd stage; files created by the attempt are removed only where owned.
- [ ] Existing working installation fails at each stage; exact previous file bytes, ownership marker and service state remain intact.
- [ ] Symlink, altered manifest, unexpected file, and concurrent modifications fail closed.
- [ ] Interruption between config write and ownership marker does not lose the original config.
- [ ] Repeated install/retry is idempotent.
- [ ] Rollback failure is reported as **incomplete**, with no false success message.
- [ ] Successful upgrade followed by uninstall respects original state or documents exactly what remains.
- [ ] CI uses only temporary fixtures and mocked systemd; no sudo, real sysfs, boot or DKMS actions.

## Release decision

**Do not claim CPU installer transactional safety yet.** The current merged ownership checks and lifecycle tests provide useful protection, but partial-install/upgrade restoration remains open. Keep the current MacBook configuration as-is while implementation is reviewed in a separate, narrowly scoped PR.
