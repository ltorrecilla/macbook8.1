# Audio driver and EQ upstream comparison

Checkpoint saved 2026-10-18, from the preceding repository review and the owner's uploaded audio-details archive. This is a file-content comparison, not a build, installation, or hardware-validation result.

## Repositories reviewed

- [leifliddy/macbook12-audio-driver](https://github.com/leifliddy/macbook12-audio-driver): the reviewed README explicitly supports MacBook9,1 and MacBook10,1 and excludes MacBook8,1. Reviewed README blob: `7887cccd4463c5ea6675d0dc5d5cfcef27431cbc`.
- [thomas-shirley/macbook8.1-speaker-driver](https://github.com/thomas-shirley/macbook8.1-speaker-driver): explicitly targets the 2015 model and credits leifliddy and davidjo. This is a much closer reference for the recovered driver.
- [leifliddy/macbook10-1-audio-driver-test](https://github.com/leifliddy/macbook10-1-audio-driver-test): historical reference, not an installation recommendation.

These statements describe the reviewed snapshots; recheck upstream before adopting future changes.

## Source identity, not proof of authorship or complete checkout history

Local collector archive: `macbook81-audio-details.tar.gz`.
SHA-256: `e2f2d2cf48896e5fa453617d964ee3bd4a1c9bc1d137ce0d11825de6958d00b0`.

Compared reference tree in thomas-shirley's repository: `fe54ad1aa7d8448fc49c0b5c8b353c50e2b1b8a1`.
[Reference tree metadata](https://api.github.com/repos/thomas-shirley/macbook8.1-speaker-driver/git/trees/fe54ad1aa7d8448fc49c0b5c8b353c50e2b1b8a1?recursive=1).

The prior comparison calculated Git blob IDs from the exact archived file bytes. Four checked files match and two differ:

| File under local `source/` | Result | Local Git blob | Reference Git blob |
|---|---|---|---|
| `dkms.conf` | MATCH | `18e7b93038c3ec29a234adf8b4a7515b4cffc964` | `18e7b93038c3ec29a234adf8b4a7515b4cffc964` |
| `dkms.sh` | MATCH | `a1edf9c3b11502e6f0ace4ea978ebff282e96a7b` | `a1edf9c3b11502e6f0ace4ea978ebff282e96a7b` |
| `patch_cirrus/cs420x.c` | MATCH | `92b1448796b6b18f54faf6e4b5011aec4b9a47c2` | `92b1448796b6b18f54faf6e4b5011aec4b9a47c2` |
| `patch_cirrus/patch_cirrus_a1534_setup.h` | MATCH | `96f8922aa513534a81fe17206610ca34854994bf` | `96f8922aa513534a81fe17206610ca34854994bf` |
| `patch_cirrus/patch_cirrus_a1534_pcm.h` | DIFFERENT | `77d4f0f9a47470306856abc10410d9de733accc6` | `cbb8bd134b153e0d76b5e3efb9908e03b73fb28e` |
| `patch_cirrus/patch_cirrus_macbook81_setup.h` | DIFFERENT | `e4fc50c139bcd6bc5725ec8ba55cd6e7786759af` | `2621cc7c7db692726eb7340e3b7c3ffd2d6c4517` |

Do not call the entire local driver identical to upstream. Matching content does not establish authorship, licensing completeness, or which checkout/patch commands were used locally. Preserve upstream attribution and investigate the differing headers before packaging.

## Do not overlay leifliddy's installer on the working installation

The reviewed leifliddy DKMS recipe uses `macbook12-audio-driver/0.1` and builds one codec module (`snd-hda-codec-cs420x` on new-layout kernels). The owner's existing package is `macbook12-audio/0.1` and builds that module plus `snd-hda-intel` and `snd-hda-codec-generic`.

The package names differ but the replacement codec module overlaps. Do not interpret the different names as making them safe to install together. Reviewed leifliddy DKMS recipe blob: `f1118f7631c6ebfb23a8251a2ec1b5dae12270a1`.

## Full speaker EQ: candidate for the next experiment, NOT a released preset

Reference: [51-macbook81-speaker.conf](https://github.com/thomas-shirley/macbook8.1-speaker-driver/blob/main/51-macbook81-speaker.conf).
Reviewed Git blob: `cb61657dd0eab63d0f804432d1b0fbff18fc50bf`.

The author labels it `macOS layout100 EQ`. This is a source comment, not an independently verified match to the owner's Big Sur system. The macOS I/O Registry report has been requested but not received at this checkpoint.

The following stages are applied on both sides. They are parameters for research, not instructions to write live configuration:

| Stage, in reference chain order | Type | Frequency (Hz) | Q | Reference gain (dB) | Captured local gain (dB) |
|---|---|---:|---:|---:|---:|
| Preamp-like stage | High shelf | 20 | 0.707 | +10 | 0 |
| HPF 1 | High pass | 134 | 0.707 | Not applicable | Not applicable |
| HPF 2 | High pass | 137 | 0.707 | Not applicable | Not applicable |
| PEQ 1 | Peaking | 258 | 0.79 | +4 | 0 |
| PEQ 2 | Peaking | 365 | 5.05 | -2 | 0 |
| PEQ 3 | Peaking | 1800 | 2.32 | -3.5 | 0 |
| High shelf | High shelf | 265 | 1.65 | -3 | 0 |
| PEQ 4 | Peaking | 875 | 0.62 | -10 | 0 |
| PEQ 5 | Peaking | 12800 | 0.56 | -14 | 0 |
| PEQ 6 | Peaking | 3000 | 0.96 | -5 | 0 |
| PEQ 7 | Peaking | 4870 | 2.96 | -4 | 0 |

The local values come from the uploaded `macbook81-pipewire-live(1).json` filter configuration. Both configurations specify the two high-pass stages. Listing parameters is not verification of the live filter's transfer function or the acoustic response.

The upstream preamp comment says +15 dB, while the actual gain is +10 dB. Do not copy either gain blindly into a live audition. A controlled offline render should account for the complete chain, reserve headroom, check actual sample/true peaks, and match levels without introducing compression. Any departure from the reference chain must be explicitly documented.

The important difference from previous experiments is the complete set of cuts, especially the broad -10 dB cut at 875 Hz. Earlier small bass boosts did not test this full profile. Whether it improves perceived sound remains untested.

## Scope of this checkpoint

Only documentation is being published. No driver source, firmware, personal codec/PipeWire dump, or audio recording is included. No changes to the owner's laptop or the existing audition scripts are made.

Resume from [the continuation checkpoint](continuation-checkpoint.md). Sound quality remains tracked in [Issue #1](https://github.com/ltorrecilla/macbook8.1/issues/1); packaging remains separate in [Issue #2](https://github.com/ltorrecilla/macbook8.1/issues/2).
