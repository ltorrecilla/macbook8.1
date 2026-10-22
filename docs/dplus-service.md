# D+ Clarity v4 — optional per-user speaker processing

Updated 2026-10-23, recording the post-7.3.0 recovery service-state check. **Owner-confirmed:** the prototype's manual `python3 manage.py install`, `check`, `start` and application routing worked and sounded good. **Not yet confirmed:** enable-at-login, logout/login, suspend/resume, PipeWire restart, volume-key behavior, automatic restart cleanup, or installation on another machine.

> **BLOCKER — 2026-10-21:** Owner reports multi-second audio delay after pausing/resuming video through the D+ FFmpeg/parecord/pacat service. Manual sound quality approval does **not** establish A/V-sync or production readiness. **Do not enable at login or make D+ the default** until this is diagnosed and fixed. If enabled, run `systemctl --user disable --now macbook81-dplus.service` and restore `pactl set-default-sink MacBook_Speaker_Raw`. Do not adjust EQ or kernel driver to fix transport latency. Investigate queue/backpressure, stream cork/uncork behavior, and timestamps; retest pause/resume repeatedly with measured audio/video offset.

## Observation after the 7.3.0 kernel recovery

The owner confirmed that patched speaker playback and Raw routing work again. A subsequent `systemctl --user is-enabled macbook81-dplus.service` and `is-active` check returned `disabled` and `inactive`. Therefore **the good sound reported at that point does not prove the D+ user service was processing audio**. Starting, enabling, and successful login of that service have not been confirmed in a new diagnostic output. The existing pause/resume A/V-sync blocker remains in effect; do not silently enable D+ as part of a kernel recovery.

Check service state without changing it with `systemctl --user is-enabled macbook81-dplus.service; systemctl --user is-active macbook81-dplus.service`. Disabled/inactive is an expected possible outcome for this optional prototype and is not a kernel-update failure. Audio driver and Raw sink checks are independent.

## Architecture and provenance

MacBook8,1 uses the existing, separately maintained three-module `macbook12-audio/0.1` HDA/CS4208 DKMS driver and `MacBook_Speaker_Raw` four-channel PCM. D+ is *userspace audio processing*, not a new hardware driver. It creates a temporary stereo sink `MacBook_Speaker_D_Live`, captures that sink's monitor, processes with FFmpeg, and plays `L,R,0,0` into Raw. It does not replace, reinstall or modify the patched kernel modules.

The owner preferred D v3 to Raw, then preferred D+ Clarity v4 to D v3, and reported v4 very close to Big Sur: macOS slightly clearer and louder at the same displayed 50% setting. **Equal displayed volume percentages are not calibrated equal loudness.** D+ is not demonstrated to reproduce Apple's internal DSP. The macOS report identified AppleHDA layout 100, `DeviceEqID=65536`, stereo output at 44.1 kHz, but not the underlying DSP coefficients.

D v4 preserves D's **11 biquad stages**, approximately **+8.31 dB pre-limiter gain**, a limiter with **5 ms attack and 80 ms release** running with 176.4-kHz oversampling, and 44.1-kHz `L,R,0,0` output. The v4 change is a **+1 dB presence adjustment around 3 kHz**. This positive gain and limiter are not a physical speaker safety certification. Do not stack another preamp or blindly maximize Raw.

The user's approved engine was supplied separately in the working `macbook81-dplus-service-prototype.zip`, copied into `~/.local/share/macbook81-dplus/dplus-engine.py` by that prototype's installer. **That engine is not yet committed to this repository as a public ready-to-run release**: reproducible packaging and redistribution/validation remain to be completed. The repository documents the confirmed behavior and keeps the runtime code separate from the driver.

## Login autostart — SUSPENDED pending A/V synchronization fix

First stop the currently running manual test or leave it to be managed by the same systemd unit. Ensure Raw is the current system default:

```sh
pactl get-default-sink
systemctl --user --no-pager status macbook81-dplus.service
```

Expected default: `MacBook_Speaker_Raw`. Confirm the unit is the previously manually tested `macbook81-dplus.service`. Do **not** start a second v4 test alongside it.

**The following enable command is retained only as documentation of a future workflow. Do not execute it while the A/V-sync defect is open.**

To enable the existing, manually tested user service for future **logins**:

```sh
systemctl --user enable macbook81-dplus.service
systemctl --user is-enabled macbook81-dplus.service
```

This does **not** change the current default output or force an immediate restart. If it is stopped and Raw is selected, start it with:

```sh
systemctl --user start macbook81-dplus.service
```

Route a single application using KDE's per-app audio selector to **MacBook Speaker (D live test)**. The existing prototype does not change the global default and does not make ordinary volume keys control D's sink. Its guard **stops** if the global default becomes D. Never use KDE's global output selector to make D the default during this test phase.

**Next test:** log out and log in, confirm D reappears and Raw remains default:

```sh
systemctl --user is-enabled macbook81-dplus.service
systemctl --user is-active macbook81-dplus.service
pactl get-default-sink
pactl list short sinks
```

Then explicitly route just one application and listen at modest volume. The systemd unit requires the graphical user session's PipeWire/Pulse/WirePlumber services. It is **login autostart**, not a boot-time system service and not a guarantee of reliable operation after sleep or PipeWire restart.

## Troubleshooting

```sh
journalctl --user -b -u macbook81-dplus.service -n 100 --no-pager
systemctl --user --no-pager status macbook81-dplus.service
pactl list short sinks
pactl get-default-sink
```

If D fails, return to Raw using normal KDE output selection or `pactl set-default-sink MacBook_Speaker_Raw`. If the temporary D sink survives a failure, **do not unload unknown PipeWire modules**. Investigate ownership and service cleanup first.

Stop it for this session:

```sh
systemctl --user stop macbook81-dplus.service
```

Disable autostart **and** stop:

```sh
systemctl --user disable --now macbook81-dplus.service
```

For the previously downloaded prototype, its extracted folder also offers `python3 manage.py disable` and `python3 manage.py remove`. The latter checks for exact matching package files and can refuse removal if locally modified. Preserve those files rather than forcing deletion.

## Kernel updates remain a separate problem

D+ requires the kernel driver and Raw sink to work. Run the repository's read-only `python3 scripts/repair-audio.py --check` after updates, and see [audio-update-recovery.md](audio-update-recovery.md) for guarded repair. No D+ audio service can restore a missing kernel-specific DKMS build. This service must not change Limine boot parameters, speaker GPIOs, HDA modules, or `IEC958` mixer workaround.

## Release gates

- [x] Owner confirmed manual startup, playback, and acceptable sound quality on one MacBook8,1.
- [ ] **BLOCKER: correct multi-second audio delay on pause/resume, verify with repeated video tests.**
- [ ] Verify actual login autostart and clean logout.
- [ ] Validate service stop/cleanup, crash/restart, headphone handling and PipeWire restarts.
- [ ] Test suspend/resume and at least one kernel-update cycle.
- [ ] Reconcile per-app routing, system volume keys and default-sink preference without unsafe automatic takeover.
- [ ] Publish audited and pinned D+ engine source with documented credits/license and tests; test a new-machine installation.
- [ ] Re-evaluate slight macOS clarity/loudness difference separately from reliable deployment.

No claim of a universal installer, verified speaker protection, or exact Apple DSP equivalence is made.
