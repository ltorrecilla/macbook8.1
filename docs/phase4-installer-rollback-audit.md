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
