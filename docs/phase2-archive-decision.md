# Phase 2 — internal link audit and archive decision

**Decision (2026-10-23): preserve historical documents at their current paths.** Historical pages already carry dated notices and point readers toward current guidance. Moving them now risks breaking unknown external URLs and relative references while offering little benefit. Keep the original measurements, failed tests, hashes and recovery context available.

## Link checking

Run from a repository checkout:

```bash
python3 scripts/check-doc-links.py
```

This is a **read-only**, standard-library Python checker of inline relative Markdown links and Markdown heading fragments. It ignores external links and does not validate public web targets. It approximates GitHub anchor generation and is not a complete Markdown parser: reference-style links, HTML links, sophisticated inline markup and some complex fenced code formatting still require review.

The [offline CI workflow](../.github/workflows/offline-validation.yml) now invokes this check on pull requests and manual runs. **Do not claim it passed until inspecting the actual CI result.** Any failure should be triaged for a genuine broken link versus parser limitation before editing evidence.

## Archive candidates retained in place

- [Continuation checkpoint](continuation-checkpoint.md): acoustic comparisons, captured recordings, routing tests and follow-up context.
- [Speaker sound diagnosis](speaker-sound-diagnosis.md): original four-channel and DSP measurements.
- [Audio support recovery](audio-support-recovery.md): source manifest, hashes and provenance clues.
- [Kernel update regression](kernel-update-regression-2026-10-22.md): keep as actively useful DMA failure evidence; not an archive candidate.
- [Current audio update recovery](audio-update-recovery.md): remains the canonical existing-install recovery guide.

## Future archival gates

Only reconsider file moves if a real navigation or maintenance problem remains after using the [documentation index](INDEX.md) and [audio guide map](audio-guide-map.md). If moving a page becomes necessary, preserve old URLs with a small forwarding stub, update every tracked inbound link, retain unique historical material, and re-run CI. Do not move files and alter kernel/install scripts in the same PR.

No documents, historical artifacts, or system configuration are deleted by this decision.
