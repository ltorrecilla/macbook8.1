# CachyOS 7.3.0-2 MacBook8,1 regression and pre-reboot safeguards

Recorded 2026-10-22 from the owner's MacBook8,1. This is a case report, **not** a universal fix.

## Confirmed evidence

- Keyboard/trackpad failed after updating from the previously working 7.2.x kernel to `7.3.0-2-cachyos`.
- The DesignWare DMA PCI driver is **built in**: `CONFIG_DW_DMAC_PCI=y`, `modinfo -F filename dw_dmac_pci` returns `(builtin)`, and `lspci -nnk -s 00:15.0` showed `Kernel driver in use: dw_dmac_pci`.
- `applespi` repeatedly logged SPI timeouts (`-110`).
- Limine *preserved* the boot arguments, but the old initcall name `__initstub__kmod_dw_dmac_pci__437_139_dw_pci_driver_init6` did not match the new kernel's observed `__initstub__kmod_dw_dmac_pci__442_139_dw_pci_driver_init6`.
- After adding the latter to `initcall_blacklist` in `/etc/default/limine`, regenerating boot images and rebooting, the owner confirmed keyboard and trackpad both work. **This is a build-specific workaround, not a stable symbol/API**.
- Camera still works on 7.3.0-2.
- Audio recovery `--check` showed the LTS kernel `6.18.55-2-cachyos-lts` had all three patched DKMS modules, but 7.3.0-2 needed a build. The running kernel resolved `snd-hda-codec-cs420x` to the stock module under `kernel/sound/hda/codecs/cirrus/` rather than `updates/dkms/`. `MacBook_Speaker_Raw` was missing; only `input.MacBook_Speaker` and built-in ALSA output were visible.
- `scripts/repair-audio.py --repair` initially stopped on kernel.org HTTP 404 for `linux-7.3.0.tar.xz`. The registered `install.cirrus.driver.sh` already tries both full and shortened versions. The recovery wrapper's preflight needed the same `.0` normalization. That fix is now in the repository.
- After applying the URL fix, both installed kernels passed the audio on-disk verification; ALSA exposed CS4208 Speaker device 2, PipeWire showed MacBook_Speaker_Raw as configured default, and the owner confirmed the speakers sound good. The exact D+ service startup state and resilience across a further kernel update remain unverified.

## Before every future kernel reboot

1. Finish the CachyOS update. Keep at least one **verified bootable** alternate kernel and corresponding patched audio modules; verify its Limine entry rather than assuming an old DKMS directory is bootable.
2. Run `python3 scripts/check-kernel-update.py`. It is read-only; an SPI **UNVERIFIED** or **NOT READY** result requires review, not an automated rewrite.
3. Run `python3 scripts/repair-audio.py --check`; if modules are missing, review `docs/audio-update-recovery.md` and run its guarded `sudo ... --repair` process while still booted into the working kernel. Do not run two DKMS builds in parallel.
4. Confirm `/etc/default/limine` contains the verified symbol(s) for the **target** kernel and that the intended Limine entry uses the generated parameters. Do not blindly copy a symbol from the running kernel onto a different kernel.
5. Only then reboot into the target kernel, with an external keyboard available, and verify `lspci -nnk -s 00:15.0`, Apple SPI behavior, `modinfo -n snd-hda-codec-cs420x`, `aplay -l`, the Raw sink and actual speaker playback. The on-disk checks cannot establish live speaker behavior; owner confirmed playback on 7.3.0-2 after recovery.

If a new kernel fails the SPI compatibility check and its symbol is not available from reliable symbol data, **stay on a known-working kernel**. There is no safe universally portable blacklist string for this built-in driver. Longer-term work should test a stable hardware-specific kernel patch/quirk (and upstream support) rather than generating fragile boot parameters automatically.

## Scope and constraints

The checker does not change `/etc/default/limine`, install drivers, choose a kernel or run at package transaction time. The audio recovery wrapper does not restore PipeWire routes, speaker firmware state or user services. A future improvement is an **opt-in** post-upgrade Pacman notification and an offline verified kernel-source cache; neither should silently reboot or rewrite a working boot setup. Treat package hooks as diagnostics only until physical update-cycle tests pass.

This issue is unrelated to resetting the SMC. A previous SMC reset reportedly helped battery charging, but the kernel-specific SPI and audio failures have distinct evidence.
