# Phase 1 — Validation, licensing and privacy audit (2026-10-23)

**Status:** preliminary targeted audit; no executable changes or hardware tests.

## Verified automated validation

GitHub Actions [run 39964164258](https://github.com/ltorrecilla/macbook8.1/actions/runs/39964164258) completed **successfully** on PR #7 at commit `1954116f0e46d850d4ace4c5a12c008a7469de33`.

The job reports successful Python syntax parsing, shell syntax checks, and `python3 -m unittest discover -s tests -v`; job log reports **Ran 59 tests in 19.464s**. Unit tests use simulated/mock behavior. **This does not establish hardware compatibility, safety of privilege escalation, suspend reliability or a reproducible fresh installation.**

## License and supply-chain observations

- The root `LICENSE` is MIT, copyright 2026 contributors. This should be understood to cover original repository-authored material only; third-party work retains its own terms.
- `docs/audio-packaging.md` explicitly flags kernel-derived GPL material, third-party reverse-engineered codec data and lack of pinned checksum verification for upstream kernel archives in the existing build flow. **Block redistribution of a combined patched driver until provenance, exact license, notices and source availability are reviewed.** The exact upstream license wording must be verified before writing a blanket conclusion.
- `docs/camera.md` links pinned source revisions for `patjak/facetimehd` and `patjak/facetimehd-firmware`, with checksums for extracted firmware. Version pinning and hashing do not grant permission to redistribute proprietary firmware or sensor calibration. Review firmware source/download terms; prefer downloads from documented sources instead of committing binaries.
- `scripts/repair-audio.py` identifies as MIT; the registered DKMS code that it drives is separate and is not included as a tracked installable driver tree in the observed repository.

## Privacy / machine-bound data

- `scripts/macbook81-hibernate-prepare.py` at lines 53–56 embeds a specific old kernel, machine identifiers and root filesystem UUID. **Do not publish these values in diagnostics, logs or reusable configuration examples.** They are identifiers rather than login passwords, but should be kept out of broadly reusable tools. The script's machine-specific guards should not be removed without a secure alternative; never run it against a different machine. Replacement with explicit validated local discovery and confirmations is a later task.
- `collect-audio-evidence.sh` writes source paths and modprobe settings to a text report.
- `collect-audio-details.sh` archives user PipeWire/WirePlumber configuration and locally stored source files.
- `collect-audio-support.sh` searches several paths, including the user's home directory, for three narrowly named helpers and copies them to an archive.
- `.gitignore` excludes some diagnostic patterns, `*.tar.gz` and `*.log`, but does **not** guarantee all generated output, recordings, or personal identifiers are excluded.
- None of these findings constitutes a confirmed leaked credential. **No comprehensive secret scan or history audit has been completed**; rotate credentials only if a real secret is subsequently identified.

## Actions before Phase 2

1. Run a full-file plus **Git history** secrets/privacy scan and manually review findings, without committing generated logs.
2. Audit licenses/attributions in all downloads/build dependencies including Linux HDA patches, camera firmware, calibration and any helper code imported from elsewhere.
3. Move machine-bound hibernation values behind per-installation discovery only after safety tests; keep existing helper documented as experimental in the meantime.
4. Review the privacy warnings and output names of all evidence collectors; add safe no-overwrite checks and scrub/redaction guidance where lacking.
5. Audit Markdown links comprehensively and verify anchor fragments, not just file targets.
6. Inventory untracked and ignored files on the **real MacBook** before any move/delete action; GitHub cannot inspect the local checkout.
7. Require real hardware regression checks and rollback instructions before distributing a stable installer.

## Decision

- **Keep all files** for now; no deletion or move is authorized by this review.
- Existing automated tests are now confirmed passing at the noted commit, with limits above.
- Treat the original audio driver source/firmware redistribution and machine-bound hibernation helper as packaging blockers.
- Subsequent source changes must happen in separate reviewed PRs, not in this documentation audit.
