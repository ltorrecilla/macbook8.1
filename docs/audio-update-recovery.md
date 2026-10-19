# Audio after kernel updates: recovery and latest findings

Updated **2026-10-20**, following the owner's confirmation that audio works again after the recovery targeting **7.2.11-1-cachyos**. The failed build log was dated October 19 and identified DKMS **3.4.4**. A complete post-recovery diagnostic dump was not supplied, so do not infer new PipeWire/WirePlumber versions or additional hardware-test results.

This page supplements the [continuation checkpoint](continuation-checkpoint.md). For update recovery and the latest EQ handoff, use this page when older wording differs.

## Three different update failures

| Evidence from the owner's logs | Conclusion | Reported recovery |
|---|---|---|
| Running `7.2.9-2-cachyos`, but audio DKMS installed only for `6.18.55-2-cachyos-lts`; stock HDA modules and no PCH speaker PCM | The running kernel lacked the patched audio build. The preceding SMC reset was not evidence that files or EQ were erased. | A matching driver build was needed for the kernel being booted. |
| Kernel and headers matched; `CONFIG_CC_IS_CLANG=y`; GCC rejected Clang flags | Wrong compiler environment inside the nested PRE_BUILD scripts | Sound worked after building with `LLVM=1 CC=clang LD=ld.lld`, checking all three modules and regenerating Limine boot images. |
| For `7.2.11-1-cachyos`, kernel.org connections failed for IPv4 and IPv6 with `Network is unreachable`; then `apt-get: command not found` | Source retrieval failed before compilation. The Ubuntu fallback misleadingly treated connection failure as evidence that the release did not exist. | Owner confirmed playback again after the source-access check and targeted recovery procedure. |

These are results from one MacBook8,1, not compatibility guarantees. The last failure does not establish source absence, a compiler error, or incompatibility with 7.2.11. It also does not establish why networking was unavailable at that moment. Do not install `apt-get`, substitute `pacman` in the fallback, or force IPv4 as though only IPv6 failed.

