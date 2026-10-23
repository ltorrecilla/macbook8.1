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
