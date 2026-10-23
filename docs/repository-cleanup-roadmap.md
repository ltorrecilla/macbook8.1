# Repository maintenance and cleanup roadmap

**Status: planned, not performed.** The priority is to preserve the owner's working MacBook8,1 setup, historical evidence and reversible recovery paths. No mass deletes or hardware-changing refactors should accompany this plan.

## Phase 0 — freeze and inventory (first)

- Record a known-good commit/tag, effective Limine command line, kernel versions, driver/module versions and services. Make a local backup before touching boot/driver files.
- Inventory tracked files and scripts by function (audio driver/recovery/EQ, SPI keyboard and trackpad, Bluetooth, camera, CPU limiting, battery/suspend/hibernation, docs/tests).
- Categorize each artifact as **verified on this MacBook**, **experiment**, **obsolete/superseded**, **machine-specific**, or **publicly reusable**; log provenance, licenses, dependencies, privilege level and rollback.
- Check git history and links before moving or deleting; never treat archived evidence as installable code.

## Phase 1 — source of truth and scope

- Keep README as a short compatibility/status matrix with date, kernel, validation scope, risks, and links to detailed guides.
- One maintained guide per subsystem; preserve chronological experiment findings under clearly labeled `docs/history/` or a dated archive.
- Resolve contradictory status statements (e.g. Raw vs D+ login activity, successful hardware test vs simulated tests, battery reporting vs real drain).
- Keep explicitly out of scope: printer configuration and custom keyboard shortcuts, per previous project decisions.

## Phase 2 — organization, without behavioral changes

- Adopt consistent folders such as `docs/{audio,camera,power,spi}/`, `scripts/{install,check,repair,uninstall}/`, `tests/`, and `archive/` only after mapping every existing reference.
- Distinguish read-only diagnostics from privileged installers; give installers matching checker and rollback instructions.
- Deduplicate scripts and generated artifacts, but do not delete upstream source/licensing notices or information needed to rebuild an existing working driver.
- Move in small reviewable PRs; update links and command examples as part of each move.

## Phase 3 — safe interface and verification

- Add a supported-hardware and kernel compatibility check for every destructive/privileged action; especially protect the kernel-specific DMA initcall workaround and multi-module audio replacement.
- Use reproducible pinned upstream dependencies where legal and practical, avoid system-specific IDs/UUIDs in generally reusable commands.
- Add shell/python format and static checks, dry-run/unit tests, and a clean README link check.
- Test install/check/uninstall, reboot, suspend/resume and kernel-upgrade paths **on real hardware** before claiming a ready-made installer.
- Put known failure/rollback recovery and evidence collection steps in contributor docs. Sanitize serials, IDs, personal paths and logs before upload.

## Phase 4 — release and upstream

- Separate production-tested fixes from experimental research (SPI PIO patch, EC wake tweak, D+ processing, hibernation).
- Build an optional, reversible install entry point only after independently validated subsystem installers.
- File focused upstream reports/patches with reproducible hardware evidence and explicit license attribution.
- Publish a release checklist and versioned support matrix; tag an initial stable release only when validated.

## Near-term order of execution

1. Complete the runtime EC suspend test and keep its results in [sleep-battery-drain](sleep-battery-drain.md).
2. Finish kernel-update/DMA compatibility checks and audio recovery regression before restructuring either area.
3. Inventory all tracked files and produce a keep/move/archive/delete proposal.
4. Clean documentation first; reorganize code only with tests and review.
5. Validate on original MacBook and a second machine before claiming general compatibility.

**Acceptance criteria:** no loss of known-good recovery information; README links resolve; every hardware claim has a test date/kernel; install/recovery is reversible and cannot silently clobber a working system; changes are reviewable separately from experiments.
