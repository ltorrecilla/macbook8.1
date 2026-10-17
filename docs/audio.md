# Audio packaging status

The owner's MacBook8,1 with kernel 7.2.9-2-cachyos has working internal audio using a patched HDA / CS4208 stack. The observed system loads `snd_hda_codec_cs420x` and `snd_hda_codec_generic`, uses `/etc/modprobe.d/mb81-singlecmd.conf`, and has a PipeWire `MacBook_Speaker_Raw` sink.

**This is not a general-purpose working audio installer yet.** Exact patched sources, DKMS build recipe, and PipeWire configuration are required.

Run on the working MacBook:

```bash
bash scripts/collect-audio-evidence.sh
```

This is a read-only inventory of likely source paths, modprobe configuration, modules and DKMS information. No kernel source is copied or published. Inspect the generated `macbook81-audio-evidence.txt` before sharing, since paths and settings may contain personal information.

Next: identify exact patch and licensing, build a versioned DKMS package, test clean installation and rollback on a supported CachyOS kernel. Preserve an unmodified kernel for recovery.

The optional CPU cap tool and more detailed documentation are also available in the v0.3 toolkit archive supplied in the project conversation, pending publication in this repository.

## Bass and speaker-channel routing diagnosis (October 2026)

The working machine reports `MacBook_Speaker_Raw` as a four-channel sink at 44.1 kHz and also exposes `input.MacBook_Speaker` through a separate PipeWire filter-chain. The owner reports thinner-than-macOS bass. **We have not identified the cause.** Possible explanations include the channel-to-speaker map, phase/polarity, differing PipeWire processing, or missing macOS acoustic correction. Do not assume a bass EQ boost is the answer: incorrectly routed speaker channels can cause cancellation, and excessive low-frequency gain may distort small speakers.

Use the [read-only audio details collector](../scripts/collect-audio-details.sh) on the working MacBook:

```bash
bash scripts/collect-audio-details.sh
```

It creates `macbook81-audio-details.tar.gz` with local DKMS source files (when readable), relevant PipeWire/WirePlumber and modprobe configuration, and a sink/channel-map report. **Review archive contents for personal data, custom code, and licenses before sharing or publishing.** It neither edits system settings nor changes the default audio output. Never publish the collected source archive directly without license and provenance review.

Inspect the actual raw sink channel positions, ALSA channel mapping and filter configuration before designing a speaker-specific DSP preset. Compare raw and filtered paths at safe volume. EQ should be optional and reversible, with no promise of macOS-identical sound.
