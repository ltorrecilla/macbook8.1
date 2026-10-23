# Phase 4 — Fresh rollback prototype security review

**Status: BLOCKED for production integration.** PR #30 merged and CI passed, but tests only exercise the existing fixture scenarios. A green CI result does not establish safe deletion of real filesystem objects.

## Findings

1. **High — lexical prefix is not directory containment.** The condition `"$path" == "$CPU_ROLLBACK_ROOT/"*` accepts strings containing `../`; deletion can escape the intended root. The root might also be a symlink.
2. **High — symlinked ancestor directories.** `-L "$path"` checks only the final path component. A directory in the path may be a symlink into another location.
3. **High — check-to-delete race.** A file may change between `sha256sum` and `rm`. Shell-level hashes plus a later pathname-based removal cannot provide atomic ownership verification.
4. **Medium — untrusted manifests and root.** Missing secure ownership/mode and manifest provenance checks; a tampered manifest could influence deletion targets.
5. **Medium — incomplete transaction semantics.** No robust handling of service enablement, partial installation, interruption, directories or rollbacks that fail.

## Required next step

Do **not** source `scripts/cpu-fresh-rollback-prototype.sh` in a privileged installer. It is a research fixture and should not be run with root privileges. The current production installer remains separate.

For a prospective real implementation:
- Design trusted transaction manifests tied to a specific installation attempt, with explicit allowed paths and secure ownership.
- Use descriptor-relative filesystem operations with verified directory handles where applicable; simple `realpath` checks alone do not eliminate races.
- Ensure rollback preserves externally modified or pre-existing files, reports incomplete restoration, and has a verified path to restore prior systemd state.
- Add adversarial tests for `../`, symlinked ancestors, malicious manifests, races and interrupted stages in disposable fixtures. No tests may access real `/etc` or CPU sysfs.
- Require separate security review and real hardware validation before integration.

**Decision:** retain the existing working CPU configuration and do not claim transactional rollback is implemented.
