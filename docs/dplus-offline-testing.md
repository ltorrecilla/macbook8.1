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
