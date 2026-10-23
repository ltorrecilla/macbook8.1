# Script reference — MacBook8,1

**Status:** source-level risk classification, not an endorsement to run every command. Refer to the corresponding guides for hardware prerequisites and rollback. Script paths are preserved; no executable changes were made. Review date: 2026-10-23.

**Categories:** READ = reads configuration but may create local diagnostic output; WRITE = modifies local data or user configuration; PRIVILEGED = installs/removes modules, services, or changes system boot/configuration; EXPERIMENT = not validated for general use; LIBRARY = invoked by another script.

| Script | Category | Purpose and essential restriction |
|---|---|---|
| `audio-preflight.sh` | READ | Precheck patched HDA/audio setup, no installer |
| `audit-audio-bundles.py` | READ / WRITE output | Audit local audio archives; review output and source licensing |
| `camera-common.sh` | LIBRARY | Shared installer/uninstaller ownership checks, not standalone |
| `check-camera.sh` | READ | Verify facetimehd configuration; does not prove third-party app discovery |
| `check-cpu-limit.sh` | READ | Report CPUFreq cap |
| `check-doc-links.py` | READ | Offline Markdown link and heading-anchor checker, heuristic |
| `check-kernel-update.py` | READ | Pre-reboot DMA symbol/audio compatibility checks; keep stable |
| `collect-audio-details.sh` | READ / WRITE output | Sensitive archive of source/config/audio data; review before upload |
| `collect-audio-evidence.sh` | READ / WRITE output | Writes driver and path inventory, may contain private paths |
| `collect-audio-support.sh` | READ / WRITE output | Archives three narrowly named recovery helpers; inspect source and paths |
| `compare-raw-voice.py` | EXPERIMENT / WRITE output | Acoustic comparison, not a driver repair |
| `cpu-cap-control.sh` | LIBRARY / PRIVILEGED | Writes CPU sysfs controls when run by systemd, not a normal diagnostic |
| `install-camera.sh` | PRIVILEGED | Downloads driver and firmware, registers/builds DKMS; matching laptop required |
| `install-cpu-limit.sh` | PRIVILEGED | Installs/starts CPU cap systemd service |
| `macbook81-hibernate-prepare.py` | EXPERIMENT / PRIVILEGED when --apply | --check is preparatory; --apply writes swap, boot/service config; fixed machine-specific parameters |
| `repair-audio.py` | READ in --check, PRIVILEGED in --repair | Existing registered patched DKMS installation only; repair rebuilds and regenerates Limine boot images |
| `stage-audio-source.py` | WRITE output | Stages a known source manifest locally; does not install modules |
| `test-speaker-routing.py` | EXPERIMENT / WRITE output | Outputs test audio and plays via speakers; use safe volume |
| `try-warm-audio.py` | EXPERIMENT / USER CONFIG WRITE | Backs up/modifies PipeWire user files, restarts user audio services; do not invoke as read-only check |
| `uninstall-camera.sh` | PRIVILEGED | Removes only installer-owned driver/DKMS state; preserves firmware |
| `uninstall-cpu-limit.sh` | PRIVILEGED | Disables/removes CPU service and related files |

Service: `systemd/macbook81-cpu-cap.service` invokes CPU sysfs changes via the installed helper. It is not a standalone CLI command.

## Safe entry points

From the repository root, on the actual MacBook, the commonly used read-only checks are:

```bash
python3 scripts/check-kernel-update.py
python3 scripts/repair-audio.py --check
bash scripts/check-camera.sh
bash scripts/check-cpu-limit.sh
python3 scripts/check-doc-links.py
```

These commands should not install or change system configuration, but checks can fail and diagnostics may reveal local machine information. The link checker works on a normal checkout on any host.

## Before any mutating command

1. Confirm MacBook8,1 hardware and correct kernel/headers when required.
2. Read the [installation matrix](installation-matrix.md) and subsystem rollback guide.
3. Preserve a known-good kernel/boot entry for kernel or audio changes.
4. Verify script ownership and do not run experimental hibernation, D+ or audio routing tools as part of routine installation.
5. For collectors, keep generated files private until screened for identifiers and code/firmware licensing.

See [maintenance rules](repository-cleanup-roadmap.md). **Keep executable entry-point paths stable unless a tested change requires otherwise.**
