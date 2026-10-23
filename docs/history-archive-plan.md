# Historical-document review and archive plan (2026-10-23)

**Planning only.** No documents are moved or deleted. Existing paths remain valid. This review examined five historical/recovery documents and their section structure and relative references; it is not a full paragraph-by-paragraph duplicate or link-anchor audit.

| Document | Unique evidence worth preserving | Current disposition |
|---|---|---|
| `continuation-checkpoint.md` | Original macOS-vs-CachyOS acoustic comparisons, phone/digital captures, routing tests, source identity, test failures, camera and power handoffs | **Archive candidate** only after a content-preserving map and backlink checks; current directions can be superseded |
| `speaker-sound-diagnosis.md` | Early four-channel mapping, EQ filter values, polarity/cancellation hypotheses and safe experiment history | **Archive candidate**; preserve numerical details and unsuccessful outcomes |
| `audio-support-recovery.md` | Hash-checked recovery of three original support files and safety issues | **Keep historical reference**, possible archive later; essential packaging provenance |
| `kernel-update-regression-2026-10-22.md` | Exact built-in DMA symbol change and real keyboard/trackpad restoration on 7.3.0-2 | **Keep in place**; still actionable for diagnosing kernel-specific breakage |
| `audio-update-recovery.md` | Confirmed 7.3.0-2 DKMS repair and speaker playback, source archive naming regression | **Keep canonical**, not an archive candidate |

## Proposed archive procedure (not executed)

1. Establish authoritative active entry points: [documentation index](INDEX.md), [audio guide map](audio-guide-map.md), [kernel update playbook](kernel-update-playbook.md), [audio recovery](audio-update-recovery.md), and [installation matrix](installation-matrix.md).
2. Inventory all inbound Markdown links, including heading anchors, from README and every tracked document/script. Record links in a reviewable mapping before moving files.
3. For each archive candidate, compare every section with current documentation. Retain original dates, checksums, measurements, negative tests and source attribution verbatim where important.
4. First add a warning banner to older pages, linking to current instructions. Prefer this to moving files immediately; links from external users may be impossible to discover.
5. If a move becomes justified, add a short stub at the original path pointing to the new archived location, and update all tracked internal links in the same PR. Confirm relative links and anchors.
6. Never rewrite or purge Git history just to tidy documentation. Any genuine sensitive-data finding requires a separate security response and explicit review.
7. Rerun offline CI and review the diff. Do not include executable, systemd, EFI, DKMS or Limine changes in archive PRs.

## Issues observed while reviewing

- `continuation-checkpoint.md` begins with a dated “start here next time” experiment. That historical directive should not outrank newer recovery or D+ service guidance.
- `speaker-sound-diagnosis.md` says bass was unresolved as of October 17; keep it as a date-stamped observation, not the only current sound-quality status.
- The detailed kernel regression is still useful despite its date because the DMA symbol is build-dependent. Do not archive away the last known recovery reasoning.
- `audio-update-recovery.md` contains a heading with literal backslash-n sequences embedded in a long section line. **Formatting cleanup candidate only**, to be done in a separate minimal diff with verification; do not modify instructions accidentally.

## Decision

**Zero deletions. Zero file moves.** Add historical/status banners next after checking links; postpone physical `docs/history/` relocation until full reference audit and signoff. Phase 1 local checkout and full-history secrets scan remain outstanding.
