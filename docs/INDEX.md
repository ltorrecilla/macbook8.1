# Documentation index — MacBook8,1 on CachyOS

The project's target is the **12-inch Early 2015 MacBook8,1**. Fixes are not automatically portable to other Apple laptops. Some steps require root privileges or modify kernel, DKMS, firmware, power-management or audio settings. **Read the linked guide and rollback path before executing a script.** A working result on one machine is not a validated general installer.

Return to [README and status tracker](../README.md).

**Before a CachyOS kernel reboot:** follow the [kernel-update safety playbook](kernel-update-playbook.md) to check both the DMA keyboard/trackpad workaround and the separate audio driver dependency.

**Installing or repairing a subsystem?** Start with the [installation, verification and rollback matrix](installation-matrix.md) before following a subsystem-specific guide.

## Hardware and compatibility

| Area | Primary guide | Current scope |
|---|---|---|
| Keyboard / trackpad, kernel updates | [Kernel-update regression and DMA symbol workaround](kernel-update-regression-2026-10-22.md) | Kernel-specific boot workaround; [read-only pre-reboot checker](../scripts/check-kernel-update.py) |
| Future SPI alternative | [Upstream SPI PIO patch evaluation](spi-upstream-pio-patch.md) | **Untested candidate**, not an installed replacement |
| Camera | [Camera setup and application discovery](camera.md) | Live capture verified in mpv, other applications still unverified |
| Audio | [Audio overview](audio.md) | Existing MacBook sound recovery; no validated universal installer |
| CPU limiting | [CPU frequency cap](cpu-frequency-limit.md) | Confirmed initial cap; regression across updates/resume pending |
| Battery sleep drain | [EC wakeup experiment](sleep-battery-drain.md) | Runtime-only proposal, **not yet confirmed effective** |
| Hibernation | [Experimental hibernation preparation](hibernation.md) | Machine-specific, restore never confirmed |

Bluetooth workaround is tracked in the [README status table](../README.md); there is not yet a validated reusable Bluetooth installer/standalone guide. Battery *reporting* inconsistencies are separate from actual energy drain and remain open.

For a compact decision guide, see the [audio guide map](audio-guide-map.md).

## Audio: choose the right document

- [Audio overview](audio.md): scope and known limitations
- [Audio recovery after a CachyOS update](audio-update-recovery.md): recovery for an **already installed** patched driver, not a fresh installer
- [Source packaging plan](audio-packaging.md): prerequisite work before any fresh-install release
- [D+ clarity per-user service](dplus-service.md): experimental processing, opt-in only; autostart and A/V timing unresolved
- [Upstream profile comparison](audio-upstream-comparison.md): still-open controlled listening experiment
- [Recovered missing installer support files](audio-support-recovery.md): historical recovery notes; not the standard repair procedure
- [Speaker routing diagnosis](speaker-sound-diagnosis.md) and [continuation checkpoint](continuation-checkpoint.md): experimental/historical evidence; **retained**, not obsolete

The [historical-document archive plan](history-archive-plan.md) identifies dated investigations to preserve and the link checks required before moving them.

**Phase 3:** see the [script organization and compatibility plan](phase3-script-organization.md). No executable relocations are approved yet.

For each available script and its side effects, use the [script reference](script-reference.md) before executing anything.

The [Phase 3 dependency map](phase3-dependency-map.md) records which script, systemd and CI paths must remain compatible before any relocation.

**Release preparation:** [Phase 4 safety gates and hardware acceptance checklist](phase4-release-safety.md) documents what must be verified before installers or releases can be considered stable.

## Maintenance and contributor references

- [Repository cleanup roadmap](repository-cleanup-roadmap.md) and [Phase 1 disposition](phase1-disposition-2026-10-23.md)
- [Phase 1 file inventory](phase1-inventory-2026-10-23.md), [source audit](phase1-source-audit-2026-10-23.md), [test coverage](phase1-test-coverage-2026-10-23.md)
- [CI validation and limitations](phase1-validation-workflow.md) and [licensing/privacy audit](phase1-license-privacy-audit-2026-10-23.md)
- [Offline validation workflow](../.github/workflows/offline-validation.yml): syntax and mocked unit tests, **not** physical hardware certification
- [7.3.0 kernel regression history](kernel-update-regression-2026-10-22.md)

## Documentation rules for future changes

1. Preserve model, kernel version, date, real-hardware vs simulated test status, risks and rollback.
2. Keep diagnostics separate from mutating install/repair/uninstall/experimental actions.
3. Keep active guides current; preserve unique dated investigations rather than deleting evidence.
4. Do not copy fixed machine identifiers, filesystem UUIDs, firmware blobs or kernel-specific DMA symbols to a different laptop without verification.
5. Printer customization and custom keyboard shortcuts are outside the repository's agreed scope.

Phase 2 initially reorganizes **navigation only**. Existing files, paths and commands remain unchanged.
