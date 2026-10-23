# Phase 1 — consolidated engineering audit archive (2026-10-23)

These three historical documents are preserved verbatim below. This is dated audit evidence, not current installation instructions. See [script reference](script-reference.md), [release safety](phase4-release-safety.md), and [documentation index](INDEX.md) for current guidance.

---

<a id="original-1"></a>

## Original file: `docs/phase1-source-audit-2026-10-23.md`

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


---

<a id="original-2"></a>

## Original file: `docs/phase1-test-coverage-2026-10-23.md`

# Phase 1 — Test coverage and repository hygiene review (2026-10-23)

**Scope:** static inspection of all six tracked `tests/test_*.py` files, `.gitignore`, and main-branch tree at `0dbf6072e9535cbad367e8189cdc4cb9077cec4e`. This is a coverage map, **not a test execution report**. No tests ran on the MacBook, no system settings changed, and all existing files remain untouched.

## Test inventory

| Test file | Discovered test methods | Primary target | Coverage emphasis |
|---|---:|---|---|
| `tests/test_audio_source_url.py` | 4 | `scripts/repair-audio.py` | Upstream archive naming/version logic |
| `tests/test_audit_audio_bundles.py` | 3 | `scripts/audit-audio-bundles.py` | Consistency and unsafe archive members |
| `tests/test_camera_scripts.py` | 18 | Camera install/uninstall/check scripts | Simulated hardware guards, firmware preservation, DKMS ownership, rollback failures |
| `tests/test_hibernate_swaps.py` | 4 | `scripts/macbook81-hibernate-prepare.py` | `swapon` parsing / error rejection |
| `tests/test_repair_audio.py` | 28 | `scripts/repair-audio.py` | Kernel/header prerequisites, DKMS recovery, conflict/failure gates, boot regeneration logic |
| `tests/test_stage_audio_source.py` | 2 | `scripts/stage-audio-source.py` | Staging allowlist and partial failures |
| **Total** | **59** | | Count from named test methods, not tests successfully run |

No dedicated tracked automated test files were found for `check-kernel-update.py`, CPU limiter and its systemd service, audio collectors, `try-warm-audio.py`, `compare-raw-voice.py`, `test-speaker-routing.py`, or the EC sleep experiment. This does not prove absence of manual test history in docs.

## Preliminary priority

1. **Critical:** test `check-kernel-update.py` against both matching and changed DMA initcall symbols and multiple installed kernel states; do not change the working blacklist while testing.
2. **Critical:** add mocked/dry-run tests of `macbook81-hibernate-prepare.py` beyond swap parsing, particularly boot/fstab backups, privilege guard and partial-failure paths; real hibernation is a separate unsafe-to-assume milestone.
3. **High:** add simulated CPU limit install/check/uninstall tests with sysfs fixtures and systemd calls mocked, including failure rollback.
4. **High:** cover `try-warm-audio.py` backup and restore behavior under errors before any reuse or relocation.
5. **Medium:** add privacy/no-overwrite/path handling tests to audio collection scripts. Never upload collectors' output unreviewed.
6. **Medium:** maintain the already useful camera and audio-repair simulated regressions and validate them on physical hardware when appropriate.

## Repository hygiene

Current `.gitignore` ignores: `macbook81-diagnostics*.txt`, `macbook81-audio-evidence*.txt`, `*.tar.gz`, `*.log`, `*.orig`, `*.rej`. This is not an exhaustive privacy barrier. Other generated files, recordings or local bundles may still appear as untracked; use `git status --short` and review before committing. Never add broad ignore patterns that hide intentional source files without analysis.

The tree contains no tracked `.github/workflows/` at this snapshot. Automated CI validation is **not evidenced** by the file tree. Add a non-privileged offline test workflow later, only after runner dependencies and safety are reviewed. Do not execute privileged install, EFI writes, suspend or hibernation in CI.

## Next gates

- [ ] Run the Python unit tests in an isolated checkout and record actual passing/failing results.
- [ ] Perform shell syntax/static checks for relevant scripts and record any actionable findings.
- [ ] Validate internal Markdown links against complete tracked paths, including anchor links.
- [ ] Finish licensing/provenance and potential secrets/machine-ID review.
- [ ] Inspect the actual MacBook working tree for untracked/ignored files; remote GitHub cannot provide this.
- [ ] Review PRs and finalize move/archive candidates only after evidence preservation and complete audit.

**Phase 1 conclusion at this point:** 59 discovered test methods with uneven subsystem coverage. **No file deletions or code reorganization recommended yet.**


---

<a id="original-3"></a>

## Original file: `docs/phase1-validation-workflow.md`

# Offline validation workflow (Phase 1)

Proposed GitHub Actions workflow: `.github/workflows/offline-validation.yml`.

Runs on pull requests and explicit manual dispatch in a disposable GitHub-hosted Ubuntu runner. It performs Python AST parse on scripts/tests, `bash -n` on shell scripts, and `python3 -m unittest discover -s tests -v`. No root privileges, DKMS installs, camera access, hibernation, Limine changes, or laptop interaction. Workflow permissions are restricted to `contents: read`.

**Validation status: not yet executed/confirmed.** On 2026-10-23 an attempt to clone the GitHub repository into the analysis environment failed because the host could not resolve `github.com`; thus no local passing-test claim can be made. GitHub's workflow run must be inspected after this PR is available. Unit tests depend on mocks and are not a substitute for real MacBook suspend, audio, camera or boot validation.

Initial link check: 29 relative links in README and one in `docs/audio.md` resolved against the tracked repository tree. The audit also checked the three Phase 1 inventory/audit notes and found no missing relative file paths. **This was a partial review**, not validation of every Markdown link, anchor, external target or README correctness.

Remaining:
- [ ] Review GitHub Actions run logs and test outcomes; record failures, then fix separately.
- [ ] Validate all internal Markdown paths and anchor fragments.
- [ ] Inspect third-party licenses, source/firmware redistribution and private identifiers in tracked text.
- [ ] Check actual working-tree status on the MacBook (remote repository cannot show untracked data).
- [ ] Keep cleanup operations separate from validation workflow.
