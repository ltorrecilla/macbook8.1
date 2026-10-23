# MacBook8,1 audio support-file recovery — 17 October 2026

> **Historical source-recovery evidence (October 17, 2026).** Checksums and recovered helper descriptions are retained for provenance. This is not a fresh-install procedure. Consult [audio packaging](audio-packaging.md) for outstanding release blockers and [audio update recovery](audio-update-recovery.md) for existing installations.

**Status: all three previously missing support files recovered. This is an evidence milestone, not an installable release.**

## Archive verification

The user's `macbook81-audio-support.tar.gz` contains six support-file copies. Each file was captured once from its installed location and once from the local audio repair source tree; the two versions have identical SHA-256 hashes.

| Support file | SHA-256 prefix | Expected installation role |
|---|---|---|
| `efi_recover.py` | `45d03baccca67cea` | Driverless CS4208 controller/codec recovery |
| `mb81-resume-recover.service` | `726a20b926850b6b` | Start speaker recovery after suspend |
| `mb81-jack-switch.service` | `7957431c26324e58` | User-session headphone-jack monitoring |

The two systemd service files invoke `/usr/local/bin/mb81-resume-recover` and `/usr/local/bin/mb81-jack-switch`. The implementations are present in the earlier **audio-details** collector archive as `source/resume_recover.sh` and `source/mb81-jack-switch.sh`, respectively. The existing `dkms.conf` builds three HDA modules: `snd-hda-codec-cs420x`, `snd-hda-codec-generic`, and `snd-hda-intel`.

**Do not publish the collected source archives directly.** They include local system configuration and externally derived code whose distribution licenses and attribution must be reviewed.

## Safety issues found in the recovered code

1. **Direct PCI/MMIO operations:** `efi_recover.py` deliberately accesses PCI configuration space and controller MMIO to power-cycle and initialize CS4208. It requires a driverless controller and special recovery conditions; it must not be a default automatic step on unvalidated systems.
2. **Unsafe original DKMS install/removal:** The legacy `dkms.sh` directly deletes `/var/lib/dkms/macbook12-audio` including DKMS's original-module backups and sweeps module files manually. A replacement must rely on DKMS transaction semantics, backups and fail-closed checks.
3. **Distribution-specific initramfs:** The original installer calls Ubuntu's `update-initramfs`; CachyOS uses the `mkinitcpio` workflow. A release must verify both boot and fallback initramfs content and avoid overwriting boot configuration.
4. **Speaker-default conflict:** `mb81-jack-switch.sh` currently selects `input.MacBook_Speaker` on startup and headphone unplug. The tested owner's preferred output is `MacBook_Speaker_Raw`, so defaults must be configurable and verified.
5. **Suspend recovery behavior:** `resume_recover.sh` stops user audio services, unbinds HDA controllers and unloads several kernel modules. It must be separately opt-in and tested for recovery and failed resume before any automatic enablement.

## Next implementation milestone

- Create a clean, versioned, attributed **patch series**, not a blind copy of the recovered source tree.
- Refactor the three-module DKMS builder with pinned/verifiable kernel source, ABI/version checks and all-module symbol CRC linkage checks.
- Add a **plan/dry-run mode** and a rollback journal; refuse to replace an existing `macbook12-audio/0.1` DKMS installation unless its state is backed up and ownership is known.
- Isolate advanced jack-switch and low-level resume recovery as opt-in modules. Default to the working raw output; keep sound-quality EQ separate (issue #1).
- Test the full install/uninstall and kernel upgrade on a spare/clean MacBook8,1 before offering a public `sudo ./install.sh`.

For now, run only the [read-only audio preflight](../scripts/audio-preflight.sh). This archive is **not** proof of a safe universal audio installer.

See [installer tracker](https://github.com/ltorrecilla/macbook8.1/issues/2).
