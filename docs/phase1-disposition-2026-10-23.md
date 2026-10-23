# Phase 1 — history review and preliminary disposition (2026-10-23)

**Scope and honesty:** GitHub main contained 51 tracked files at this checkpoint. The accessible commits API returned 74 commits on its first page, but that is **not** a full historical secrets scan: individual past file contents, other refs, deleted blobs, forks and local files were not exhaustively checked. Attempts to clone from this analysis environment failed due to DNS resolution of github.com. This report is documentation-only.

## Verified status

- PRs #3–#8 are reflected in current main; automated workflow run 39964164258 completed successfully with 59 tests. This is mocked/offline coverage, not hardware validation.
- Focused pattern review (not a comprehensive detector) of README, hibernation guide, continuation checkpoint, previous licensing review, hibernation helper and .gitignore found **machine-specific filesystem UUID and machine IDs in the hibernation helper**. Do not copy values from that source into reusable examples. No obvious GitHub token, AWS access-key or PEM private-key delimiter was flagged in this limited sample. **This is not an assurance that secrets are absent**.
- Root .gitignore excludes some logs, archives and evidence text; other files can be accidentally staged. Treat history and local untracked data as not yet cleared.

## Provisional keep/move/archive/delete decisions

| Category | Candidate paths | Proposed decision and safeguard |
|---|---|---|
| Canonical | README, LICENSE, .gitignore, .github/workflows/offline-validation.yml, tests/* | **KEEP** and validate continuously |
| Working-system protection | scripts/check-kernel-update.py, scripts/repair-audio.py, current camera and CPU check/install/remove helpers, systemd CPU unit | **KEEP IN PLACE** until hardware regression and rollback tests cover a move |
| Power research | docs/hibernation.md, docs/sleep-battery-drain.md, scripts/macbook81-hibernate-prepare.py | **KEEP EXPERIMENTAL**; mark machine-specific helper not portable |
| Audio research | docs/audio-upstream-comparison.md, docs/dplus-service.md, scripts/try-warm-audio.py, scripts/compare-raw-voice.py, scripts/test-speaker-routing.py | **KEEP EXPERIMENTAL**; prevent auto-running mutating sound scripts |
| Evidence tools | three distinct collect-audio-*.sh tools, audit/stage helpers | **KEEP**; improve privacy warnings and no-overwrite tests before consolidation |
| Historical narrative | docs/continuation-checkpoint.md, docs/speaker-sound-diagnosis.md, docs/audio-support-recovery.md, dated regression history | **ARCHIVE CANDIDATES, NOT YET MOVES**; verify unique details and inbound links first |
| Docs overview | docs/audio.md, audio-packaging.md, audio-update-recovery.md, camera.md, cpu-frequency-limit.md, SPI patch guide, phase1 audit notes | **KEEP**, simplify navigation in Phase 2 |
| Delete | None | **DELETE ZERO FILES** until all remaining gates are satisfied |

## Blocking work before real cleanup

1. On a trustworthy local checkout, perform a full-history scan including all refs and historical blobs with a vetted tool (e.g. Gitleaks), ensuring outputs are private and not committed; review findings manually. A detector's clean result alone is not proof.
2. Inventory local working tree: `git status --short`, `git ls-files --others --exclude-standard`, and carefully review ignored files before sharing paths.
3. Complete detailed licensing/provenance review for kernel-derived audio patches and Apple camera firmware/calibration before redistribution.
4. Validate the link and anchor graph and identify unique material in any archive candidate. Preserve permanent links or redirects when moving documents.
5. Keep the working boot/DMA setup and audio modules unchanged. Move code only in separate, small PRs with corresponding test updates and real hardware recovery checklists.
6. Finish hardware acceptance checkpoints for experimental sleep/hibernation paths; none is a certified general-purpose installer.

## Safe local commands (read-only)

```bash
cd ~/git/macbook/macbook8.1
git status --short
git ls-files --others --exclude-standard
git branch -a
git log --all --oneline -n 20
```

Don't upload these raw outputs if they expose local paths or personal content. A full historical secret scan is a separate, controlled operation with an installed scanner; don't use ad hoc `grep` as a substitute.

**Phase 1 conclusion:** inventory and early triage are ready; CI passes, but **Phase 1 is not fully closed** until complete secrets/history, provenance and local-state gates are reviewed. Phase 2 may begin with a documentation-only navigation proposal, not deletion or code moves.
