# CachyOS on the 12-inch MacBook (Early 2015, MacBook8,1)

Experimental, hardware-specific fixes and diagnostics for CachyOS. **Not a complete one-command installer.** The original MacBook's working configuration is not a guarantee of compatibility with another laptop or kernel.

**[Documentation index](docs/INDEX.md)** · **[Installation and rollback matrix](docs/installation-matrix.md)** · **[Script reference](docs/script-reference.md)** · **[Kernel-update playbook](docs/kernel-update-playbook.md)**

## Hardware status

| Area | Evidence on original MacBook | Current guidance |
|---|---|---|
| Keyboard and trackpad | Working on CachyOS kernel 7.3.0-2 after a build-specific DMA workaround | [Kernel regression](docs/kernel-update-regression-2026-10-22.md), [upstream alternative research](docs/spi-upstream-pio-patch.md) |
| Audio output | Patched CS4208 speaker and Raw sink recovered on 7.3.0-2; fresh installation unverified | [Audio recovery](docs/audio-update-recovery.md) |
| Camera | Live image confirmed using mpv; desktop app discovery and wrapper fresh-install still open | [Camera guide](docs/camera.md) |
| CPU frequency limit | Initial cap confirmed; update/resume persistence and full rollback still under study | [CPU guide](docs/cpu-frequency-limit.md) |
| D+ speaker processing | Corrected native PipeWire D+ graph confirmed AUDIBLE with both tone and real 30-second music on MacBook8,1 (2026-10-25); preferred +1 dB profile preserved; normal-app routing, limiter parity, sleep recovery and automatic default remain unverified | [D+ status and tasks](docs/dplus-service.md), [Issue #39](https://github.com/ltorrecilla/macbook8.1/issues/39) |
| Bluetooth | Pairing worked after machine-specific ACPI/DSDT workaround; no reusable installer | No reusable installer |
| Battery reporting and sleep drain | Inconsistent charge readings and drain under s2idle; EC experiment not validated | [Sleep experiment](docs/sleep-battery-drain.md) |
| Hibernation | Preparation experimental; hardware restore not confirmed | [Hibernation guide](docs/hibernation.md) |

## Before a CachyOS kernel reboot

On the original MacBook, run these **read-only** checks from the repository root:

```bash
python3 scripts/check-kernel-update.py
python3 scripts/repair-audio.py --check
```

Review any **SPI NOT READY**, **SPI UNVERIFIED**, or audio module warnings before rebooting. The DesignWare DMA `initcall_blacklist` symbol can change between kernel builds. Do not copy historical Limine parameters blindly. See the [kernel-update playbook](docs/kernel-update-playbook.md).

## Installation and safety

Start with the [installation matrix](docs/installation-matrix.md). Camera and CPU scripts have limited installation/removal workflows, but physical fresh-install and rollback behavior still require validation. The audio repair script is **for an existing registered patched DKMS installation only**, not a fresh driver installer.

Do not run experimental hibernation preparation on an unreviewed installation. Preserve a known-good kernel and review rollback instructions before any privileged operation.

## Development and investigations

- [Script safety and side effects](docs/script-reference.md)
- [Maintenance and remaining work](docs/repository-cleanup-roadmap.md)
- [Phase 4 release-safety gates](docs/phase4-release-safety.md)
- [Audio source packaging and licensing blockers](docs/audio-packaging.md)
- [D+ development roadmap, verified results and remaining tasks](docs/dplus-service.md)

Offline GitHub Actions cover syntax, unit tests, and a heuristic documentation-link checker. **Passing CI does not verify actual MacBook hardware.**

This repository intentionally excludes printer customization and custom keyboard shortcuts. Original project material is MIT-licensed; upstream kernel-derived code and firmware have separate provenance/licensing requirements.
