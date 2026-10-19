# Continuation checkpoint — MacBook8,1 CachyOS

Saved 2026-10-18 at the owner's request to pause and continue later. Updated 2026-10-19 with hibernation compatibility and preparation progress. This records the October 2026 conversation, uploaded evidence, and completed analyses; it is not a new hardware test or release.

## Start here next time

**Next experiment: evaluate the complete speaker EQ from `thomas-shirley/macbook8.1-speaker-driver`, using an offline-rendered, gain-managed comparison through the existing raw output.** Read [the upstream comparison](audio-upstream-comparison.md) first. The complete preset has NOT been tested on this machine. No implementation or new playback file for that preset is included in this checkpoint.

Keep the working three-module driver and `MacBook_Speaker_Raw` unchanged. Do not install the generic leifliddy package over them, rerun the legacy installer, change codec registers, or turn the recording difference into a large bass boost.

No new recording or diagnostic collection is needed merely to resume. The owner has already done numerous listening tests and supplied two sets of acoustic recordings, a digital monitor capture, codec dumps, and source/support archives. Do not restart that sequence from scratch.

Suggested continuation prompt:

> Read docs/continuation-checkpoint.md and docs/audio-upstream-comparison.md. Continue with a non-invasive, headroom-managed comparison of the full upstream MacBook8,1 EQ profile. Keep the working driver and default raw sink unchanged. Use the recorded findings and do not repeat completed tests without a specific reason.

## 1. Last established baseline

These are observed/reported versions, not a claim that no later system update has occurred.

| Item | Last established state |
|---|---|
| Hardware | 12-inch Early 2015 MacBook, MacBook8,1; Intel Core M-5Y51; CS4208 |
| OS and kernel | CachyOS, `7.2.9-2-cachyos`; LTS `6.18.55-2-cachyos-lts` also installed |
| Audio stack | PipeWire 1.6.9; WirePlumber 0.5.18; desktop uses fish shell |
| Working DKMS package | `macbook12-audio/0.1`, reported installed for both kernels |
| Patched modules | `snd-hda-intel`, `snd-hda-codec-cs420x`, `snd-hda-codec-generic` |
| Local DKMS source | `/usr/local/src/macbook81-audio-repair`, found through the DKMS source symlink |
| Preferred playback | `MacBook_Speaker_Raw` (CS4208 Speaker), not the older EQ input |
| ALSA stream | `PCH` PCM device 2: S16_LE, 4 channels, 44100 Hz, MMAP_INTERLEAVED |
| Speaker codec route | Digital converter `0x0a` to enabled speaker pin `0x1d` |
| Existing driver options | `single_cmd=1 power_save=0`; `softdep snd_hda_intel pre: snd_hda_codec_cs420x` |
| CPU limiter | Published; owner confirmed initial operation. Reboot/resume/update persistence still needs explicit verification. |
| Other hardware | Keyboard/trackpad and Bluetooth previously reported working on the original machine; reusable installers not validated. Battery reporting remains unresolved in this record. |

The separate analog `Master` control is associated with converter `0x02`. Left and right were equal at raw value 80/127 (-23.5 dB). Lowering to raw 60 and restoring 80 produced no clear speaker-volume change. Do not mistake raw 80 for 80%, or set Master to maximum to solve this issue.

## 2. What has been tested

### Routing and format

- The kernel's active `hw_params` agreed with the four-channel/16-bit/44.1 kHz raw sink configuration. This does not prove four physical speaker components or correct codec slot mapping.
- An initial live PipeWire dump showed Firefox routed through `input.MacBook_Speaker` and then through the raw output. A later dump confirmed the default and Firefox links went directly to `MacBook_Speaker_Raw` after the application route was changed.
- The later Firefox stream originated as stereo but exposed four output ports. Its `channelmix.upmix-method` was `none`. Connected ports alone did not establish nonzero samples in all channels.
- All four logical channels were individually audible in tone tests. The final controlled 230 Hz results were: individual channels audible, in-phase FL+RL and FR+RR audible, opposite-phase pairs silent. Earlier inconsistent reports were followed by this more specific test. None establishes physical wiring polarity or proves four separate physical speakers.

### Small EQ experiments

The owner reported no clear improvement from +2.5 dB at 258 Hz, +4 dB at 185 Hz, or a same-raw-sink comparison with +3.5 dB at 210 Hz and -1.5 dB at 3 kHz. Some early raw/EQ tests were not level matched and included routing problems. Later offline same-sink tests also sounded similar. Treat the result as no clear improvement from those trials, not proof that all EQ is ineffective or that a particular macOS DSP stage is missing.

