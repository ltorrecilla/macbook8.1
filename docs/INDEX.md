# MacBook8,1 documentation

For the **12-inch Early 2015 MacBook on CachyOS**. These are hardware-specific results, not a validated all-in-one installer. Return to the [README and tested status](../README.md).

## Use and recovery

| Area | Guide |
|---|---|
| Keyboard, trackpad, kernel updates | [Kernel-update playbook](kernel-update-playbook.md) and [recorded 7.3.0 regression](kernel-update-regression-2026-10-22.md) |
| Camera | [FaceTime HD camera](camera.md) |
| CPU limiting | [CPU cap](cpu-frequency-limit.md) |
| Audio | [Recovery for an existing driver](audio-update-recovery.md), [future driver packaging](audio-packaging.md) |
| Sound processing | [Experimental D+ service](dplus-service.md) |
| Battery and sleep | [Unverified EC-wakeup experiment](sleep-battery-drain.md) |
| Hibernation | [Experimental, machine-specific preparation](hibernation.md) |

**Before a kernel reboot:** run `python3 scripts/check-kernel-update.py` and `python3 scripts/repair-audio.py --check`. Review warnings before reboot. Do not copy DMA blacklist symbols from an older kernel.

## Details and research

- [Installation, verification, and rollback](installation-matrix.md)
- [Script reference and side effects](script-reference.md)
- [SPI upstream alternative](spi-upstream-pio-patch.md) — untested on this machine
- [Original audio channel measurements](speaker-sound-diagnosis.md), [listening experiments](continuation-checkpoint.md), [upstream comparison](audio-upstream-comparison.md)
- [Recovered audio support files](audio-support-recovery.md) — provenance, not a fresh installer

## Maintainers

- [Release blockers and physical test checklist](phase4-release-safety.md)
- [Maintenance rules and remaining work](repository-cleanup-roadmap.md)
- [Offline CI workflow](../.github/workflows/offline-validation.yml)

**Status language matters:** tested on this MacBook does not mean tested after every update or on another machine. Keep drivers, Limine boot settings, and normal CPU/audio configuration unchanged when editing documentation. Historical audit records remain in Git history instead of cluttering current guides.
