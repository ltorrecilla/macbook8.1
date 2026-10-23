# Phase 4 — release-safety and hardware acceptance gates

**Status: planning/checklist, not approval to release.** Recorded 2026-10-23. Phase 3 dependency-map PR #21 was merged and [CI run 39980631428](https://github.com/ltorrecilla/macbook8.1/actions/runs/39980631428) succeeded. Mocked tests and syntax/link checks do not demonstrate safe installation on another laptop.

## Invariants to protect

- Do not alter a working Limine boot entry or kernel-specific DMA initcall blacklist during documentation or installer packaging.
- Do not replace the registered three-module HDA/DKMS stack or the default MacBook_Speaker_Raw sink without explicit diagnosis, backup, and a verified recovery kernel.
- Do not claim hibernation or the EC sleep-drain workaround works until real suspend/resume and battery measurements are reported.
- Never silently take ownership of manual camera/firmware installations or overwrite third-party configuration.
- Never treat CPU frequency caps as thermal safety guarantees. Preserve original policy limits and detect external changes.
- Keep camera, audio, CPU and power changes independent and opt-in.

## Validation matrix

| Subsystem | Automated baseline | Real MacBook acceptance test | Release blocker |
|---|---|---|---|
| Kernel/Apple SPI | 7 mocked DMA compatibility tests, read-only preflight | Current and target kernel: keyboard/trackpad after cold boot, reboot, ordinary suspend/resume | Kernel symbol portability / upstream replacement unresolved |
| Camera | Simulated installer, uninstall ownership and diagnostics tests | Clean installation on matching hardware; mpv capture; app discovery; reboot/resume/update | Wrapper hardware installation not yet confirmed |
| CPU cap | 9 mocked runtime helper tests | Install, restart, reboot, suspend/resume, uninstall and external-manager coexistence | Full hardware persistence and rollback not yet recorded |
| Existing audio | DKMS recovery regression tests and source URL tests | Raw playback, HDA module paths, kernel update and rollback from partial failure | Fresh install not available; provenance/licensing pending |
| D+ processing | No complete service lifecycle automation | Log in/out, A/V pause/resume offset, crash, PipeWire restart, rollback to Raw | A/V sync delay; do not autostart |
| Battery/suspend | Read-only investigation guidance | Timed unplugged baseline and EC experiment, Wh/charge samples, safe lid/power wake | Effect not measured; battery gauge inconsistent |
| Hibernation | Swap output parsing tests | Controlled preflight, preparation, true poweroff/restore, error recovery | Full restore not confirmed and helper machine-bound |

## Installer risk controls (review each before a release)

1. **Identity and preflight:** supported model, OS, installed/running kernel, matching headers and prerequisites must be positively identified. Unknown conditions stop.
2. **Ownership:** detect manual, vendor, and already-managed files. Do not overwrite files not verifiably owned by the installer.
3. **Download integrity/provenance:** pin source revisions and verify checksums where possible. Audit licensing before distributing third-party code or firmware.
4. **Atomicity and idempotency:** reruns preserve existing data; unexpected failure stops without claiming success. Record exactly what may have been changed.
5. **Backup and rollback:** preserve prior configs, services, module state and usable boot entry. Test remove/rollback after complete install and after representative partial failures.
6. **Diagnostics/privacy:** default to local, non-sensitive reports; require human review before sharing archives. Do not commit per-machine identifiers, recordings or generated source bundles.
7. **Documentation and version scope:** list tested kernels, devices, date and evidence; separate simulated CI from physical validation.

## Release phases

- **Pre-release research:** working notes and isolated read-only scripts only; explicitly label privileged and experimental commands.
- **Limited hardware-tested toolkit:** each published installer independently verified for install/check/uninstall/reboot and suspend where applicable, with known-good recovery procedure.
- **General release:** reproducible, licensed and documented drivers; compatibility matrix for each supported model/kernel; clean-install test on more than one machine; no unresolved safety-critical blocker.

## Suggested test record template

For each hardware check record: date, model, firmware if relevant, `uname -r`, installed target kernel, command/feature tested, before/after result, logs sanitized for personal identifiers, exact rollback actions, and whether the laptop booted and resumed without peripherals failing.

## Remaining blockers