The captured local EQ had all peaking/shelf gains at zero and specified two high-pass stages at 134/137 Hz. The entire upstream profile described below was not evaluated in those trials.

## 3. Recording analyses already completed

The following values are preserved from the generated session reports; they were not recomputed as part of saving this checkpoint. They are relative measurements of recordings, not calibrated speaker SPL, amplifier gain, or inverse-EQ settings.

### Two MacBooks: macOS versus CachyOS

The owner has two machines of the same model, one on Big Sur and one on CachyOS. Phone, source audio, distance, placement, and settings were kept as consistent as the owner reasonably could. The owner explicitly confirmed this; do not request the same setup confirmation again.

Conditions: CachyOS raw output at 85% desktop volume; macOS at 50%. Slider percentages were not treated as equivalent gain scales. Recordings were captured on the same phone; automatic recorder processing is not independently characterized. Because there are two physical laptops, speaker condition remains a possible confounder.

A matching 10-second passage was analyzed. Recorded loudness was -26.6 LUFS for CachyOS and -33.1 LUFS for macOS. After matching 500–4000 Hz reference-band energy, CachyOS had approximately **19.55 dB less 150–300 Hz energy**. Five matching two-second sections showed a similar 19–20 dB relative deficit. The result supports the owner's tonal complaint but does not identify its cause. Do not apply a +20 dB bass boost.

### Digital raw-monitor capture

`macbook81-raw-monitor-v2.wav`: 44.1 kHz, four-channel float WAV, 1,937,408 frames per channel, duration 43.932154 seconds.

| Requested channel label | Whole-file RMS | Result |
|---|---:|---|
| FL | -20.2057 dBFS | Audio present |
| FR | -20.2127 dBFS | Audio present |
| RL | Exact zero | Every sample zero |
| RR | Exact zero | Every sample zero |

This is evidence about the monitor capture under its requested map, not a physical-speaker measurement. Capture/remapping behavior must not be conflated with codec/amp output.

### Routing-only A/B, recorded with the phone

The generated `macbook81-routing-ab.wav` used 10 seconds A = L,R,0,0; 2 seconds silence; 10 seconds B = L,R,L,R. The front samples were bit-identical. No EQ was added, and the owner supplied `compare-routing-ab.m4a` after playback through `paplay`.

Analysis aligned A near 0.7056 s and B near 12.7054 s in that phone file. B was about **6.95 dB louder in recorded RMS**, but only **1.18 dB higher in 150–300 Hz relative to a matched 500–4000 Hz reference**. Five sections gave roughly +0.22 to +2.05 dB relative bass differences.

**Conclusion: filling the extra channels mainly changed level; it did not substantially restore bass.** Do not publish permanent duplication as a confirmed sound-quality fix. This does not identify where the signals sum. Do not subtract numbers from separate acoustic sessions to derive an exact remaining correction.

## 4. Most recent lead: full upstream EQ and source provenance

See [audio-upstream-comparison.md](audio-upstream-comparison.md) for repository links, reviewed Git blob/tree IDs, the six-file identity comparison, and the full frequency/Q/gain table.

- The reviewed `leifliddy/macbook12-audio-driver` excludes MacBook8,1 and builds an overlapping codec replacement; it is not a supported drop-in update for this local three-module stack.
- Four checked files in the local archive match `thomas-shirley/macbook8.1-speaker-driver`; two playback/setup headers differ. Do not claim the whole local source tree is identical or newly original work.
- The model-specific project supplies a full EQ labelled by its author as `macOS layout100 EQ`. That origin has not been independently verified against the owner's Big Sur system.
- Unlike the captured local configuration, its profile includes +4 dB at 258 Hz, -10 dB at 875 Hz (Q 0.62), -3.5 dB at 1800 Hz, -5 dB at 3000 Hz, and other stages. It is not the small isolated boost already tested.
- Its preamp comment says +15 dB but the actual high-shelf gain is +10 dB. Blindly copying it into the live pipeline is not an acceptable test.

Source comments also describe EFI/boot-chime coefficient replay. This raises a possible normal-playback initialization question but does not establish that the coefficients are wrong or causing the deficit. Do not change GPIO/MMIO/register settings on that inference.

## 5. Exact next experiment — planned, not implemented or tested

