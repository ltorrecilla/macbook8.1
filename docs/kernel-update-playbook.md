# CachyOS kernel updates — MacBook8,1 safety playbook

**Documentation only.** This summarizes the existing guides; it does not authorize automatic boot edits or promise future-kernel compatibility. Read [the 7.3.0 regression investigation](kernel-update-regression-2026-10-22.md) and [audio update recovery](audio-update-recovery.md) for technical details.

## Before rebooting after a package update

The Early 2015 MacBook8,1 currently relies on a **kernel-build-specific DesignWare DMA initcall blacklist** to keep Apple SPI keyboard and trackpad usable. Limine retaining a boot argument does not guarantee its symbol still matches a new kernel. The patched CS4208 speaker driver is an independent DKMS dependency.

On the MacBook, from this repository checkout, run the existing **read-only** checks:

```bash
python3 scripts/check-kernel-update.py
python3 scripts/repair-audio.py --check
```

Check the installed-kernel results, not merely `uname -r` (which shows the *running* kernel). If any new kernel is reported SPI NOT READY, SPI UNVERIFIED, audio missing, or another mismatch, **stop and investigate before reboot**. Do not copy a previously observed initcall symbol into a new kernel without verifying the exact installed build. Keep a known-good boot/recovery path.

## Recovery decisions

| Symptom | First response | What not to do |
|---|---|---|
| Keyboard/trackpad unavailable after reboot | Use a known-good kernel/alternate input and read the [DMA regression case report](kernel-update-regression-2026-10-22.md) | Do not blindly blacklist new symbols or replace Limine parameters |
| Speaker silent / Raw sink missing after update | Run `python3 scripts/repair-audio.py --check`; consult [audio recovery guide](audio-update-recovery.md) | Do not use `--repair` as a new-machine installer or replace all HDA modules manually |
| Camera app cannot find camera | Check [camera diagnostic guide](camera.md) and distinguish device capture from app discovery | Do not reinstall firmware because one application lacks a device |
| CPU frequency limit appears lost | Read [CPU ceiling guide](cpu-frequency-limit.md) and run `bash scripts/check-cpu-limit.sh` | Do not assume the cap is a hardware temperature limit |
| New suspend/battery behavior | Record `/sys/power/mem_sleep` and review [EC sleep experiment](sleep-battery-drain.md) | Do not silently switch to `deep` or enable untested EC/Limine changes |

## Mutating operations are separate decisions

- `sudo python3 scripts/repair-audio.py --repair` changes registered DKMS kernel modules and regenerates Limine boot images. Use only after following the specific recovery guide, reviewing prerequisites and retaining a recovery kernel.
- Editing `/etc/default/limine` and regenerating boot images to resolve DMA symbols affects boot input compatibility. Existing symbols from 7.2.x and 7.3.0-2 are historical observations, **not a universal parameter list**.
- Hibernation preparation is experimental and machine-bound; do not run it as part of normal kernel update preparation.
- The upstream SPI PIO patch is a candidate to replace fragile blacklist behavior, but was **not hardware-validated** here.

## Verification after successful reboot

Confirm the expected kernel and effective boot command line, working keyboard and trackpad, audio playback via Raw, camera capture when needed, CPU cap if enabled, and at least one ordinary suspend/resume cycle when safe. Document failures with kernel release, date, test evidence and rollback. Avoid treating simulated CI tests as hardware confirmation.

Return to the [documentation index](INDEX.md).