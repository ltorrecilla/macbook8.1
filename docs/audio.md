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