- [ ] Full-history secrets/privacy audit and local untracked-file inventory.
- [ ] Third-party audio driver and camera firmware redistribution review.
- [ ] Source-level partial failure and rollback audit for each privileged installer.
- [ ] Real camera wrapper install/uninstall, audio update/recovery, CPU cap persistence and suspend tests.
- [ ] Hibernation recovery and EC wake battery tests only after explicit controlled setup.
- [ ] Versioned release notes plus hardware validation matrix.

**Do not merge unrelated hardware changes into a safety documentation PR.** See [script reference](script-reference.md), [installation matrix](installation-matrix.md), and [kernel update playbook](kernel-update-playbook.md).


---

## Archived Phase 4 engineering notes (2026-10-23)

The following original reports are retained here for engineering context, not instructions to execute experimental rollback code. Each original URL is kept as a redirect.


<a id="phase4-original-1"></a>

### Original: docs/phase4-cpu-failure-validation.md

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


<a id="phase4-original-2"></a>

### Original: docs/phase4-installer-rollback-audit.md

# Phase 4 — privileged installer ownership and rollback audit

**Date:** 2026-10-23. Static source review only; no scripts were executed on the MacBook. The [Phase 4 release-safety checklist](phase4-release-safety.md) remains the release gate.

## Confirmed findings

| Component | Existing protection | Gap / action |
|---|---|---|
| Camera installer | Checks model, PCI device, headers, pinned upstream commits, firmware hashes, source owner marker and manifest, conflicts, ownership before DKMS changes | **Partially installed state may be retained after failures by design.** Confirm retry/uninstall scenarios on real hardware; examine partial firmware installation and DKMS failure recovery. |
| Camera uninstaller | Refuses unrecognized source/manifest and mismatched DKMS ownership; attempts module unload before deletion; preserves firmware | Strong fail-closed behavior, but physical uninstall and rollback not yet validated. Preserve existing checks. |
| CPU installer | Checks model, CPUFreq bounds, service ownership header, helper ownership header, other manager conflicts | **Concrete gap:** it writes `/etc/macbook81-cpu-cap.max-khz` without checking whether an existing config belongs to this installer or preserving its prior value. Service enable/restart failure may leave files/configuration partially installed. |
| CPU uninstaller | Requires owned service marker, disables service before removing unit; only removes helper when its header matches | **Concrete gap:** with an owned unit, removal of `/etc/macbook81-cpu-cap.max-khz` is unconditional, even if the config was changed by another program; interrupted disable/remove paths need tests. |
| CPU runtime helper | Prevalidates all policies, saves previous ceiling, restores only when current value matches applied cap | State recovery after interrupted application needs further testing, especially when only some policies were written. Existing 9 tests cover typical apply/restore and external changes. |
| Audio recovery | Checks registered DKMS identity, matching kernels/headers, source availability and conflicting packages; rebuild then regenerate Limine | Partial DKMS success followed by boot regeneration failure requires a documented rollback/recovery path. Keep as existing-install repair only. |
| Hibernation | Guarded preparation with machine identity and backups | No real hibernate/restore test; keep excluded from release. |

## Priority actions

1. **High priority: CPU config ownership.** Add a fail-closed check for an existing unrecognized configuration before any write. Make uninstall refuse to remove modified/unowned config. Preserve the current valid configuration through safe upgrade/rollback. Write separate simulated installer/uninstaller tests; do not change installed configuration until reviewed.
2. **High priority: CPU partial-failure.** Test failures at service copy, config write, daemon-reload, enable and restart stages. Document whether a retry or dedicated rollback is appropriate without clobbering third-party files.
3. **High priority: Camera partial-state tests.** Supplement existing mocked ownership tests with interrupted firmware copy/DKMS registration cases. Ensure conflict checks remain before privileged mutation.
4. **Medium priority: audio DKMS rollback.** Record exact modified modules and safe recovery when boot-image regeneration fails. Do not replace a working three-module stack in a CI environment.
5. **Keep hibernation and EC sleep experiments outside routine installer workflows.** Neither is a released battery fix.

## Safe sequencing

- Separate source fixes and regression tests by subsystem, starting with CPU ownership. Require passing offline CI.
- Before deploying any modified installer to the actual MacBook: capture its current service/config/helper state, keep a copy, review the test diff, and confirm idempotency/uninstall behavior.
- After a simulated fix, require real hardware confirmation before updating release-status claims.

**Decision:** no hardware or source-code changes in this audit PR. Treat CPU config overwrite/removal protection as the next targeted implementation task. No general-purpose installer release is approved.


<a id="phase4-original-3"></a>

### Original: docs/phase4-cpu-transaction-design.md

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
