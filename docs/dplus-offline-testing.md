# D+ Clarity v4 — offline reference (Milestone 2.2)

**Offline reference generation only, NOT an installer, live processor or speaker safety test.** It does not contact PipeWire/ALSA, run systemd, change outputs or play audio.

The approved source engine and extracted JSON profile remain local/private pending provenance/licensing review. The repository tracks only generic test tooling.

## Usage

Put the user-held `dplus-v4-reference-profile.json` and `macbook81-dplus-engine-reference.py` under `~/Downloads/` and execute as your normal user from the repository root:

```bash
python3 scripts/dplus-offline-reference.py \
  --profile "$HOME/Downloads/dplus-v4-reference-profile.json" \
  --engine-source "$HOME/Downloads/macbook81-dplus-engine-reference.py" \
  --output-dir "$HOME/Downloads/dplus-v4-baseline"
```

`--engine-source` is optional but recommended. It verifies the approved SHA-256 digest and constants using a static AST read; it never executes the source. The only external requirement is FFmpeg. No sudo or Python packages needed.

The output directory must not contain existing files. Five synthetic cases render to four-channel S16_LE 44.1-kHz WAVs and a `manifest.json` containing FFmpeg version, source/filter hashes, output hashes, peaks, RMS and channel activity. Do not play these synthetic fixtures at normal speaker volume.

Run offline unit tests (no FFmpeg or private profile needed):

```bash
python3 -m unittest discover -s tests -p 'test_dplus_offline_reference.py' -v
```

## Milestone 2.3 — Biquad-only equivalence (no live device)

After the five full-chain offline reference tests pass, run the new **11-biquad-only** comparison. It does not change, enable or start audio services, default sinks, PipeWire modules, or kernel drivers.

```bash
python3 scripts/dplus-biquad-parity.py \
  --profile "$HOME/Downloads/dplus-v4-reference-profile.json" \
  --output-dir "$HOME/Downloads/dplus-v4-eq-parity"
```

The output folder must be absent or empty. It generates a `parity-report.json` that compares a separate Python f64 TDII implementation with FFmpeg's eleven identical biquads (stereo silence, left/right impulse, stereo tones). It also generates a **review-only, inert** `biquad-only-filter.graph` with 22 PipeWire `bq_raw` filters, 11 per channel. The graph is **not** an installable PipeWire module or safe speaker chain: no +1 dB presence, no pre-gain/limiter/oversampling, no `L,R,0,0` mapping or restart/recovery logic. **Do not copy it into ~/.config/pipewire**, or set it as a default sink.

The standalone parity test validates mathematical interpretation of the source biquads vs FFmpeg, **not** the actual PipeWire DSP execution. Next gates are sample-aligned native PipeWire evaluation of `bq_raw` and the separate extra 3-kHz band, followed by limiter, gain, sample-rate, mapping, real-time and A/V-sync tests.

Run portable unit tests:

```bash
python3 -m unittest discover -s tests -p 'test_dplus_biquad_parity.py' -v
```

## Next gate: PipeWire graph sample rate (read-only)

The owner confirmed the offline 11-biquad math on CachyOS. **Do not interpret that as native PipeWire filter equivalence.** PipeWire's documented `bq_raw` picks the available coefficient set nearest to the **graph sampling rate**. The inert generated graph has only 44.1-kHz coefficients; if the actual processing graph runs at 48 kHz, applying the same values will shift the response. `pactl list short sinks` does not prove the graph clock rate.

Inspect without changing anything:

```bash
printf '=== SETTINGS METADATA ===\n'
pw-metadata -n settings 0
printf '=== AUDIO DEFAULT AND PROTOTYPE ===\n'
pactl get-default-sink
systemctl --user is-enabled macbook81-dplus.service
systemctl --user is-active macbook81-dplus.service
```

The next *implementation* must either ensure the actual biquad processing graph is fixed at 44.1 kHz with verified resampling boundaries, or generate the correctly transformed coefficients for the verified rate. Neither approach is assumed solved. Do not set `clock.force-rate`, change the global PipeWire clock, load the graph, or enable the old D+ service as part of this check.

## 48-kHz response audit — confirmed graph rate on original MacBook

On 2026-10-23 the owner reported PipeWire metadata `clock.rate=48000`, `clock.allowed-rates=[ 48000 ]`, core default 48000/quantum 1024. The physical `MacBook_Speaker_Raw` is 44100 Hz. The old D+ service remains disabled/inactive and Raw remains default. **Do not force the PipeWire graph to 44100 Hz or change system-wide audio timing to test EQ.**

