# Installation and rollback matrix — MacBook8,1

**Read before running any installer.** These tools target the Early 2015 12-inch MacBook8,1 running CachyOS. A passing simulated test does **not** certify a clean hardware installation. This is a navigation/decision guide, not a one-command installer.

| Subsystem | Prerequisites and support | Installation or repair | Verification | Rollback and limits |
|---|---|---|---|---|
| Camera | Matching MacBook8,1, packages and kernel headers detailed in [camera guide](camera.md). Original *manual* setup confirmed moving image in mpv; wrapper fresh-install not tested on laptop | Optional `bash scripts/install-camera.sh` (runs as normal user, escalates specific steps via sudo) | `bash scripts/check-camera.sh`; physical capture test described in guide | `sudo bash scripts/uninstall-camera.sh` for wrapper-owned installation **only**; firmware intentionally preserved. Do not remove a pre-existing manual installation |
| CPU frequency cap | Model and CPUFreq policy checked by installer; only initial cap confirmed by owner | `sudo bash scripts/install-cpu-limit.sh 1600` | `bash scripts/check-cpu-limit.sh`; check again after reboot and resume | `sudo bash scripts/uninstall-cpu-limit.sh`; other CPU management tools can override cap; not a guaranteed temperature ceiling |
| Existing patched audio | Requires already-registered three-module patched CS4208 DKMS source and suitable kernel packages; see [recovery](audio-update-recovery.md) | Check first: `python3 scripts/repair-audio.py --check`. On diagnosed missing build only: `sudo python3 scripts/repair-audio.py --repair` | Check DKMS/modules, ALSA speaker, Raw sink and audible playback per recovery guide | Recovery procedure and known-good boot kernel; **not** a fresh-install/uninstall solution; replacement affects HDA and boot images |
| Fresh audio installation | **Not available**: third-party source provenance, license, reproducible package and rollback still outstanding | No supported install command; see [packaging](audio-packaging.md) | No clean-install validation | Do **not** execute recovered legacy Ubuntu-oriented installer |
| Keyboard and trackpad | Running kernel-specific built-in DMA behavior; see [kernel update playbook](kernel-update-playbook.md) | **No general-purpose installer.** Working initcall blacklist in Limine is kernel-specific, not portable | `python3 scripts/check-kernel-update.py` before reboot; then hardware input after reboot | Retain known-good kernel and alternate input/recovery route; do not copy symbols from another kernel |
| Bluetooth | Working after local ACPI/DSDT workaround according to owner; [README tracker](../README.md) | No validated reusable installer | Check pairing and reconnect on actual hardware | Machine-specific recovery must be documented before packaging |
| D+ speaker processing | Optional user-session prototype; [guide](dplus-service.md) | Experimental opt-in only; do not auto-enable on login | Manual listening and pause/resume A/V sync | Disable user unit, restore Raw as default; latency bug remains unresolved |
| Sleep battery drain | `s2idle` active, EC wakeup experiment proposed; [guide](sleep-battery-drain.md) | Runtime-only experiment requires controlled testing | Confirm resume, lid wake and measured Wh consumption | Runtime revert/reboot; no supported persistent improvement yet |
| Hibernation | Machine-specific 7.2.9 preparation assumptions; read [hibernation guide](hibernation.md) | **Experimental and not fully tested**. No universal installer or successful restore confirmed | Read-only preparation check first; real restore test separately | Backups and recovery documented in guide; do not execute as part of normal setup |

## Required format for future installation guides

Each subsystem guide should contain, at minimum:

1. **Supported hardware, kernel and state:** explicit model, observed versions, prerequisites and tested vs simulated distinction.
2. **Read-only preflight:** commands that do not change system configuration; explicit stop conditions.
3. **Install/repair:** privileged actions, exact ownership, what files and services change, and whether the action is optional.
4. **Verification:** hardware and service tests after install, reboot, suspend/resume and kernel update as applicable.
5. **Rollback/recovery:** known-good boot entry, preserved files, safe uninstall scope and partial-failure behavior.
6. **Open risks:** unresolved bugs, portability restrictions, license obligations and links to dated evidence.

**Do not run all installers in sequence.** Only apply a subsystem change to address a confirmed need and follow its current dedicated guide.

See [documentation index](INDEX.md), [kernel-update playbook](kernel-update-playbook.md), and [release-safety checklist](phase4-release-safety.md).
