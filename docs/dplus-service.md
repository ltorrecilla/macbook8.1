# D+ Clarity v4 — status, evidence, and delivery roadmap

**Updated 2026-10-23 · MacBook8,1 (Early 2015) / CachyOS · [Tracking issue #39](https://github.com/ltorrecilla/macbook8.1/issues/39)**

**Goal:** make D+ the automatic, reliable **internal-speaker** output while retaining `MacBook_Speaker_Raw` and the existing patched CS4208 driver as a recoverable base. Deliver actual sound and working A/V synchronization before promoting D+ to the default. **No production-ready D+ implementation or new kernel driver has been released.**

**Current safe state (owner-confirmed):** the old `macbook81-dplus.service` is **disabled/inactive** and `pactl get-default-sink` reports **`MacBook_Speaker_Raw`**. The newest isolated graph experiment did not change this. Do not re-enable the old prototype or make D+ the system default.

## Verified results and boundaries

| Item | Status on the owner's MacBook | Important limitation |
|---|---|---|
| Patched HDA/CS4208 | Kernel `7.3.0-2-cachyos` runs; all three DKMS modules passed **on-disk** checks for it and `6.18.55-2-cachyos-lts`; ALSA exposed `CS4208 Speaker` device 2 | On-disk checks do not prove current module binding, boot image contents or playback on another install |
| Raw routing | Preferred `MacBook_Speaker_Raw` at S16LE, four channels, 44.1 kHz; playback previously owner-confirmed | Last follow-up commands confirmed the default, not a fresh listening comparison |
| Original D+ quality | Owner preferred D+ Clarity v4 to earlier profiles and found it close to Big Sur | No proof of Apple DSP equivalence or speaker-protection certification |
| D+ prototype lifecycle | Multi-second A/V delay after pause/resume; after s2idle wake its output-flow watchdog fired and Raw was temporarily absent; selecting D as default tripped its deliberate guard and a restart loop reached `start-limit-hit` | Wake timing is correlated with the first failure, not a proved kernel root cause |
| D+ reference | Approved local Python engine inspected; 11 biquads and full FFmpeg chain extracted; five synthetic full-chain renders replicated on CachyOS | Engine/profile remain user-held, not released here pending provenance/licensing review |
| EQ math | Independent 44.1-kHz double-precision biquads matched FFmpeg (four cases; maximum observed error about `8.77e-14`) | **Not** a test of PipeWire output or the limiter |
| Clock/rate | Production PipeWire graph uses 48 kHz (allowed rates only `[ 48000 ]`), Raw hardware uses 44.1 kHz | Reusing 44.1-kHz filter coefficients at 48 kHz changes the EQ |
| 48-kHz EQ audit | Naive unchanged coefficients drift up to ~3.71 dB in sampled 20 Hz–5 kHz band; basic bilinear conversion is closer there but differs by ~2.13 dB at 18 kHz | Experimental high-frequency correction (~0.077 dB *calculated magnitude* error) is **not** a verified native processor or release candidate |
| Isolated PipeWire | Private server connection, metadata, filter-chain loading, and two test nodes all confirmed; 21 static smoke tests passed | In a private server without session management, both nodes stayed suspended and **zero Port objects** were published even with the opt-in activation probe; **no PCM was processed** |

**Decision (2026-10-23): stop iterating on the stripped-down private PipeWire smoke-test harness.** Its purpose—proving native filter-chain module availability—is complete. Its missing ports do not establish a defective `bq_raw` filter, bad hardware driver or production PipeWire incompatibility. Next development must deliver *actual audio*, not another node-enumeration report.

## 2026-10-24 handoff — first listenable prototype

The next step has changed from private PipeWire node-registration diagnostics to an **opt-in real-time listening trial**. A standalone `dplus-live-preview.py` proof-of-concept was prepared in the conversation and packaged for private owner testing; it is **not committed to this repository** until its actual first audio output and safe stop/recovery have been validated on the MacBook. [Issue #39](https://github.com/ltorrecilla/macbook8.1/issues/39) tracks its acceptance.

The experimental client runs `pipewire -c preview.conf` against the existing user PipeWire/WirePlumber session, exposing a temporary selectable output for **one manually routed application**. It generates 48-kHz-matched D+ EQ from the owner's locally held profile, an extra 3-kHz presence stage, and an **LSP Limiter Stereo LV2** candidate, then explicitly targets the four-channel `MacBook_Speaker_Raw` device with `L,R,0,0`. In development, the 11-filter magnitude response plus corrective filters matched the original with a maximum sampled error of about 0.0589 dB; six offline Python unit tests passed. **None of these tests proves live PipeWire audio, limiter dynamics, phase or physical safety.**

The preview deliberately omits the original +8.31-dB pregain, runs the limiter at unity input gain and reduced output gain (0.35), and includes a post-limiter hard clamp. It will sound **quieter than approved D+ v4**; it is not presented as an equivalent calibrated preset. The LV2 plugin may need the distro `lsp-plugins-lv2` package, but no package is installed automatically.

**Acceptance gate:** on the owner's laptop, confirm temporary output appears, one application can play through it, Raw stays default, startup/stop are reversible, and no unexpected distortion or delay occurs. Only then commit/refine it as an experimental supported repo workflow. Do not enable the old D+ service to test this.

### 2026-10-24 — KDE device selection versus application routing

Owner installed the LSP LV2 dependency and the downloadable first real-time preview successfully displayed `Ready: MacBook_Speaker_D_Preview`. On selecting the new output in KDE, the preview printed `STOP: System default changed; stopping trial`; its temporary output disappeared. This matches the preview's **deliberate guard**: it closes itself if the global default is no longer `MacBook_Speaker_Raw`. This is **not** proof of a DSP error or sleep failure. The reported logs do not distinguish exactly which KDE control was used, but selecting the output under **Output Devices** typically changes the global default.

**One-app audition:** keep the preview running, start audio playback in an app, then choose D+ only for that app under KDE's **Applications / Playback Streams** audio controls. **Do not** select D+ in KDE's global **Output Devices** list during this experimental trial. Keep Raw as the system default and stop with Ctrl+C. If the app routes correctly, the next acceptance question is whether audio is actually heard without undue latency/distortion. [Track outcome in Issue #39](https://github.com/ltorrecilla/macbook8.1/issues/39).

The finished D+ product must eventually be able to act as the global speaker default. This temporary prototype guard is a research safety measure and cannot simply be removed until we have verified that the final graph cannot loop back into itself.

### 2026-10-24 — First audible real-time preview confirmed

The owner confirmed **“works”** after following the per-application KDE routing instructions for the experimental `MacBook_Speaker_D_Preview` client. This is the first confirmed **live native PipeWire preview playback** on the MacBook through a selected application. The preview appeared earlier but stopped when chosen as KDE's **global** default; that shutdown is intentional. The later successful playback was achieved with the per-application selection method.

**Do not overstate this milestone:** the experimental preview is intentionally lower-gain and is **not** equivalent to the approved D+ v4 limiter or loudness. The owner has not yet reported objective A/V delay, matched sound quality, measured latency, long-playback stability, headphone behavior, or suspend/resume recovery. The experimental script is still a user-held bundle, not a validated installed package. Raw remains the intended default; the latest successful listening report did not separately reprint the default sink state.

**Next task (no new script):** while the preview is running, route a video player's audio **only for that application**, perform pause/resume and seeking repeatedly (initial small sample, then the planned 20-cycle test), check for any growing A/V delay or dropouts, and stop with Ctrl+C. Observe whether stopping removes the preview and normal Raw audio remains. Only after that should we refine the limiter, level, and automatic resume/default handling.

### 2026-10-24 — Playback feedback and controlled vocal-clarity trial

Owner reports the opt-in lower-gain D+ preview has been **working well so far, without noticed functional issues**; voices remain **very slightly muffled**. This is encouraging but not proof of long-duration sync, measured latency or exact D+ v4 dynamics.

The existing preview already includes an extra **+1.0 dB at 3 kHz** presence stage. A privately supplied experimental A/B variant (not yet in the repository) holds the 11 source biquads, 48-kHz correction filters, reduced-gain LSP limiter, final clamp, stereo-to-Raw `L,R,0,0` mapping, and default-selection guard unchanged. It permits just **+1.0 versus +1.5 dB** on the 3-kHz band. Six offline safety/graph consistency tests passed, but the brighter variant has **not** been listened to or validated on this MacBook.

The test should use the same speech excerpt and roughly matched loudness at modest volume, starting/stopping each variant separately (per-app KDE selector only, not global default). If the extra half-decibel does not clearly improve natural speech or causes sharp consonants, retain the already functioning +1.0 dB setting. A slightly muffled impression could also result from the intentionally lower gain rather than filter shape; do not increase global volume, driver gain, or the original +8.31 dB pregain as a shortcut.

## Approved D+ v4 reference contract

The owner-supplied `macbook81-dplus-engine-reference.py` (SHA-256 `43da928c7b1b7cd1b1628e47276820dcb2eeeeb841136a425ea25d280ec4076b`) implements:

```text
stereo float32, 44100 Hz
 → 11 ordered biquads / channel (FFmpeg f64, transposed DF-II)
 → +1 dB peaking EQ at 3000 Hz, Q=1
 → +8.31 dB pregain
 → 176400-Hz double-precision resampling (4×)
 → FFmpeg alimiter: limit=0.6683439175686147, attack=5 ms,
   release=80 ms, linked stereo; automatic level disabled
 → 44100-Hz resampling → -0.01 dB final trim
 → L,R,0,0 (four-channel S16LE, 44100 Hz; no dither)
 → MacBook_Speaker_Raw
```

The high pregain **must never be used without a verified limiter and headroom checks**. The exact 11 coefficient rows remain in the private extracted reference JSON; neither they nor the engine are currently packaged as redistributable release assets. Equal displayed volume percentages across macOS and CachyOS are not a calibrated loudness comparison.

## Architecture decision

**Keep driver and sound processing separate.**

- **Hardware layer:** retain the working three-module `macbook12-audio/0.1` CS4208 DKMS setup, mixer behavior and Raw sink. Fixes to hardware initialization, clock state, amplifier routing and kernel updates belong in [driver issue #2](https://github.com/ltorrecilla/macbook8.1/issues/2) and [audio recovery](audio-update-recovery.md).
- **D+ layer:** prefer a real-time PipeWire/WirePlumber-compatible processing path using an existing maintained DSP/LV2 implementation where feasible. Use a small native plugin **only if** needed to reproduce the limiter or an essential real-time property. Do not return to the fragile `parecord → FFmpeg → pacat` bridge for production.
- **Rate contract:** keep the normal PipeWire 48-kHz system graph stable. Evaluate either **(A)** a measured 48-kHz response-matched DSP and limiter, or **(B)** properly isolated 44.1-kHz DSP with bounded resampling. Choose by measured audio parity, CPU use and latency, **not** by a frequency plot alone.
- **Routing:** initial output must be **manual, per-application, opt-in**, with safe mapping to Raw. Never stack upstream EQ or duplicate rear channels. Default-device selection and system volume integration are later work.

## Work plan — acceptance gates

Treat a checkbox as complete **only when the deliverable was observed**, not merely when a diagnostic script passed. Use [issue #39](https://github.com/ltorrecilla/macbook8.1/issues/39) for ongoing checkboxes and ownership.

### A. Preserve the known-good state — mostly complete

- [x] Verify current installed DKMS module files and working `MacBook_Speaker_Raw` routing.
- [x] Disable the failed old D+ user unit and confirm `disabled`/`inactive` and Raw as default.
- [ ] Confirm ordinary Raw speaker playback at modest volume after the latest changes; document a known-good kernel and fallback procedure.

**Gate:** known-good Raw output and a tested return path. Do not alter Limine, HDA modules or speaker GPIOs to develop D+.

### B. Freeze reference audio — mathematical baseline complete

- [x] Recover and inspect approved v4 engine and full filter order; preserve source digest.
- [x] Reproduce five offline full-chain synthetic cases on CachyOS, including silence, isolated left/right impulses, and quiet/loud signals; rear outputs exactly zero.
- [x] Reproduce 44.1-kHz biquad-only math on CachyOS; run 48-kHz response-drift audit.
- [ ] Add representative level-matched reference material, aligned impulse/transient checks, true-peak and limiter-response comparisons; review source/plugin attribution.

**Gate:** reproducible full-profile audio benchmarks with objective headroom and dynamics measurements, not just EQ magnitude.

### C. Deliver ONE listenable native D+ prototype — next priority

- [ ] Select and document the real-time host/limiter and version; check whether it can reproduce the FFmpeg limiter well enough.
- [ ] Resolve 48-kHz graph / 44.1-kHz Raw rate handling with measured response, phase, dynamic and latency parity. Avoid shipping the naive conversion.
- [ ] Build a **complete** opt-in processing chain: 11 biquads, +1 dB presence, bounded gain + working limiter, stereo output and explicit `L,R,0,0` Raw mapping.
- [ ] Produce an actual per-app listening A/B on the MacBook with one reproducible start/stop command and no persistent default change.
- [ ] Capture and compare processed PCM against the approved reference; measure clipping/peaks, CPU demand and end-to-end latency.

**Gate:** audible, safe, bounded-latency D+ playback on real hardware. If this approach cannot deliver actual PCM without more infrastructure churn, stop and switch DSP architecture instead of making another smoke harness.

### D. Stabilize actual playback

- [ ] Confirm owner-approved sound vs D+ v4 and Raw at matched levels.
- [ ] Run at least 20 pause/resume/seek video cycles, 30 minutes continuous playback and A/V alignment measurements relative to Raw; **no growing delay**.
- [ ] Confirm modest-volume behavior, no uncontrolled gain/clipping, and reasonable CPU/xrun results on Core M hardware.
- [ ] Verify stop/crash cleanup, PipeWire restart, lid suspend/resume, and headphone/Bluetooth handling without taking over other devices.

**Gate:** reproducible sound parity (or explicit owner acceptance of measured differences) and reliable video synchronization.

### E. Default output, packaging and maintenance — only after C/D pass

- [ ] Implement WirePlumber/KDE preferred internal-speaker output, normal volume keys, explicit fallback to Raw and respect for headphones/external devices.
- [ ] Verify three cold boots, login/logout, five suspend/resume cycles, failure recovery and a kernel update on hardware.
- [ ] Provide reversible `check/install/verify/uninstall` workflow; audit DSP and driver licensing, ownership and clean-install safety.
- [ ] Update README hardware status only after tests; release the first **opt-in** package before recommending D+ as default.

**Gate:** user does not need to start D+ manually and can always return to working Raw without rebuilding drivers.

## Operational safety and rollback

The old prototype intentionally **refuses to be the system default** and has a known transport latency/restart failure. Do not enable it for this plan:

```bash
systemctl --user is-enabled macbook81-dplus.service
systemctl --user is-active macbook81-dplus.service
pactl get-default-sink
```

Expected baseline: `disabled`, `inactive`, `MacBook_Speaker_Raw`. If the old prototype is unexpectedly active, stop and disable **that exact unit**:

```bash
systemctl --user disable --now macbook81-dplus.service
pactl set-default-sink MacBook_Speaker_Raw
```

This doesn't delete its local code or rebuild HDA. For any new D+ test, prefer an isolated per-app manual selector and provide a verified stop/cleanup operation **before** activation. Do not unload unknown PipeWire modules, force global sample-rate changes, run an unreviewed Ubuntu-oriented root installer, or replace a working kernel.

## References and maintenance

- [Offline D+ tests and experimental isolated PipeWire research](dplus-offline-testing.md) — **historical technical evidence, not the next required workflow**.
- [Audio-update recovery](audio-update-recovery.md) and [source packaging blockers](audio-packaging.md).
- [Earlier listening / speaker-tone work](https://github.com/ltorrecilla/macbook8.1/issues/1).
- [Implementation task tracker](https://github.com/ltorrecilla/macbook8.1/issues/39).

The previous multi-revision experimental diagnostics remain in Git history. Keep the repository small; **do not add more diagnostic-harness revisions** unless required to deliver an end-to-end audio output or to investigate a newly observed fault. Real hardware acceptance remains separate from simulated unit tests.
