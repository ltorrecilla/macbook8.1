# MacBook8,1 D+ native user service — opt-in experiment

**Status, 2026-10-25:** the checked-in renderer uses the **exact source bytes** of the first two-stage-copy PipeWire graph that the MacBook owner verified with a tone and a real 30-second music track. The owner has now confirmed an **audible D+ tone through the manually started user service**; service stop/cleanup, long-running behavior and sleep recovery are **not yet verified on that MacBook**. It is a trial, not an enabled default speaker or exact D+ v4 reproduction.

## Safety and scope

- Uses the owner's existing privately held `dplus-v4-reference-profile.json` **locally**, validates its original reference SHA, then generates `~/.config/macbook81-dplus-native/dplus.conf`. Nothing uploads the JSON or hard-codes its 11 private EQ rows into public code.
- The graph preserves the original +1.0 dB at 3 kHz, 48-kHz magnitude corrections, LSP Limiter Stereo (reduced gain 0.35), 0.45 clamp, `L,R,0,0`, and the physical `MacBook_Speaker_Raw` target. This is **lower-gain experimental EQ**, not the approved exact +8.31-dB/FFmpeg limiter chain or certified speaker protection.
- The installed unit `macbook81-dplus-native.service` is a **user** service, distinct from the obsolete `macbook81-dplus.service`. It is neither started nor enabled on installation; it deliberately uses `Restart=no` and stops if Raw disappears or is no longer the global default. It cannot yet promise resume recovery.
- The guard never executes `pactl set-default-sink`. It does not restart WirePlumber/PipeWire globally, install a driver, modify `pipewire.conf.d`, or override headphones/Bluetooth. If WirePlumber nevertheless selects the preview as global default, the guard stops its own child.
- Stop the experimental `dplus-topology-preview.py` manually first (Ctrl+C), or the service refuses a duplicate. The existing Raw service and older legacy settings are not modified.

## Prerequisites

CachyOS with working `MacBook_Speaker_Raw`, an installed `lsp-plugins-lv2`, PipeWire, WirePlumber, `pactl`, Python 3 and systemd --user. The private profile must already exist on the machine.

Run these from the repository root, **as the ordinary user, without sudo**:

```bash
python3 scripts/dplus/manage-native.py check --profile ~/Downloads/dplus-v4-reference-profile.json
python3 scripts/dplus/manage-native.py install --profile ~/Downloads/dplus-v4-reference-profile.json
python3 scripts/dplus/manage-native.py status
```

`install` writes only its private user configuration, a checksum manifest, a small runtime supervisor and the named systemd user unit; any existing file at its managed paths makes installation refuse overwriting. `check` only validates the private profile and graph and writes nothing. The source generator is SHA-256 pinned to the owner-audible revision.

## Owner acceptance checkpoint — 2026-10-25

Owner reports they **heard the 20-second test tone via the managed D+ service** after installation/manual start. Only that direct-audio milestone is confirmed. Before proceeding to ordinary app routing, validate the service `status`, `stop`, Raw playback/rollback, and a second manual start. Do not enable it automatically.

## First MANUAL service trial

Ensure the old preview has exited and `pactl get-default-sink` returns `MacBook_Speaker_Raw`. Then:

```bash
python3 scripts/dplus/manage-native.py start
python3 scripts/dplus/manage-native.py status
journalctl --user -u macbook81-dplus-native.service -n 60 --no-pager
```

The service saying *sink registered* is **NOT** evidence of working PCM. For acceptance, play the previously audible 20-second tone from the earlier proven preview through it and listen:

```bash
pw-play --target=MacBook_Speaker_D_Preview ~/Downloads/dplus-topology/audible-check-20s.wav
```

Stop and verify rollback:

```bash
python3 scripts/dplus/manage-native.py stop
pactl get-default-sink
```

After that, verify normal Raw playback. The service has no intentional automatic start or persistent default selection. **Do not enable it** until we verify manual start, audio, stop, login, resume, headphones and fail-closed behavior on the actual MacBook. If `start` initially reports success but the service immediately exits, inspect `journalctl`; it means the preflight or guard refused it.

## Route a normal application without changing the default

With the managed D+ service manually started and Raw globally selected, use the new [one-application routing procedure](dplus-application-routing.md). The helper `scripts/dplus/route-app.py` lists live named application streams, deliberately refuses to move D+'s own output bridge or other unnamed EQ streams, and moves **one playing Firefox stream** to the D+ sink using the PulseAudio-compatible routing interface. Unlike clicking KDE's global output selector, it does **not** call `pactl set-default-sink`. It verifies the route *actually changed* after WirePlumber processes it and refuses Bluetooth/headphone streams or ambiguous Firefox tabs. **18 offline tests pass; this has not yet been confirmed in normal application playback on the MacBook**. Return Firefox to Raw using `raw --id ID` before ending the test; stream IDs change between launches.

```bash
python3 scripts/dplus/manage-native.py status
python3 scripts/dplus/route-app.py list
python3 scripts/dplus/route-app.py dplus --app Firefox
# When done, while Firefox is still playing, use the ID reported:
python3 scripts/dplus/route-app.py raw --id ID
```

Never route the D+ return stream back to D+; the helper explicitly blocks that feedback hazard. Do not enable the service automatically or choose D+ as KDE's global output yet.
## Removal

```bash
python3 scripts/dplus/manage-native.py remove
```

`remove` first checks the manifest and refuses to delete files that changed or unexpected files in its private directory; it stops/disables **only its own unit**, deletes only files it owns, and reloads systemd's user unit table. It will not delete your reference profile, other D+ ZIP experiments, the existing Raw sink, or old speaker fixes.

## Offline regression

```bash
DPLUS_TEST_PROFILE=~/Downloads/dplus-v4-reference-profile.json \
  python3 scripts/dplus/test_native_service.py
```

These tests simulate filesystem writes and rollback and compare the generator with the pinned source; they **cannot** simulate PipeWire or the physical MacBook. The follow-on milestones are per-app KDE audio, measured latency/limiter safety, then login and sleep recovery, and only afterward a speaker-only default with safe external-device override and a GUI installer.

PipeWire's filter-chain client and config search behavior: [Filter-chain docs](https://pipewire.pages.freedesktop.org/pipewire/page_module_filter_chain.html), [filter-chain.conf](https://pipewire.pages.freedesktop.org/pipewire/page_man_pipewire-filter-chain_conf_5.html), [pipewire.conf environment](https://docs.pipewire.org/page_man_pipewire_conf_5.html).
