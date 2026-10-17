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
