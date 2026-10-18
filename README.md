# CachyOS MacBook8,1 fixes

Experimental hardware support for the 12-inch MacBook (Early 2015). This project is not yet a complete one-command hardware installer.

## Fix tracker

**Latest recorded results: 2026-10-18.** **Working** means the owner confirmed that behavior on the original MacBook8,1. **Open** means a resolution is not yet confirmed. Installer availability and reboot, suspend/resume, kernel-update, and other-machine validation are tracked separately.

| Fix / area | Current result on the owner's MacBook | Repository support | Next action |
|---|---|---|---|
| CPU frequency limit | **Working:** initial frequency cap confirmed. | [Installer, checker, and removal helper](docs/cpu-frequency-limit.md). | Verify the cap after reboot, suspend/resume, and a kernel update. A frequency cap is not a temperature guarantee. |
| Camera capture | **Working in `mpv`:** moving image, reported `848x588` at 30 fps. | [Camera guide and helpers](docs/camera.md); new wrappers have simulated tests, but no physical installation test yet. | Validate a fresh wrapper installation and reboot/resume/update behavior; the existing manual setup needs only the diagnostic check. |
| Camera discovery in other apps | **Open:** another, unnamed camera app reports no devices. | [Application discovery checks](docs/camera.md#application-discovery-still-open). | Record the app name/version and installation source; close `mpv`, retry, then inspect the recorded V4L2/PipeWire/device-user diagnostics. |
| Audio playback | **Working:** patched HDA/CS4208 modules and `MacBook_Speaker_Raw` produce sound. | [Working baseline and evidence](docs/continuation-checkpoint.md#1-last-established-baseline); diagnostic, staging, and audit helpers. | Use this working baseline for the sound-quality and installer work below. |
| Audio sound quality | **Open:** bass/tonal balance still differs from macOS. | [Full EQ comparison plan](docs/audio-upstream-comparison.md), [Issue #1](https://github.com/ltorrecilla/macbook8.1/issues/1). | Compare the complete upstream EQ offline with controlled gain; the earlier recordings and routing tests are already documented. |
| Reusable audio installer | **Open:** sources and support files recovered; public installation is not validated. | [Packaging plan](docs/audio-packaging.md), [Issue #2](https://github.com/ltorrecilla/macbook8.1/issues/2). | Complete provenance/license review, CachyOS integration, safe rollback, and clean-install/reboot/resume/update validation. |
| Keyboard and trackpad | **Working:** owner confirmed operation after the boot-parameter workaround. | Reported result recorded here; no validated reusable installer. | Document the exact procedure and verify persistence without treating per-kernel symbols as portable. |
| Bluetooth | **Working:** owner confirmed pairing after the ACPI/DSDT workaround. | Reported result recorded here; no validated reusable installer. | Document a machine-appropriate procedure and verify reboot/resume behavior. |
| Battery reporting | **Open:** reported charge state and percentage disagree. | No confirmed fix published. | Continue diagnosis of the contradictory battery readings. |
| Brother DCP-9020CDW printing | **Open:** last CUPS output showed no configured print destinations. | No confirmed fix published. | Complete printer-queue setup and confirm a physical test page. |
| Custom keyboard shortcuts | **Open:** input-remapper still required manual launch/application each session. | No confirmed persistent solution published. | Establish and verify mappings that apply automatically at login. |
| Limine boot-usage warning | **Open:** boot-usage limit warning reported with no snapshot entries. | No confirmed fix published. | Inspect boot filesystem usage and snapshot configuration, then confirm a targeted correction. |

When a result changes, update this table and its linked guide or checkpoint with the date, kernel, what was actually tested, and the next action. Mark persistence or another-machine compatibility verified only after recording that test. A published helper or passing simulated test does not by itself close a hardware issue.

## Continue the investigations

**[Continuation checkpoint — 2026-10-18](docs/continuation-checkpoint.md)** records the working baseline, completed listening/recording tests, recovery lessons, remaining installer work, and the exact next experiment.

Audio next step: [full upstream MacBook8,1 EQ and source comparison](docs/audio-upstream-comparison.md). The full profile is **not yet tested or installed**. Channel duplication mainly increased recorded volume, not bass balance. Keep the working driver and `MacBook_Speaker_Raw` unchanged; the next comparison is planned as offline-rendered audio with controlled gain, not a driver replacement.

Sound quality: [Issue #1](https://github.com/ltorrecilla/macbook8.1/issues/1). Reversible audio packaging: [Issue #2](https://github.com/ltorrecilla/macbook8.1/issues/2). The checkpoint preserves the completed work and next steps for these separate tasks.

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

## Audio (not installable yet)

The owner's MacBook8,1 has patched CS4208/HDA DKMS modules and a four-channel `MacBook_Speaker_Raw` PipeWire sink. Bass quality is still being investigated. The local driver source, configuration and previously missing support files have been recovered; a reproducible public installer has not been validated. See the [current checkpoint](docs/continuation-checkpoint.md) before repeating diagnostics. New contributors can use `bash scripts/collect-audio-evidence.sh` or `bash scripts/collect-audio-details.sh`, then inspect the produced report/archive for private data before sharing. See [Audio details](docs/audio.md).

## Other fixes

Keyboard/trackpad and Bluetooth work on the original laptop, but universal installers have **not** been validated. The tracker above also records the unresolved battery, printing, shortcut, and boot-warning tasks. Do not copy per-kernel `initcall_blacklist` arguments or ACPI DSDT binary files to other machines without validation.

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