1. Use the reviewed model-specific profile with its complete stage order, frequencies, Q values, and filter types. Verify the offline implementation against the intended biquad response rather than assuming similarly named filters are identical.
2. Render one permitted local speech/music excerpt into baseline and full-profile variants. Keep sample rate and channel mapping identical in both; do not confound EQ with duplication. Preserve the documented high-pass stages in the profile under test; do not describe them as validated speaker protection.
3. Work with floating-point intermediate audio, reserve headroom, inspect the resulting peaks, and lower both variants as necessary. Treat the positive upstream preamp as a gain-management detail, not a mandate to boost the laptop. Document deviations from the source chain explicitly.
4. Match file loudness with constant gain only, within the shared peak/headroom bound. Record method and limits; RMS or LUFS matching is not identical to acoustic/perceived loudness matching.
5. Play through the already-working raw sink using the verified Pulse-compatible route. Do not change the default sink, restart services, rewrite live configuration, install modules, or force an unsupported target.
6. Only consider a reversible optional preset if the complete profile produces a clear, repeatable benefit. Keep audio packaging independent from sound-quality acceptance.

The file `macbook81-macos-audio-reference.txt` was requested from the Big Sur laptop but has **not** been supplied. It would expose selected I/O Registry/system-profiler properties, not a complete codec or amplifier register trace. Collect it if needed to validate the claimed layout or investigate remaining differences; no extra action is required solely for this checkpoint.

## 6. Tool behavior and recovery lessons — avoid repeating failures

- `pw-play`/`pw-record` with the explicitly named raw target and no-fallback properties later failed with `defined target not found` on this setup. That is a connection failure, not a bass diagnosis.
- `parecord` using the explicitly listed `MacBook_Speaker_Raw.monitor` source succeeded; `paplay` using `MacBook_Speaker_Raw` succeeded for the four-channel routing test. Preserve explicit channel order and no-remix/no-remap behavior for comparisons.
- Setting `input.MacBook_Speaker` as the default from the audition script failed with `Not supported`. Earlier restore attempts also raced sink discovery. Restoration to the raw output subsequently succeeded according to the owner's output.
- Do not delete an audition backup just to bypass the guard. Preserve it until recovery succeeds. Avoid using the live-config-restarting audition method for the next experiment.
- A target's name being present as a label does not establish a successfully linked stream. A successful routing command also does not establish that EQ was applied.
- Output labels such as `CS4208 Speaker:playback_FL` are not shell commands. Keep example output separate from commands; the owner uses fish.
- CPU installer success and audio playback success are user reports, not proof that every published revision or clean-install/resume path was hardware-tested.

## 7. Installer work is a separate, still-open task

