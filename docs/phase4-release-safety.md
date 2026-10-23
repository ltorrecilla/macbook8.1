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

**CPU rollback:** configuration ownership protections and simulated failure tests exist, but the installer is not transactional. A discarded rollback prototype had unsafe path/race assumptions; it is not available for use. Read its Git history if investigating those approaches.
