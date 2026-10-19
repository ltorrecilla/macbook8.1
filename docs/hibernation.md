# Hibernation preparation on MacBook8,1

**Status recorded 2026-10-19: experimental and specific to the owner's current installation.** Ordinary `s2idle` suspend resumes normally, but consumes battery while asleep. A preparation helper is available; successful preparation and hibernation/restoration have **not** been reported on the MacBook.

The first helper stopped during read-only preflight because it passed unsupported `--json` and `--output` options to `swapon`. The published version includes the correction:

```sh
swapon --show=NAME,TYPE,SIZE,USED,PRIO --bytes --noheadings --raw
```

The corrected preflight has not yet been confirmed on the laptop. That earlier failure occurred before boot cleanup, swap creation, or configuration changes.

## Scope and recorded starting point

[The helper](../scripts/macbook81-hibernate-prepare.py) has hard-coded guards for the reviewed machine ID, filesystem UUID, exact kernel, and boot layout. It is not a general installer for another MacBook or a changed installation. Do not remove these guards merely to make a check pass.

| Area | Reviewed configuration |
|---|---|
| Hardware and kernel | MacBook8,1; `7.2.9-2-cachyos` |
| Current suspend mode | `[s2idle] deep`; `mem_sleep_default=s2idle` and the existing DesignWare DMA initcall blacklist |
| Kernel power support | `freeze mem disk`; hibernation exposes both `platform` and `shutdown` |
| Root storage | Single-device Btrfs; root subvolume `@`; approximately 192 GiB free when inspected |
| Memory and swap | Approximately 7.7 GiB RAM; only `/dev/zram0`, priority 100 |
| Boot layout | Limine, `/boot/limine.conf`; current kernel and LTS entries use `/boot/f1d9c71eb83b40baa8a21f233674ca7b/` |
| Boot space | Approximately 24 MiB free; the unreferenced `/boot/e236028073f84f21be594c22fdbfe6f9/` directory occupies approximately 83 MiB |
| Initramfs configuration | Uses the mkinitcpio `systemd` hook; the helper checks the actual active image for the resume binary, generator, and service |

The approach uses systemd's `HibernateLocation` EFI variable to locate the saved image on the next boot. Preflight requires systemd 255 or newer, writable EFI-variable support, kernel hibernation support, and the resume components in the active initramfs. See the [systemd resume-generator documentation](https://www.freedesktop.org/software/systemd/man/latest/systemd-hibernate-resume-generator.html).

