# CachyOS MacBook8,1 fixes

Experimental hardware support for the 12-inch MacBook (Early 2015). This project is not yet a complete one-command hardware installer.

## CPU frequency limit (tested on one MacBook8,1)

The optional CPU limiter reduces the maximum requested CPU frequency; it does **not** guarantee a maximum temperature or change thermal protection.

```bash
git clone https://github.com/ltorrecilla/macbook8.1.git
cd macbook8.1
sudo bash scripts/install-cpu-limit.sh 1600
bash scripts/check-cpu-limit.sh
```

Try 1300 (cooler/slower), 1600 (balanced default), or 2000 MHz (more headroom). Check again after reboot and suspend/resume: the latter is not yet automated. Remove with `sudo bash scripts/uninstall-cpu-limit.sh`. See [CPU details](docs/cpu-frequency-limit.md).

## Audio (not installable yet)

The owner's MacBook8,1 has patched CS4208/HDA DKMS modules and a four-channel `MacBook_Speaker_Raw` PipeWire sink. Bass quality is still being investigated. We are collecting the exact local driver sources and speaker-channel configuration before publishing an installer. Run `bash scripts/collect-audio-evidence.sh` or `bash scripts/collect-audio-details.sh`, then inspect the produced report/archive for private data before sharing. See [Audio details](docs/audio.md).

## Other fixes

Keyboard/trackpad and Bluetooth work on the original laptop, but universal installers have **not** been validated. Battery reporting and printing remain unresolved. Do not copy per-kernel `initcall_blacklist` arguments or ACPI DSDT binary files to other machines without validation.

Original scripts and documentation are MIT-licensed. Linux kernel-derived future code must preserve upstream licenses and credits.

## Audio installer development (read-only preparation)

The working CS4208 driver snapshot has been recovered, but **public installation is not yet safe**. It replaces three kernel HDA modules, and the original installer is missing suspend/headphone support files and assumes Ubuntu initramfs tooling. Do not run its old install/removal scripts on a working CachyOS installation.

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
