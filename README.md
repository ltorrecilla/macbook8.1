# CachyOS MacBook8,1 fixes

Experimental hardware support for the 12-inch MacBook (Early 2015). This project is not yet a complete one-command hardware installer.

## Fix tracker

**Latest repository update: 2026-10-22.** **Working** means the owner confirmed that behavior on the original MacBook8,1. **Open** means a resolution is not yet confirmed. Installer availability and reboot, suspend/resume, kernel-update, and other-machine validation are tracked separately.

| Fix / area | Current result on the owner's MacBook | Repository support | Next action |
|---|---|---|---|
| CPU frequency limit | **Working:** initial frequency cap confirmed. | [Installer, checker, and removal helper](docs/cpu-frequency-limit.md). | Verify the cap after reboot, suspend/resume, and a kernel update. A frequency cap is not a temperature guarantee. |
| Camera capture | **Working in `mpv`:** moving image, reported `848x588` at 30 fps. | [Camera guide and helpers](docs/camera.md); new wrappers have simulated tests, but no physical installation test yet. | Validate a fresh wrapper installation and reboot/resume/update behavior; the existing manual setup needs only the diagnostic check. |
| Camera discovery in other apps | **Open:** another, unnamed camera app reports no devices. | [Application discovery checks](docs/camera.md#application-discovery-still-open). | Record the app name/version and installation source; close `mpv`, retry, then inspect the recorded V4L2/PipeWire/device-user diagnostics. |
| Audio playback | **Recovered on 7.3.0-2:** owner confirmed speaker playback sounds good following DKMS rebuild; CS4208 Speaker device 2 and MacBook_Speaker_Raw were visible. Earlier playback on 7.2.11 confirmed; | [Latest recovery findings](docs/audio-update-recovery.md); existing three-module driver. | Keep the recovered configuration unchanged while resuming EQ work. |
| Audio after kernel updates | **7.3.0-2 regression diagnosed:** preflight falsely requested linux-7.3.0.tar.xz (404); kernel.org archive is linux-7.3.tar.xz. Source URL fix committed; both kernels passed on-disk verification, Raw sink returned and speaker playback was owner-confirmed. | [Recovery/check helper](scripts/repair-audio.py) and [guide](docs/audio-update-recovery.md); 28 simulated tests. | Run the read-only check now. The new wrapper still needs a real MacBook recovery/update-cycle test. |
| Audio sound quality | **Working prototype / still open:** owner prefers D+ Clarity v4 to Raw and D v3; Big Sur remains slightly clearer/louder. | [D+ v4 service and listening results](docs/dplus-service.md), [Issue #1](https://github.com/ltorrecilla/macbook8.1/issues/1). | Preserve approved v4 and separately verify loudness, not more blind EQ boosts. |
| D+ login service | **Manual start and playback owner-confirmed; login autostart untested.** | [Opt-in enable/disable/rollback guide](docs/dplus-service.md). | Test a full logout/login with Raw remaining default; validate crash and suspend/resume cleanup. |
| Reusable audio installer | **Open:** sources and support files recovered; public installation is not validated. | [Packaging plan](docs/audio-packaging.md), [Issue #2](https://github.com/ltorrecilla/macbook8.1/issues/2). | Complete provenance/license review, offline source preparation, safe rollback, and clean-install/reboot/resume/update validation. The recovery wrapper is not a fresh installer. |
| Keyboard and trackpad | **Working again on 7.3.0-2:** prior built-in dw_dmac_pci blacklist symbol changed from __437_139 to __442_139; after updating Limine blacklist, owner confirmed both recovered. | Reported result recorded here; no validated reusable installer. | Document the exact procedure and verify persistence without treating per-kernel symbols as portable. |
| Bluetooth | **Working:** owner confirmed pairing after the ACPI/DSDT workaround. | Reported result recorded here; no validated reusable installer. | Document a machine-appropriate procedure and verify reboot/resume behavior. |
| Battery reporting | **Open:** reported charge state and percentage disagree. | No confirmed fix published. | Continue diagnosis of the contradictory battery readings. |
| Suspend and hibernation | **Experimental:** ordinary `s2idle` suspend resumes normally, with battery drain. Hibernation remains untested. | [Guarded preparation helper and guide](docs/hibernation.md) for the owner's recorded installation. | Rerun the corrected read-only preflight; successful preparation and the first hibernation/restore test have not been reported. |
| Limine boot-usage warning | **Open:** an unused boot directory of approximately 83 MiB was identified; cleanup is not confirmed. | [Hibernation preparation helper](docs/hibernation.md) can archive, verify, and remove that exact directory. | Confirm cleanup and resulting free space, then check whether the warning is resolved. |

When a result changes, update this table and its linked guide or checkpoint with the date, kernel, what was actually tested, and the next action. Mark persistence or another-machine compatibility verified only after recording that test. A published helper or passing simulated test does not by itself close a hardware issue.

## Continue the investigations

**Start with the [latest audio recovery and EQ handoff](docs/audio-update-recovery.md), updated 2026-10-20 after the owner confirmed recovery.** It supplements the earlier [continuation checkpoint](docs/continuation-checkpoint.md), which preserves the acoustic/routing analyses and other hardware investigations.

Audio next step: [full upstream MacBook8,1 EQ and source comparison](docs/audio-upstream-comparison.md). The original live EQ was tried and Raw was preferred; what remains untested is the **controlled offline, level-managed full-profile comparison through the same Raw sink**. Channel duplication mainly increased recorded volume, not bass balance. Keep the working driver and `MacBook_Speaker_Raw` unchanged.

Sound quality: [Issue #1](https://github.com/ltorrecilla/macbook8.1/issues/1). Reversible audio packaging: [Issue #2](https://github.com/ltorrecilla/macbook8.1/issues/2). The checkpoint preserves the completed work and next steps for these separate tasks.

## D+ Clarity v4 speaker processing (optional)

The owner confirmed the manually started D+ v4 per-user service sounds much closer to macOS than Raw. Its engine is **not yet a complete reproducible GitHub release**. If you already installed and manually tested the prototype, enable login autostart using `systemctl --user enable macbook81-dplus.service`; the service does not become the system default and Raw remains the fallback. **Do not enable until the manual test works.** See [D+ v4 setup, checks, limitations and rollback](docs/dplus-service.md). No boot-time service or mandatory audio-package change is added.

## Pre-reboot kernel compatibility check (read-only)\n\nRun `python3 scripts/check-kernel-update.py` **after each CachyOS update and before rebooting**. It checks installed kernel module paths and whether the available DMA initcall symbol matches `/etc/default/limine`. If future-kernel symbol data is unavailable it reports **SPI UNVERIFIED** rather than claiming safety. It does not install anything, modify boot parameters, or validate audio playback. See [7.3.0 kernel regression and prevention](docs/kernel-update-regression-2026-10-22.md).\n\n## Audio recovery after an update (existing installations only)

After updating this checkout, check installed kernels without changing anything:

```sh
python3 scripts/repair-audio.py --check
```

If an update leaves a missing audio build, finish the update, connect to the internet, and run:

```sh
sudo python3 scripts/repair-audio.py --repair
```

The helper detects installed kernel images (including a new kernel before reboot), checks matching headers and the existing three-module source, selects the target compiler, checks exact source access, builds missing audio modules, verifies them, and regenerates Limine boot images. It does not change EQ/Raw routing, install prerequisites, reset firmware, reload hardware, or reboot. **Read the [recovery guide and limitations](docs/audio-update-recovery.md) first. The wrapper has simulated tests, not a physical hardware-validation result.**

No automatic boot-time service is enabled. Kernel-source downloads and future driver/API changes can still fail; this is a repeatable recovery command, not a promise that every future kernel works.

## CPU frequency limit (tested on one MacBook8,1)

The optional CPU limiter reduces the maximum requested CPU frequency; it does **not** guarantee a maximum temperature or change thermal protection.

```bash
git clone https://github.com/ltorrecilla/macbook8.1.git
cd macbook8.1
sudo bash scripts/install-cpu-limit.sh 1600
bash scripts/check-cpu-limit.sh
```

Try 1300 (cooler/slower), 1600 (balanced default), or 2000 MHz (more headroom). Check again after reboot and suspend/resume: the latter is not yet automated. Remove with `sudo bash scripts/uninstall-cpu-limit.sh`. See [CPU details](docs/cpu-frequency-limit.md).

## Camera (live capture verified; app discovery still open)

The owner confirmed a moving image in `mpv` on MacBook8,1 with CachyOS `7.2.9-2-cachyos`, upstream `facetimehd` release `0.7.2`, firmware `5.60.0`, and sensor calibration `1675_01XX.dat`. The reported mode was `848x588` at 30 fps. An unnamed camera app still reports no devices, so general application compatibility is **not yet confirmed**.

If the camera already works in `mpv`, check the existing installation without reinstalling:

```sh
bash scripts/check-camera.sh
```

For a new installation, follow [the camera guide](docs/camera.md) to install prerequisites and matching kernel headers, then run `bash scripts/install-camera.sh` as your ordinary user. The optional installer pins upstream revisions, uses DKMS, and checks driver ownership and firmware hashes. The hardware result came from the preceding manual procedure; these new wrappers still need a physical installation test. Reboot, suspend/resume, kernel updates, and browser/Flatpak use have not been verified. The guide also explains the unresolved app discovery checks and removal of a wrapper-owned installation.

## Hibernation (experimental; specific to the owner's installation)

Ordinary `s2idle` suspend resumes normally on the owner's MacBook8,1, but the battery drains during sleep. The optional [hibernation guide](docs/hibernation.md) documents preparation for longer breaks, including a 10 GiB Btrfs swapfile and systemd's EFI resume mechanism. The helper checks the recorded kernel, machine ID, filesystem UUID, and Limine boot layout; it is not a general MacBook installer.

Start with the read-only check:

```sh
sudo python3 scripts/macbook81-hibernate-prepare.py --check
```

The first published helper stopped during preflight because it used unsupported `swapon` options. That reader is now corrected, but the owner has **not yet reported a successful corrected preflight, preparation run, or hibernation/restore test**. Follow the guide for the guarded preparation and separate first test. Preparation does not initiate hibernation or change the normal suspend/lid action.

## Audio (fresh installation not available yet)

The owner's MacBook8,1 has patched CS4208/HDA DKMS modules and a four-channel `MacBook_Speaker_Raw` PipeWire sink. Bass quality is still being investigated. The local driver source, configuration and previously missing support files have been recovered; a reproducible public installer has not been validated. The recovery helper above is only for an already-registered installation. See the [latest audio findings](docs/audio-update-recovery.md) and [earlier checkpoint](docs/continuation-checkpoint.md) before repeating diagnostics. New contributors can use `bash scripts/collect-audio-evidence.sh` or `bash scripts/collect-audio-details.sh`, then inspect the produced report/archive for private data before sharing. See [Audio details](docs/audio.md).

## Other fixes

Keyboard/trackpad and Bluetooth work on the original laptop, but universal installers have **not** been validated. The tracker above also records the unresolved battery, hibernation, and boot-warning tasks. Do not copy per-kernel `initcall_blacklist` arguments or ACPI DSDT binary files to other machines without validation.

Original scripts and documentation are MIT-licensed. Linux kernel-derived future code must preserve upstream licenses and credits.

## Audio installer development (read-only preparation)

The working CS4208 driver snapshot and its support files have been recovered, but **public installation is not yet safe**. It replaces three kernel HDA modules. The legacy installer assumes Ubuntu initramfs tooling and includes unvalidated low-level recovery and cleanup behavior. Do not run its old install/removal scripts on a working CachyOS installation.

Check your current system without changing it:

```bash
bash scripts/audio-preflight.sh
```

Stage the 18 known source/config files from **your own** collector archive without installing:

```bash
python3 scripts/stage-audio-source.py /path/to/macbook81-audio-details.tar.gz ./local-audio-stage
```

Read [the detailed audio packaging plan](docs/audio-packaging.md) before sharing any staged kernel source. Automated tests can run using `python3 -m unittest discover -s tests -p 'test_stage_audio_source.py'`.

### Recovered audio support files (October 2026)

The missing codec recovery and suspend/headphone systemd service files have now been collected; their installed and source copies match. See [support-file analysis](docs/audio-support-recovery.md) and [offline archive audit](scripts/audit-audio-bundles.py). **The audio installation procedure is still blocked** by unsafe legacy DKMS cleanup, Ubuntu-only initramfs handling, and untested low-level recovery/rollback. Do not run the recovered legacy installers. Progress is tracked in [Issue #2](https://github.com/ltorrecilla/macbook8.1/issues/2).
