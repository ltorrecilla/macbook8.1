# Phase 3 — safe script organization plan

**Planning only; no scripts moved or changed.** Baseline: main commit `455cd128f23fba25a519182238f9e86188d71aad` (2026-10-23). PR #16 merged, and GitHub Actions [run 39971402169](https://github.com/ltorrecilla/macbook8.1/actions/runs/39971402169) passed. This only confirms the available syntax, mocked unit and heuristic Markdown-link checks; hardware updates and recovery remain separate.

## Principles

1. Keep executable script paths stable until *every* documented caller, test, shell source import, service file and external reference is understood.
2. Preserve working audio driver, default Raw sink, DMA blacklist, Limine boot configuration, camera module and CPU cap on the owner's MacBook.
3. Prefer **no move** if renaming creates more risk than clarity. A new index and doc-only grouping are acceptable.
4. Any future migration must be isolated by subsystem, with a rollback path and CI; never batch boot, DKMS, EFI or suspend changes with cosmetic restructuring.
5. Never run untested mutating scripts merely to validate organization.

## Current script group mapping

| Proposed logical group | Existing paths (keep unchanged now) | Risk and dependencies |
|---|---|---|
| Kernel / preflight | `check-kernel-update.py`, `check-doc-links.py` | First script reads Limine and kernel-specific DMA symbols; critical pre-reboot diagnostic. Second is read-only documentation CI. |
| Audio check/evidence | `audio-preflight.sh`, `audit-audio-bundles.py`, `collect-audio-details.sh`, `collect-audio-evidence.sh`, `collect-audio-support.sh`, `stage-audio-source.py` | Three collectors have distinct output scopes. Reports/archives may include private paths or third-party sources. |
| Audio repair/experiments | `repair-audio.py`, `compare-raw-voice.py`, `test-speaker-routing.py`, `try-warm-audio.py` | Repair modifies DKMS and boot images; warm-audio modifies PipeWire user configuration. Never classify both as read-only. |
| Camera | `camera-common.sh`, `check-camera.sh`, `install-camera.sh`, `uninstall-camera.sh` | Helper is sourced by callers; installer touches firmware and DKMS, uninstaller is ownership-sensitive. Move only as one reviewed unit. |
| CPU | `cpu-cap-control.sh`, `check-cpu-limit.sh`, `install-cpu-limit.sh`, `uninstall-cpu-limit.sh`; `systemd/macbook81-cpu-cap.service` | Service and installed helper paths are coupled; protect uninstall and reboot persistence. |
| Power / experimental | `macbook81-hibernate-prepare.py` | Machine-specific filesystem and boot assumptions; no successful restore recorded. Keep quarantined from general installation. |

## Proposed migration order

**A. Read-only and metadata first.** Add a scripts index, explicit risk labels and tool ownership descriptions at current paths. Make no executable changes.

**B. Test gaps.** Add automated tests for `check-kernel-update.py` (different DMA symbols / installed kernels) and CPU service behavior. Mock privilege and filesystem writes. Run in isolated CI; do not require actual MacBook hardware.

**C. Camera migration last among ordinary subsystem utilities.** If folder moves improve maintainability, first map and update relative `source` references, external README instructions, tests and uninstall paths. Keep compatibility shims at old paths temporarily and regression-test them.

**D. Audio and power guarded separately.** Defer audio repair and hibernation moves until local checkout, licensing/provenance, actual update recovery, and suspend/restore risk gates are cleared.

**E. Remove compatibility shims only after an announced stable release, tracked link checks and real-user validation.** History should remain accessible.

## Required checks before any executable relocation

- [ ] Inventory local modified/untracked/ignored files on the owner's MacBook and archive private recovery assets safely.
- [ ] Inspect exact relative imports, shell sourcing, service `ExecStart`, scripts invoked in Markdown, and tests.
- [ ] Retain full-history security scan and audio/firmware license blockers as open items.
- [ ] Prove read-only checks stay read-only and privileged scripts refuse unsupported hardware.
- [ ] Run offline CI; record the run URL and failures.
- [ ] Verify on actual MacBook: boot input, patched speaker, camera capture, CPU cap and safe suspend, as applicable.
- [ ] Document rollback for both repository migration and installed system state.

**Decision:** Phase 3 begins with a compatibility-preserving documentation/index step. No files are approved for removal or relocation yet.