The upstream [juicecultus/macbook-sleep installer](https://github.com/juicecultus/macbook-sleep/blob/069c38709d0ef9ac06fc6bcff5a021c0ffecaf8b/install.sh) was reviewed but is not installed by this helper. Its bootloader handling does not cover Limine, and its SPI unload list omits `spi_pxa2xx_pci`, which is loaded on the owner's laptop and holds the SPI core. The preparation here keeps the existing boot images and driver workarounds in use.

## What preparation changes

`--check` is the default and performs read-only checks. `--apply` repeats those checks, then:

1. Backs up the existing Limine configuration, Limine defaults, and fstab under a dated, root-only directory in `/var/backups/macbook81-hibernate/`.
2. Copies the one unreferenced old boot directory into that backup, verifies its contents, and syncs the copy before removing the original. Active kernel/initramfs hashes are checked against Limine before and after cleanup. Recovered space is expected to be about 83 MiB; actual cleanup is still unconfirmed.
3. Creates a top-level Btrfs `@swap` subvolume mounted at `/swap`, then a 10 GiB `/swap/swapfile` using `btrfs filesystem mkswapfile`. It validates the file's mapping with `btrfs inspect-internal map-swapfile -r`.
4. Activates disk swap at priority 10, alongside zram at priority 100, and adds marked mount/swap entries to `/etc/fstab`.
5. Creates `/etc/systemd/sleep.conf.d/70-macbook81-hibernate.conf` with only:

   ```ini
   [Sleep]
   HibernateMode=shutdown
   ```

6. Records checkpoints and configuration hashes, reloads systemd, and reports `CanHibernate` eligibility.

The helper stops before any sleep action. It does not rebuild an initramfs, edit the kernel command line, unload drivers, or configure lid actions. Existing normal suspend and audio-recovery configuration are retained. `HibernateMode` selects how the kernel completes hibernation; see [systemd-sleep.conf](https://www.freedesktop.org/software/systemd/man/latest/systemd-sleep.conf.html).

The swapfile's separate subvolume keeps it outside snapshots of the root subvolume. Btrfs requires appropriate allocation and mapping for swapfiles; the helper uses the filesystem's own creation and mapping tools. See [Btrfs swapfile requirements](https://btrfs.readthedocs.io/en/latest/Swapfile.html).

## Run on the reviewed installation

From the repository root:

```sh
sudo python3 scripts/macbook81-hibernate-prepare.py --check
```

If it reports **Preflight passed**, prepare the separate manual test:

```sh
sudo python3 scripts/macbook81-hibernate-prepare.py --apply
```

If either command prints `STOP`, keep the exact output and inspect the printed backup/checkpoint location if one was created. Do not continue to hibernation after a failed preparation.

`--apply` expects the reviewed starting state. After successful or partial preparation, another `--apply` can intentionally reject the existing swap or configuration. Use the read-only status view instead:

```sh
sudo python3 scripts/macbook81-hibernate-prepare.py --status
```

## First hardware test

Only after **Preparation complete**:

1. Save all work, and leave an ordinary application and terminal open so the restored session is recognizable.
2. Run `systemctl hibernate` and wait for power-off.
3. Turn the MacBook on with its power button and select **linux-cachyos, kernel `7.2.9-2-cachyos`**. Do not update or change the kernel between saving and restoring the session.
4. Verify that the same session returns. A new login session alone is not evidence of restoration.
5. Check keyboard, trackpad, speakers, Wi-Fi, Bluetooth, and camera. Record the date, kernel, command result, and any device regression.

If restoration repeatedly hangs, a one-time `noresume` kernel parameter in Limine's entry editor can skip restoration and allow a fresh boot. This abandons the saved hibernation session; saved files remain the recovery baseline. See the [resume-generator command-line options](https://www.freedesktop.org/software/systemd/man/latest/systemd-hibernate-resume-generator.html).

Once manual hibernation is confirmed, the next step is a separate suspend-then-hibernate configuration with an explicit delay. That would keep quick resume for short breaks and power off after longer sleeps. It has not been configured or tested here.

## Recovery after a preparation error

Recovery is checkpointed and manual. A failure can leave completed stages in place; the helper does not attempt a blanket rollback.

The printed backup directory contains `state.json`, `preparation.log`, `RECOVERY.txt`, and the original configuration copies. Review these before changing anything. In particular:

- An active swapfile must be successfully deactivated before unmounting its filesystem. If `swapoff` fails, keep the swapfile and filesystem intact.
- Restore the saved fstab only when the current file matches the recorded intended hash. If it has subsequent edits, review and remove only this helper's marked block.
- Remove the helper's sleep drop-in only when its hash matches the record, then run `systemctl daemon-reload` after configuration changes.
- Do not automatically delete the swapfile or `@swap`. The archived old boot files can remain in the backup; restoring them consumes boot-partition space and is not required by the current Limine entries.

## Regression tests

Run the focused swap-reader tests without root:

```sh
python3 -B -m unittest discover -s tests -p 'test_hibernate_swaps.py'
```

These tests cover the supported command syntax, numeric conversion including signed priorities, empty output, malformed rows, and command failures. They use mocked command output and do not perform mounts, swap activation, or sleep. Passing them does not validate hibernation on the MacBook.

The command format is documented by [util-linux swapon](https://man7.org/linux/man-pages/man8/swapon.8.html). The existing helper's archive and configuration failure paths were also tested in isolated temporary directories during its initial preparation; target-machine execution remains pending.