[Issue #2](https://github.com/ltorrecilla/macbook8.1/issues/2) tracks a reversible CachyOS installer. Source and all three previously missing support assets were recovered: `efi_recover.py`, `mb81-resume-recover.service`, and `mb81-jack-switch.service`. Do not request those files again as missing.

The recovered legacy scripts are not a safe general installer. Remaining work includes license/provenance review, comparison of the locally modified headers, verified kernel source and symbol linkage for all three modules, CachyOS/mkinitcpio integration, preservation of DKMS original-module backups, opt-in low-level recovery, rollback, and clean installation/reboot/resume/kernel-update testing. Existing audit/staging unit tests are not substitutes for those hardware tests. No new code execution or tests were performed for the original audio-only checkpoint.

## 8. Evidence inventory and privacy

The following are conversation/local artifacts, **not files uploaded into this public repository by this checkpoint**. Retain originals locally. If a future session cannot access an attachment, reuse the saved file rather than collecting another recording unnecessarily.

| Artifact | Role |
|---|---|
| `macbook81-audio-details.tar.gz` | Recovered driver/source and local configuration |
| `macbook81-audio-support.tar.gz` | Recovery helper and systemd service copies |
| `macbook81-codec-live.txt`, `macbook81-codec-live(1).txt` | Codec snapshots, whose instantaneous activity differs |
| `macbook81-pipewire-live.json`, `macbook81-pipewire-live(1).json` | Before/after application route snapshots |
| `cachyos.m4a`, `macos.m4a` | Two-machine phone comparison |
| `macbook81-raw-monitor-v2.wav` | Four-channel software monitor capture |
| `macbook81-routing-ab.wav`, `compare-routing-ab.m4a` | Routing-only stimulus and phone response |
| `recording_comparison_report.md`, `raw_monitor_report.md`, `routing_ab_report.md` | Full session measurement reports |
| `macbook81-upstream-comparison.md` | Prior report preserved in repo form as `audio-upstream-comparison.md` |

Identity checks recorded by the prior analyses:

- Audio-details archive SHA-256: `e2f2d2cf48896e5fa453617d964ee3bd4a1c9bc1d137ce0d11825de6958d00b0`.
- Raw-monitor WAV SHA-256: `8f27fd0f74278bd514341d1ce34af5511265957967c170c43ff4519192e714d5`.
- Routing A/B stimulus SHA-256: `5a0f7462f8e46d8d9cf7f5a72519d29eef53221db631965c4d58d17b9b285ae1`.
- Routing phone capture SHA-256: `e7fb91390eb3be4183364e0828bc7a3aafce8da4aabb42ad33a0a8db5538198c`.

This checkpoint publishes summarized findings and public-source references only. It does not publish recordings, unreviewed source archives, personal session identifiers, full system dumps, or firmware. Earlier chronological docs may contain superseded 'missing file' or 'next test' statements; use this checkpoint and Issues #1/#2 to resume.

## 9. Camera follow-up — 2026-10-18

The owner reported `MacBook8,1`, kernel `7.2.9-2-cachyos`, matching `linux-cachyos` / `linux-cachyos-headers` packages at `7.2.9-2`, DKMS `3.4.3-1`, and Broadcom camera PCI ID `14e4:1570`. Initially, the `facetimehd` module, firmware directory, and video device class were missing.

After the manual installation of upstream `facetimehd` release `0.7.2` (its native DKMS version is `0.7.0.1`) and firmware `5.60.0` with sensor calibration files including `1675_01XX.dat`, the owner confirmed a **normal moving image** in `mpv av://v4l2:/dev/video0`. The reported mode was `848x588` at 30 fps. Mesa/pixel-conversion and shutdown buffer messages appeared in that successful run.

**Remaining camera task:** another, unnamed camera app reports no devices. Its exact name/version and installation method are unknown. Close `mpv`, fully reopen the app, then obtain `v4l2-ctl --list-devices`, `wpctl status`, and `fuser -v /dev/video0` if it still fails. These outputs have not yet been supplied. Do not mark PipeWire, browser, or Flatpak camera compatibility as solved, and do not change the working audio stack to guess at an app-discovery fix.

See [the camera guide](camera.md) and the optional `scripts/install-camera.sh`, `scripts/check-camera.sh`, and `scripts/uninstall-camera.sh` helpers. They pin the working upstream driver/firmware combination and preserve unrelated installations. The wrappers are newly added and have not been run on the physical laptop; the existing manual installation needs only the diagnostic check. Reboot, suspend/resume, and rebuilding through a kernel update remain unverified. This camera addition does not change the audio continuation plan above.

## 10. Suspend and hibernation — 2026-10-19

The owner confirmed that ordinary `s2idle` suspend resumes normally, with battery drain during sleep. The running kernel is `7.2.9-2-cachyos`; `/sys/power/mem_sleep` reports `[s2idle] deep`, and hibernation is exposed in `/sys/power/state`. Only zram swap was active. No successful hibernation or restoration has been reported.

The review of `juicecultus/macbook-sleep` led to an adapted preparation helper for this installation. The upstream installer has different bootloader and SPI-module assumptions. See [the hibernation guide](hibernation.md) and `scripts/macbook81-hibernate-prepare.py`. This helper guards the exact recorded kernel, machine ID, root filesystem UUID, and Limine boot layout; it is not validated for another installation or a later kernel.

The planned preparation adds a 10 GiB swapfile in a separate Btrfs `@swap` subvolume, retains zram, and selects `HibernateMode=shutdown`. It checks the active initramfs for systemd's EFI resume support and preserves the existing boot images, boot parameters, and normal suspend/lid behavior. It stops before initiating hibernation. Automatic suspend-then-hibernate remains a later step after a successful manual restore test.

The first helper **stopped during read-only preflight** because `swapon` rejected its unsupported `--json` option; the reader also used unsupported `--output`. The corrected helper uses the documented raw output format and has been delivered. **A successful corrected preflight, `--apply` run, and hardware hibernation/restore test are all still unconfirmed.** The next step is `sudo python3 scripts/macbook81-hibernate-prepare.py --check`, then the guide's preparation and separate test only if the checks pass. A passing simulated test is not evidence of physical restoration.

Boot diagnostics identified approximately 83 MiB under the old machine-ID directory as unreferenced by the sole Limine configuration. Both current kernel entries use the current machine-ID directory. The helper can archive and verify the old directory before removing it; neither that cleanup nor resolution of the boot-usage warning has been confirmed. Preserve the current boot images and backups. This addition does not change the audio continuation plan above.
