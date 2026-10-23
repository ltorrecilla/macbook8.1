# Phase 1 — Repository inventory (2026-10-23)

**Scope:** read-only audit of GitHub `main` at `fe056f9c15aa36e8ead3958306f5415c30194ed4`. GitHub Git Trees API returned `truncated: false`: **43 tracked files**, about **272,117 bytes**; directories are excluded from the count. This is a *file/path and README-level* inventory, not a full code review, license audit, local-installation audit or hardware test. No existing script, driver, service, kernel parameter or system setting was changed.

## Classification legend

- **KEEP** — maintain as canonical project infrastructure or current tool; requires later review/testing.
- **REVIEW** — retain unchanged pending deeper code, overlap, safety or accuracy review.
- **HISTORY CANDIDATE** — consider archiving historical context only after links and unique evidence have been checked.
- **EXPERIMENT** — retain clearly marked as unverified/experimental; must not enter a one-click installer.
- **MACHINE-SPECIFIC** — guard against reuse of hard-coded installation data or kernel-specific symbols.

A classification is **not a claim that code is safe or works**. No files are approved for deletion in Phase 1.

## Complete tracked-file register (main)

| Path | Phase 1 label | Recommendation |
|---|---|---|
| `.gitignore` | KEEP | Review ignored logs, backups, compiled assets and secrets |
| `LICENSE` | KEEP | Verify attribution and third-party kernel-derived code licensing |
| `README.md` | KEEP | Retain as short compatibility and verified-status entry point |
| `docs/audio-packaging.md` | REVIEW | Keep installer prerequisites, provenance and licensing gates |
| `docs/audio-support-recovery.md` | REVIEW | Check overlap with current recovery guide before merging |
| `docs/audio-update-recovery.md` | KEEP | Preserve 7.3.0 recovery and update regression record |
| `docs/audio-upstream-comparison.md` | EXPERIMENT | Preserve controlled comparison findings and untested tasks |
| `docs/audio.md` | REVIEW | Assess as main audio overview; remove duplicate assertions later |
| `docs/camera.md` | KEEP | Preserve live capture confirmation vs unresolved app discovery |
| `docs/continuation-checkpoint.md` | HISTORY CANDIDATE | Preserve unique evidence and links before archiving |
| `docs/cpu-frequency-limit.md` | KEEP | Preserve scope and rollback instructions |
| `docs/dplus-service.md` | EXPERIMENT | Keep auto-start and A/V timing cautions visible |
| `docs/hibernation.md` | EXPERIMENT / MACHINE-SPECIFIC | No successful full hibernate/resume reported |
| `docs/kernel-update-regression-2026-10-22.md` | KEEP / HISTORY CANDIDATE | Retain current kernel regression evidence; later move historical notes |
| `docs/speaker-sound-diagnosis.md` | HISTORY CANDIDATE | Compare with newer D+ and upstream documentation |
| `docs/spi-upstream-pio-patch.md` | EXPERIMENT | Candidate upstream replacement for brittle blacklist; untested locally |
| `scripts/audio-preflight.sh` | KEEP | Read-only diagnostic; review host assumptions |
| `scripts/audit-audio-bundles.py` | REVIEW | Check duplication with evidence/source collection workflow |
| `scripts/camera-common.sh` | KEEP | Shared library for camera wrappers; check callers |
| `scripts/check-camera.sh` | KEEP | Read-only camera check |
| `scripts/check-cpu-limit.sh` | KEEP | Verify CPU cap implementation and dependencies |
| `scripts/check-kernel-update.py` | KEEP / MACHINE-SPECIFIC | Critical kernel/DMA compatibility check; keep stable |
| `scripts/collect-audio-details.sh` | REVIEW | Review overlap, captured private data and destinations |
| `scripts/collect-audio-evidence.sh` | REVIEW | Review overlap, captured private data and destinations |
| `scripts/collect-audio-support.sh` | REVIEW | Review overlap, captured private data and destinations |
| `scripts/compare-raw-voice.py` | EXPERIMENT | Preserve acoustic research; verify dependencies |
| `scripts/cpu-cap-control.sh` | KEEP | Runtime service helper; review safety and rollback |
| `scripts/install-camera.sh` | KEEP / REVIEW | Simulated tests exist; physical fresh install not validated |
| `scripts/install-cpu-limit.sh` | KEEP | Privileged action: review idempotency and uninstall behavior |
| `scripts/macbook81-hibernate-prepare.py` | EXPERIMENT / MACHINE-SPECIFIC | Guarded preparation; full restore untested |
| `scripts/repair-audio.py` | KEEP / MACHINE-SPECIFIC | Recovery for existing install, **not** fresh audio installer |
| `scripts/stage-audio-source.py` | KEEP / REVIEW | Offline preparation; track source provenance |
| `scripts/test-speaker-routing.py` | EXPERIMENT | Audio routing investigation rather than general validation |
| `scripts/try-warm-audio.py` | EXPERIMENT | Validate purpose/effects before reuse |
| `scripts/uninstall-camera.sh` | KEEP / REVIEW | Validate wrapper-owned removal only |
| `scripts/uninstall-cpu-limit.sh` | KEEP | Preserve reversible workflow |
| `systemd/macbook81-cpu-cap.service` | KEEP | Audit service privilege, dependencies and login behavior |
| `tests/test_audio_source_url.py` | KEEP | Protect regression around kernel source URLs |
| `tests/test_audit_audio_bundles.py` | KEEP | Protect audit tool behavior |
| `tests/test_camera_scripts.py` | KEEP | Simulated tests do not equal real camera validation |
| `tests/test_hibernate_swaps.py` | KEEP | Protect portability of swap reader |
| `tests/test_repair_audio.py` | KEEP | Keep regression coverage for repair wrapper |
| `tests/test_stage_audio_source.py` | KEEP | Preserve offline staging tests |

