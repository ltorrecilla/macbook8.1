# Upstream MacBook8,1 SPI PIO fix — evaluation track

Status as of 2026-10-23: **candidate only; not installed or tested on this owner's CachyOS machine. Upstream merge/inclusion in CachyOS is unconfirmed.** Preserve the working DMA initcall blacklist until a separate test build has passed.

## Upstream development

Shih-Yuan Lee submitted the Linux SPI patch series **v17 (2026-09-30)**:
- [v17 cover letter and full thread](https://lore.landau.one/lkml/20260930160629.1822-1-fourdollars%40debian.org/T/)
- [v17 patch 6/6: disable DMA and runtime autosuspend specifically for Apple MacBook8,1](https://lists.openwall.net/linux-kernel/2026/09/30/2141)
- [Original kernel bug 108331](https://bugzilla.kernel.org/show_bug.cgi?id=108331)

The proposed quirk belongs in `drivers/spi/spi-pxa2xx-pci.c` for the Intel LPSS SPI controller `00:15.4` (PCI 8086:9ce6), scoped by the MacBook8,1 DMI identifier. It avoids DMA channel allocation and uses PIO. It also avoids normal runtime autosuspend on this machine to reduce input-latency/key-loss issues. The companion DMA controller is at `00:15.0` (8086:9ce0).

**Why it may be better:** unlike the current `initcall_blacklist=...` workaround, it does not depend on unstable compiler-generated initcall names, and is scoped to the affected SPI controller rather than suppressing initialization of a shared DMA driver. This is a proposed design advantage, **not a confirmed result on our installation**.

Earlier v16 received maintainer questions requesting evidence on DMA configuration and transfer timeouts. Do not treat v17 as accepted merely because it was submitted. Check the current upstream status and CachyOS patch queue before testing.

## Current proven workaround (do not remove yet)

On `7.3.0-2-cachyos`, `CONFIG_DW_DMAC_PCI=y`. Loading the built-in `dw_dmac_pci` resulted in `applespi` SPI transfer timeouts (`-110`) and both input devices failing. Booting with the matching initcall symbol blacklisted restored the keyboard/trackpad. The initcall name changed between 7.2.x (`__437_139`) and 7.3.0-2 (`__442_139`). See [regression report](kernel-update-regression-2026-10-22.md). This is the only owner-verified recovery currently.

## Safe experimental test plan

1. Check whether the v17 quirk or a successor has been merged and whether CachyOS already carries it. Verify kernel tree revision and patch dependencies, not simply a version number.
2. Review the complete series and its maintainer discussion; patch 6/6 may depend on earlier patches. Record source URLs, revision, hashes, and kernel build configuration.
3. **Do not patch/replace the working `linux-cachyos` package in place.** Build a distinct test kernel package/release with its own initramfs, modules directory and Limine entry. Retain a verified bootable fallback plus an external keyboard.
4. Test input in the isolated build **without the old blacklist only on that test entry**. Do not remove the current workaround from the normal Limine configuration until the new fix is validated. Verify logs, `lspci -nnk`, keyboard/trackpad, cold and warm boots, normal runtime input, and suspend/resume.
5. Expect the custom three-module CS4208 DKMS audio package to need a separate build for the test kernel. Test audio separately after input is reliable, including CS4208 Speaker device 2 and MacBook_Speaker_Raw.
6. If successful, contribute precise before/after reproduction data, logs and tested kernel/patch commit to the upstream mailing-list thread and request a CachyOS backport when appropriate. If unsuccessful, select the old kernel in Limine and keep its known-working boot parameters.

**No auto-apply script or Pacman hook should install this patch yet.** No performance, battery, suspend, or audio claims follow from a successful keyboard test. Keep documentation and tests available for a future controlled update.
