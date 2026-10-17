# MacBook8,1 speaker bass and channel routing (2026-10-17)

**Status: internal speakers work, but bass is thinner than macOS; not yet solved.** Avoid changing working kernel/DKMS modules just to tune audio.

## Findings from the owner's audio source archive

- Kernel `7.2.9-2-cachyos`, DKMS `macbook12-audio/0.1` with patched `snd-hda-intel`, `snd-hda-codec-cs420x` and `snd-hda-codec-generic`.
- CS4208 speaker PCM is `hw:1,2`, exposed by WirePlumber as `MacBook_Speaker_Raw`: four-channel S16LE at 44100 Hz, logical positions `FL FR RL RR`.
- The optional `input.MacBook_Speaker` filter duplicates stereo left to FL/RL and right to FR/RR, and has two high-pass biquads near 135 Hz (134 Hz and 137 Hz, Q = 0.707) on each side. This attenuates bass in the **EQ** path, but doesn't establish why **raw** playback lacks bass.
- Despite a comment mentioning a 15 dB preamp, the EQ's actual high-shelf and peaking gains are all 0 dB.
- Driver header describes TDM slot offsets `[32,96,0,128]`. Logical channel positions alone do not confirm physical speakers or polarity.

## Safe, interactive test

From the repository root, as your normal desktop user:

```bash
git pull
python3 scripts/test-speaker-routing.py --self-test
python3 scripts/test-speaker-routing.py
```

Eight modest-volume tests play through the raw sink only: each channel separately at 490 Hz, then logical front/rear pairs in phase and opposite phase at 230 Hz. Note where each tone sounds and which pair sounds fuller. Stop for distortion/discomfort; this is a listening diagnostic, not a calibration or proof of wiring polarity. The test never changes default sinks, kernel drivers, audio config or system services and doesn't need sudo.

## Installer packaging is not yet safe

The source archive contains the DKMS build scripts and local code, but the original installer references several **absent** files: `efi_recover.py`, `mb81-resume-recover.service`, `mb81-jack-switch.service` and installer-root copies of the runtime PipeWire/WirePlumber/modprobe configs (live copies were captured separately). Also the installer uses Ubuntu's `update-initramfs`, rather than the CachyOS initramfs workflow. We must resolve those dependencies, license and attribution, recovery and uninstall behavior, and test a clean installation before publishing a hardware audio fix. Do not publish the captured source archive directly.
