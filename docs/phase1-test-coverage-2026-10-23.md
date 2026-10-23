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