Run the offline frequency-response calculation with the same private profile:

```bash
python3 scripts/dplus-biquad-parity.py \
  --profile "$HOME/Downloads/dplus-v4-reference-profile.json" \
  --rate-audit
```

This prints JSON to the terminal without generating a graph, touching settings, or using a sound device. It compares (a) applying unchanged 44100-Hz coefficients at the real 48000-Hz graph rate, and (b) a **candidate** bilinear-substitution coefficient mapping to 48000 Hz. It reports sampled maximum and specific-frequency response differences relative to the exact original 44100-Hz cascade. The fixed 44.1-kHz review-only graph is **not** suitable for the 48-kHz graph.

Early offline analysis of the approved profile showed unchanged coefficients shifted about -2.51 dB at 100 Hz and -2.97 dB at 18 kHz. The bilinear candidate reduces low-frequency drift but still shifts about -2.13 dB at 18 kHz. Therefore **neither conversion is approved as D+ equivalent**, and the audit does not export deployable 48-kHz coefficients. A more accurate response fit, or an isolated true 44.1-kHz DSP/resampling design, must be measured before any live PipeWire graph. Also evaluate the separate +1 dB stage, limiter and full-chain response.

Offline unit tests now include four additional rate-analysis tests (12 tests total). The historical offline FFmpeg-versus-Python parity result remains valid **at 44100 Hz only**.

## Milestone 3.0 — Native module initialization in a separate PipeWire server

The MacBook preflight confirmed `pw-cat`, `pw-link`, `pw-cli`, `pw-dump`, and the installed native filter-chain module. The actual checkout is `/home/luis/git/macbook/macbook8.1` (not the older path).

First test the runtime availability of PipeWire's builtin `bq_raw` with an **independent disposable PipeWire daemon**. This is a minimal *unity* stereo test; it does not use the confidential D+ profile or exercise speaker sound quality. It creates a new private socket/config under a temporary directory, loads only protocol/client/adapter and the filter-chain module, observes the two test nodes through that socket, then terminates only its own child process and removes its temporary files. It does not start WirePlumber, PipeWire-Pulse, ALSA monitoring or a hardware sink, and never issues a systemd command.

From a current checkout, as your ordinary user:

```bash
python3 -m unittest discover -s tests -p 'test_dplus_isolated_pipewire_smoke.py' -v
python3 scripts/dplus-isolated-pipewire-smoke.py --show-config
python3 scripts/dplus-isolated-pipewire-smoke.py
```

If the last command fails, preserve its printed **private daemon log** and stop: do not work around it by restarting the production PipeWire service, enabling D+, or loading the graph into the live server. `--show-config` is dry-run only. This stage validates **module initialization and node enumeration**, not actual signal flow or DSP parity. Run the subsequent audio-capture test only after this passes and its routing has been reviewed.

Continue verifying `pactl get-default-sink` remains `MacBook_Speaker_Raw`; keep the original D+ user service disabled. The disconnected smoke test's unity coefficients are **not** the real D+ v4 EQ and no limiter or channel mapping is included.


## What is actually tested

- Silence, left impulse, right impulse, quiet synthetic audio, loud synthetic audio.
- Expected frame count and rate; exactly zero rear channels (`L,R,0,0`); isolation of left/right impulses; silent input stays silent.
- Rejects changed limiter threshold, missing biquads, altered output mapping and wrong source hash.
- The graph is constructed from the exact 11-biquad coefficients, +1 dB at 3 kHz, +8.31 dB gain, 176.4-kHz oversampling, FFmpeg 5/80-ms limiter, final trim and mapping in the approved JSON profile. **Never use the large pre-gain without a limiter.**

## Limits

- Output hashes can differ across FFmpeg builds, resamplers and platforms; compare measured PCM and level-aligned results before judging changes.
- Sample peaks do not establish true peaks or physical speaker safety.
- This is a baseline for later native-PipeWire DSP parity work, not proof of native limiter equivalence, live A/V synchronization, suspend recovery or headphone behavior.
- Keep the old D+ service disabled, Raw as the default, and the engine/profile private until release review.

Progress and acceptance criteria: [D+ roadmap issue #39](https://github.com/ltorrecilla/macbook8.1/issues/39).