## Observations and backlog

1. **Documentation overlap, not automatic redundancy:** `audio.md`, `audio-support-recovery.md`, `audio-update-recovery.md`, `audio-packaging.md`, `speaker-sound-diagnosis.md`, and `continuation-checkpoint.md` cover related but not necessarily duplicate material. Inspect actual content/links before moving anything.
2. **Three audio collectors:** `collect-audio-details.sh`, `collect-audio-evidence.sh`, `collect-audio-support.sh` need side-by-side review for purpose, private information, and outputs. No consolidation decided.
3. **High-risk privileged interfaces:** `repair-audio.py`, `macbook81-hibernate-prepare.py`, install/uninstall scripts, service and boot checker need source-level audit before refactoring.
4. **No bundled complete audio driver/install tree in this 43-file listing:** README describes existing-machine audio recovery, not a reproducible fresh driver installation.
5. **Keep support matrix precise:** MacBook8,1 model, tested kernel, reported success, hardware-tested vs simulated, and rollback. Avoid generalizing to all MacBooks.
6. **Known open issues:** battery fuel-gauge inconsistency, s2idle drain, hibernation, camera app discovery, D+ service persistence, audio packaging, kernel-update compatibility.
7. **Removed project scope:** printer and custom keyboard shortcuts should not be reintroduced.
8. **Prior documentation PR:** [#3](https://github.com/ltorrecilla/macbook8.1/pull/3) adds the proposed EC sleep experiment and cleanup roadmap. It is separate from this main-based inventory; reconcile/merge both without losing either.
9. **External reference and privacy audit needed:** validate README/doc links and check sample logs, fixed machine IDs, serials, local paths, and firmware redistribution rights. The current tree listing alone cannot establish these.
10. **No deletion list yet:** Phase 1 decision is **retain all 43 tracked files** until full script/guide review and measured machine regressions are complete.

## Proposed next audit sequence

- [x] Snapshot complete tracked paths and file sizes on main.
- [x] Record subsystem grouping and provisional classifications.
- [ ] Inspect every executable for shellcheck/python static issues, root writes, kernel/EFI/boot modifications and error handling.
- [ ] Compare all audio collectors and overlapping historical audio guides; produce an evidence-preserving consolidation map.
- [ ] Map tests to corresponding tools; run non-hardware tests without writing to laptop config.
- [ ] Inventory **local untracked files** and installed machine state separately on the MacBook (cannot be inferred from GitHub).
- [ ] Review licenses/third-party origin, secrets and system-specific identifiers.
- [ ] Finalize keep/move/archive/delete proposal in a separate PR, explicitly requiring backup and signoff before deletions.

## Suggested non-destructive local inventory

Run from the actual checkout, if available, to capture untracked and ignored files **without uploading sensitive contents**:

```bash
cd ~/git/macbook/macbook8.1
git status --short
git ls-files
git ls-files --others --exclude-standard
git status --short --ignored
```

Review outputs before sharing. These commands do not remove or alter files. Do not run any installers to satisfy this audit.

**Gate for phase 2:** reviewed inventory, documented owners/rollback, and a stable baseline for audio, SPI, camera, CPU and suspend; no mass cleanup while behavior remains unverified.
