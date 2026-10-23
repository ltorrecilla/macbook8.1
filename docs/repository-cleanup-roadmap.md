# Maintenance rules and open work

This is a **hardware-specific research toolkit**, not a general installer. The [README](../README.md) is the source of truth for tested results; the [documentation index](INDEX.md) links to supported procedures.

## Keep the repository small

- One practical guide per subsystem; detailed original experiments remain only where they add unique technical evidence.
- Don't add planning notes, duplicate audit reports, temporary logs, or prototype code to the active tree. Git history preserves old revisions.
- Keep `scripts/` entry-point paths stable; tests and services refer to them. Rename only for demonstrated benefit.
- Put instructions near the script they concern. Describe supported model/kernel, preflight, side effects, verification, rollback and whether testing was simulated or performed on hardware.
- Avoid hard-coded personal machine IDs in reusable tooling, and review every evidence archive before sharing.
- Printer configuration and custom keyboard shortcuts remain out of scope.

## Outstanding work (not documentation cleanup)

1. **Hardware:** measure `s2idle` battery drain before/after an optional EC-wakeup experiment; confirm battery readings from `macsmc-battery`, not the former `BAT0` path.
2. **Kernel updates:** verify DMA compatibility and patched HDA audio after each upgrade and keep a known-good boot entry.
3. **Audio and camera:** complete D+ latency investigation, fresh audio licensing/packaging, camera application discovery and wrapper validation.
4. **Power/CPU:** confirm cap persistence and real installer rollback, then test hibernation/restore only under controlled conditions.
5. **Release:** review provenance and private data, verify rollback on real hardware, maintain tested-kernel matrix, and report upstream findings where reproducible.

**Documentation completion gate:** concise README/index, no broken tracked links, automated CI green, and no obsolete maintenance files duplicated in the current tree. Physical hardware validation remains a *separate* release gate.
