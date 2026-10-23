# Phase 4 — CPU limiter failure-path validation

Additional isolated tests cover an orphan ownership marker, a config written without its marker, a tampered config, a symlinked marker, and a valid managed retry. Tests operate only on temporary files. They do **not** exercise the full privileged installation script or real systemd transitions.

## Important distinction

The current installer updates helper, service and config in sequence, then enables/restarts the service. If a command fails in that sequence it can leave a partially updated installation. The ownership helper intentionally fails closed on orphan/modified markers, but **does not itself make the complete install atomic**. A failed write of the ownership marker can leave an unmarked config. Do not promise unattended rollback.

## Remaining implementation gates

- [ ] Safely simulate each privileged install stage (copy helper, copy service, config write, marker write, daemon-reload, enable, restart) with all OS access redirected to temporary fixtures.
- [ ] Test actual uninstall flow after failed service disable, missing helper and incomplete installation; ensure no unrelated files are removed.
- [ ] Consider transactional stage/backup semantics and a recovery procedure in a separate PR after those tests.
- [ ] Verify known-good MacBook CPU cap behavior and upgrade/reinstall using backup and a deliberate hardware test.

Until this is completed, **do not run the changed installer solely to verify cleanup**. See [installer rollback audit](phase4-installer-rollback-audit.md).

## Transactional design follow-up

See [the CPU transactional rollback design](phase4-cpu-transaction-design.md) for the required fresh-install versus existing-upgrade behavior and the next regression test plan. This remains a proposal, not a validated change to the working installation.
