# Audio driver packaging (experimental preparation)

**Do not run the recovered `source/install.sh` or `source/dkms.sh` on a working MacBook.** They are not safe CachyOS installers. We are packaging a reproducible CS4208 driver, but a public, one-command installation is not ready.

## Evidence recovered from the working MacBook8,1

- CachyOS kernel `7.2.9-2-cachyos`; DKMS `macbook12-audio/0.1` also installed for the LTS kernel.
- Three patched modules are interdependent: `snd-hda-intel`, `snd-hda-codec-cs420x`, and `snd-hda-codec-generic`. A CRC mismatch can cause the generic codec to bind first and leave the speaker silent.
- `/etc/modprobe.d/mb81-singlecmd.conf` enables `single_cmd=1`, `power_save=0` and `softdep snd_hda_intel pre: snd_hda_codec_cs420x`.
- WirePlumber exposes a four-channel TDM output as `MacBook_Speaker_Raw`; this is the preferred working sink. Bass/voice response remains under investigation.

## Why installation is still blocked

1. The original root installer depends on files absent from the collected snapshot: `efi_recover.py`, `mb81-resume-recover.service` and `mb81-jack-switch.service`. Some support scripts are present, but a complete recovery procedure cannot yet be distributed.
2. The original scripts use Ubuntu `update-initramfs`, not CachyOS's `mkinitcpio`. DKMS and module-load ordering must be integrated and verified before reboot.
3. The build helper downloads an upstream kernel tarball without verifying a pinned checksum. A matching kernel source and ABI checks are needed for every CachyOS kernel.
4. The original DKMS remove script deletes state files directly and can remove modules not owned by the installer. Reversible removal must use DKMS's own restoration mechanisms and verify the original modules.
5. Kernel-derived source is GPL-2.0-or-later, and the local snapshot includes third-party reverse-engineered codec data. Review original provenance, license notices and private data before putting source in a public repository.

## Safe things to run now

Run a **read-only preflight** as your ordinary user, not with sudo:

```bash
cd ~/git/macbook8.1
git pull
bash scripts/audio-preflight.sh
```

If you have your **own** `macbook81-audio-details.tar.gz` from `collect-audio-details.sh`, you may stage known source files locally:

```bash
python3 scripts/stage-audio-source.py /path/to/macbook81-audio-details.tar.gz ./local-audio-stage
```

The staging program extracts only the 18 expected source/config files, writes SHA-256 hashes and a DO-NOT-INSTALL warning, and excludes the collector's report and legacy root installer. It never calls DKMS, sudo, mkinitcpio or modifies system audio. **Do not publish the staged folder yet.**

## Release acceptance checks

- License and upstream credit review, plus a clean reproducible source patch series.
- Builds for all three modules for tested CachyOS kernel versions, including symbol-version linkage validation.
- Correct `mkinitcpio` integration, reboot-safe load ordering, non-destructive rollback.
- Verified speaker, headphone, suspend/resume, kernel upgrade, uninstall and reinstall on at least one clean test installation.
- No equalizer preset by default; keep working `MacBook_Speaker_Raw` sound.
