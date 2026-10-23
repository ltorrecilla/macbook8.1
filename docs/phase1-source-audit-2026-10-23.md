# Phase 1 follow-up: source safety and overlap audit (2026-10-23)

**Review scope:** static inspection on GitHub main, 2026-10-23. Reviewed 14 script files for notable filesystem/service commands and read all three audio collection scripts; compared headings of six audio guides. No commands were executed on the MacBook, no behavior or installations were tested, and no executable changes are proposed. This is a targeted audit, **not** a complete line-by-line security review of all project code. Follow [phase 1 inventory](phase1-inventory-2026-10-23.md).

## Audio collection scripts — keep separate

| Script | Actual role | Output and side effects | Decision |
|---|---|---|---|
| `collect-audio-evidence.sh` | Basic driver/module/config/path and sink inventory, without source file contents | Writes a local `.txt` report. Scans parts of `$HOME` for candidate file *paths* and copies modprobe config **text** into report. | **KEEP**, diagnose lightweight; warn about private paths/config. |
| `collect-audio-details.sh` | Full technical audio bundle (PipeWire/WirePlumber/modprobe configs, source files, sink data) | Writes tar.gz containing configuration and potentially source code; temporary staging dir is removed via `trap`. DMI guard and no-clobber output check present. | **KEEP**, evidence/source archival; inspect for private and license-restricted content before sharing. |
| `collect-audio-support.sh` | Narrow recovery of three missing installer helper files: `efi_recover.py`, `mb81-resume-recover.service`, `mb81-jack-switch.service` | Writes tar.gz with up to 40 matching files in known locations including the user's home; guards normal-user and DMI. | **KEEP as specialist recovery**; not a generic audio collector. |

**No deduplication recommendation yet:** these scripts overlap in file-search mechanics but have distinct outputs and purpose. A future common helper must preserve privacy checks, no-clobber semantics, and exact collection scope. None is safe to automatically upload.

## Specific operational risks and guardrails

| Area/path | Static evidence | Recommended action |
|---|---|---|
| `scripts/repair-audio.py` | `--repair` runs DKMS installation for registered audio module and `limine-mkinitcpio`, and checks pacman DB lock; `--check` is a separate read-only mode. | KEEP, **privileged existing-install recovery only**. Review backup/rollback and failure after partial DKMS work before redesign. Never present as fresh audio installer. |
| `scripts/macbook81-hibernate-prepare.py` | `--apply` is capable of filesystem/swap, boot and service configuration changes; defaults refer to the owner's Limine and filesystem setup; explicit check/status modes. | EXPERIMENT + MACHINE-SPECIFIC. Do not reuse as a general installer or run as part of cleanup. Require complete first physical hibernate/restore validation. |
| `scripts/install-camera.sh` | Downloads upstream sources/firmware, stages under `/usr/src`, registers/installs DKMS, then `modprobe`; guards version and checks ownership via common helpers. | KEEP; preserve pins and idempotency checks. Hardware clean install not yet validated. |
| `scripts/uninstall-camera.sh` | `modprobe -r`, `dkms remove --all`, `rm -rf` owned source path; uses common helper preflight to reject unexpected DKMS entries. | KEEP; must retain strict ownership verification, ensure failure never removes other installations. |
| `scripts/install-cpu-limit.sh`, `scripts/uninstall-cpu-limit.sh` | Write/remove systemd unit, `/usr/local/libexec` helper and `/etc` config; enable/restart or disable service. | KEEP together as reversible pair; test reinstall, shutdown and rollback behavior before relocation. |
| `scripts/try-warm-audio.py` | Despite experimental filename, performs **writes** to PipeWire user configuration/default, creates/restores backup and restarts user PipeWire and WirePlumber services. | **EXPERIMENT / MUTATING**. Never run automatically or classify as read-only diagnosis; document preconditions and failure recovery before reuse. |
| `scripts/test-speaker-routing.py` | Uses `pw-play`, makes test audio and may drive speakers. | EXPERIMENT; safe-volume/hearing precaution; not a system configuration repair. |
| `scripts/check-kernel-update.py` | Reads `/etc/default/limine` and installed kernel module directories; checks kernel-specific DMA initcall symbols. | KEEP read-only critical pre-reboot check. Revalidate on each kernel version, protect its failure status messages. |
| `scripts/camera-common.sh` | Contains critical `/usr/src` and DKMS ownership checks shared by installer and uninstaller. | KEEP alongside callers. Never move in isolation. |
| `scripts/cpu-cap-control.sh` | Manipulates CPU sysfs cap/state, intended for the systemd service. | KEEP paired with service; review sysfs feature assumptions and idempotency. |

**Safety conclusion:** the repository has several scripts with destructive-capable commands (`rm -rf`, DKMS removals, service restarts, boot regeneration), generally within bounded operations. This audit does **not** establish that all guardrails are sufficient. The main immediate documentation risk is treating experimental/mutating commands as diagnostics. No confirmed exploit or data-loss bug is asserted.

## Documentation consolidation map (proposal only)

- Main audio entry: `audio.md` stays a concise overview with pointers to current workflow.
- Recovery: `audio-update-recovery.md` is the canonical *existing-install* kernel-update recovery guide. `audio-support-recovery.md` preserves prior recovery of missing helper files, **not a duplicate**.
- Packaging: `audio-packaging.md` remains separate: future fresh-install prerequisites and license/safety gate.
- Sound quality: `audio-upstream-comparison.md` and `dplus-service.md` reflect distinct comparison and user-service experiments.
- Historical evidence: `continuation-checkpoint.md` and `speaker-sound-diagnosis.md` are **possible archive candidates after unique results and backlinks are inventoried**; no deletion or move before this.
- Regression history: `kernel-update-regression-2026-10-22.md` should stay discoverable from the live kernel compatibility instructions.

## Remaining Phase 1 gates

- [ ] Full line-by-line review of every mutating script, dependency, firmware/source integrity and rollback (this report is preliminary).
- [ ] Run offline automated tests/static checks in an isolated workspace with results recorded by tool and revision.
- [ ] Compare doc links and overlap by content (not headings only), map preserved evidence and external references.
- [ ] Check licenses and sensitive fields in tracked files and generated archives.
- [ ] Obtain **local** `git status --short`, `git ls-files --others --exclude-standard` and ignored-file inventory on the MacBook; GitHub cannot see the working tree.
- [ ] Only then write the final keep/move/archive/delete proposal. At present: **delete none**.

This is a documentation-only classification; do not apply changes to the working laptop based solely on this audit.