The [reviewed source downloader](https://github.com/omnidecker/macbook8.1-speaker-driver/blob/e4134fb272ba3be29aa71ad7aa6eae8b0ebddf1a/install.cirrus.driver.sh) contains that fallback. Its source download is an additional requirement beyond kernel headers. The [DKMS recipe](https://github.com/omnidecker/macbook8.1-speaker-driver/blob/e4134fb272ba3be29aa71ad7aa6eae8b0ebddf1a/dkms.conf) builds three modules inside PRE_BUILD.

## One command for an existing installation

The new [repair helper](../scripts/repair-audio.py) wraps the successful manual workflow. **Its 28 simulated tests pass, but this wrapper has not yet been run on the owner's laptop.** It is experimental, not the still-unreleased fresh-install audio package.

Update the existing repository checkout normally:

```sh
cd /home/luis/git/macbook8.1 && git pull --ff-only
```

Use your actual checkout path if different. If Git refuses the pull, stop and preserve local work; do not use `reset --hard` or `clean`.

### While sound works: check without modifying anything

```sh
python3 scripts/repair-audio.py --check
```

No sudo is needed. No downloads, builds, boot-image changes, service restarts, or configuration writes occur in check mode. Exit 0 means selected on-disk module checks passed; exit 2 means a build is needed; exit 1 indicates a guard/error. Passing does not verify live playback, firmware state, mixer settings, or an existing initramfs's contents.

### After a kernel update: before rebooting

Finish the package update and all its hooks first. Stay connected to the internet. Do not start another package update or DKMS operation while recovery runs.

```sh
sudo python3 scripts/repair-audio.py --repair
```

There is no kernel version to edit. By default it considers all installed, package-owned stable CachyOS kernel images, not merely `uname -r`. Before reboot, the running kernel may still be the old one, and an update may already have removed its old files. Directories containing only leftover DKMS files are ignored. Unsupported release formats and missing headers cause a stop rather than a silent substitution.

An optional exact target can limit the operation:

```sh
sudo python3 scripts/repair-audio.py --repair --kernel 7.2.11-1-cachyos
```

That version is an example from this recovery, not a command to reuse unchanged for later releases.

### What repair mode does

The helper restricts itself to MacBook8,1, x86_64, CachyOS and package-owned kernel images. It checks DKMS status plus all three module paths and vermagic. If DKMS claims an installation but the files disagree, it stops instead of force-replacing them.

For missing builds, it validates the already-registered `macbook12-audio/0.1` three-module source, matching headers, symbol file and compiler tools. It supplies LLVM for Clang-built targets and GCC for GCC-built targets, without modifying the source's existing compiler-selection patch. All target headers/tools are checked before any installation begins.

It checks reachability of each exact kernel source archive, then runs targeted `dkms install` commands without `--force`, `remove`, or `--all`. Existing installations for other kernels and their original-module backups are not removed. No other DKMS package is targeted. After verifying the installed modules, it runs `limine-mkinitcpio`; failed builds or verification prevent that step.

Repair mode also refreshes the boot images when modules already pass, allowing a retry after a previous run installed modules but failed during boot-image generation. A boot-image failure remains an error, not success. Limine's wrapper manages installed boot images and entries; this helper does not edit kernel command-line parameters or choose a default kernel.

It does not run the full legacy installer, install prerequisites, change Raw/EQ defaults or volumes, restart PipeWire, unload/reload hardware modules, modify firmware/codec registers, or initiate a shutdown. Keep the existing source checkout available: it is still required by DKMS.

### Finish and verify

Only after **ON-DISK REPAIR COMPLETE**, save your work and perform an ordinary full shutdown. Start normally and boot the intended checked kernel. Do not repeat an SMC reset.

After login, compare with the established working setup:

```sh
uname -r
aplay -l
amixer -c PCH cget name='IEC958 Default PCM Playback Switch'
wpctl status -n
```

Expect `CS4208 Speaker` as PCH device 2 and the sharing switch `off`. Keep the preferred `MacBook_Speaker_Raw` route and test at modest volume. No automated speaker playback test is performed. Repeating the mixer command cannot repair a missing speaker device when the patched driver is absent.

## Logs, failures, and fallback

Attempts reaching the source-access/build stage keep private local logs under:

```text
/var/log/macbook81-audio-recovery/<timestamp-and-unique-suffix>/
```

The helper prints the path. A failed DKMS build's current make.log is copied there before another attempt can overwrite it. Inspect logs before sharing; no logs, recordings, source archives, or personal dumps are automatically published.

If all on-disk modules pass but playback remains silent, do not rebuild repeatedly. Check the booted kernel, loaded modules/initramfs, mixer and existing audio routing. The helper deliberately does not guess at amplifier or firmware recovery.

If a build fails, stop before booting that unprepared kernel. Retain a known-working installed kernel and its modules as a fallback. Rolling updates may remove old kernel files: an old directory or DKMS status entry alone does not guarantee a bootable fallback.

A failed multi-kernel repair is not transactional: earlier targets may already be installed. It does not undo successful targets automatically. Review the log, correct the reported issue and rerun to finish. Do not delete DKMS directories or use the unsafe legacy removal script as recovery.

This wrapper is not installed as a service. There is no automatic job to disable just to stop using it.

## What is not automatic yet

Existing DKMS hooks still handle routine builds, and the existing driver requests automatic installation. This helper is a repeatable recovery/pre-reboot command, not a new unattended updater or boot-time build service. Its default selects the current installed kernels without requiring the user to rewrite version strings.

The prior automatic-Clang source adjustment was proposed to persist compiler selection. A complete successful unattended update cycle using that patch has not been demonstrated here. The wrapper supplies the compiler environment independently whenever it is run.

**The network dependency remains.** The reachability test is not an archive signature/checksum verification or an offline cache. It cannot guarantee that connectivity remains available inside DKMS. The wrapper reuses the already-trusted registered recipe, including its downloader: if that later fails, the old Ubuntu fallback can still appear in the build log. The wrapper does not install prerequisites; do not install apt-get to accommodate the legacy fallback. Do not disable global DKMS isolation or network protections based on an unverified theory about this failure.

The durable packaging task in [Issue #2](https://github.com/ltorrecilla/macbook8.1/issues/2) is to acquire and verify exact source beforehand, cache it for an offline build, fail clearly without Ubuntu fallback, preserve backups, and validate compiler/API changes plus post-update playback. No unattended network-dependent root build has been enabled at login or boot. No helper can guarantee compatibility with every future kernel API change.

## EQ: resume without repeating completed tests

Audio recovery and sound quality remain separate. The owner prefers `MacBook_Speaker_Raw`; keep the working driver, mixer rule and customized/live EQ configuration unchanged.

The original live processed output was tried and sounded worse than Raw. Earlier statements that the full EQ was never installed/tried must not erase that listening result. What remains untested is a controlled, level-managed offline comparison of the complete reviewed profile through the same Raw output and identical channel mapping. Earlier small-band changes and the subsequent zero-gain live configuration are not that controlled comparison.

The completed channel-duplication experiment mainly changed recorded loudness (about 7 dB), with only a small relative bass change. It is not a demonstrated bass fix. These measurement summaries are preserved from the checkpoint, not newly recomputed here. Existing phone recordings, monitor capture, and analyses remain the evidence; no new recording is needed just to resume.

Next input: the existing **macbook81-raw-monitor-v2.wav**. Its saved analysis is available, but the current conversation workspace could not reopen the audio bytes. Reattach the existing file rather than record again. The timestamped **macbook81-macos-audio-reference-*.txt** is useful if it was created, but has not been supplied/analyzed here. It is not a complete macOS DSP/register dump and is not required for the offline listening comparison.

The earlier request for `ffmpeg`, `pactl`, `parecord`, and `pacat` came from a Linux-style workflow, not a prerequisite for native macOS metadata. That report uses the built-in `sw_vers`, `system_profiler`, and `ioreg` tools. Do not install extra software or repeat finished acoustic tests for this handoff.

Follow the [full-profile comparison plan](audio-upstream-comparison.md): prepare baseline/full-profile versions of the same excerpt, keep channel mapping identical, reserve/check headroom and match file loudness, then play through Raw. No new audition files, calibrated EQ preset, or validated speaker-protection setting are released by this update. Sound quality remains [Issue #1](https://github.com/ltorrecilla/macbook8.1/issues/1).

## Validation and references

**28 simulated unit tests pass.** They cover read-only behavior, new-kernel detection, preservation of other kernels/configuration, compiler selection, wrong model/distribution, active package lock, missing/mismatched headers, network/build/boot failures, source identity, package ownership, module-file checks, exact source URL selection, rejection of release candidates, predictable locale and failure-log preservation. These mocks do not build real modules or test speakers.

```sh
python3 -m unittest discover -s tests -p 'test_repair_audio.py' -v
```

Manual procedure: owner-confirmed recovery targeting 7.2.11-1-cachyos. New wrapper on physical hardware: not yet tested. New unattended update cycle, suspend/resume, microphone/headphones, and another-machine validation: not newly verified.

Primary references: [DKMS actions and per-kernel installs](https://man.archlinux.org/man/dkms.8.en), [LLVM environment for nested builds](https://docs.kernel.org/kbuild/llvm.html), [CachyOS boot-image management](https://wiki.cachyos.org/configuration/boot_manager_configuration/). This helper redistributes no driver source; existing source-attribution and licensing work remains in the packaging issue.
