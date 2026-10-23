# Phase 3 — script and service dependency map (2026-10-23)

**Scope:** static review of selected critical script, service and CI references on main at `245c9a59208fd622510072952393f223c8abe554`. This map is a relocation-risk guide, not a complete dynamic-call graph or a fresh hardware test. PR #20 has merged and [GitHub Actions run 39979797152](https://github.com/ltorrecilla/macbook8.1/actions/runs/39979797152) succeeded.

## Concrete relationships

| Source | Depends on / calls | Consequence of changing paths |
|---|---|---|
| `scripts/install-camera.sh` | `scripts/camera-common.sh` via `source "$CAM_SCRIPT_DIR/camera-common.sh"`; DKMS, upstream download tools and firmware locations | Move **with** common helper; relative source and documented commands require changes |
| `scripts/uninstall-camera.sh` | Same `camera-common.sh`, DKMS registration and owned source paths | Critical: uninstall ownership checks must remain intact |
| `scripts/check-camera.sh` | Same `camera-common.sh`; local hardware/DKMS queries | Read-only camera checks should remain easy to run |
| `scripts/install-cpu-limit.sh` | Repository-relative `scripts/cpu-cap-control.sh` and `systemd/macbook81-cpu-cap.service` | Moving either breaks helper source lookup unless installer updated |
| `systemd/macbook81-cpu-cap.service` | Installed helper at `/usr/local/libexec/macbook81-cpu-cap`; `ExecStart ... apply`, `ExecStop ... restore` | Installed service path is **not** repository location; changing it affects installed machines |
| `scripts/cpu-cap-control.sh` | CPUFreq sysfs, config and runtime state files | Preserve restore correctness; nine newly added mocked tests verify state interactions |
| `scripts/repair-audio.py` | Existing registered `macbook12-audio` DKMS source, kernel headers, `dkms install`, `limine-mkinitcpio` | High-risk hardware impact. No path migration until recovery is independently validated |
| `scripts/check-kernel-update.py` | Installed `/usr/lib/modules` kernel images and `/etc/default/limine`; kernel-specific DMA symbols | Keep stable for pre-reboot diagnostics. Seven tests verify simulated old/new kernels |
| `tests/test_camera_scripts.py` | Repository-relative `scripts` directory and camera script names | Moving camera files requires test fixtures and invocation updates |
| `tests/test_cpu_cap_control.py` | Exact path `scripts/cpu-cap-control.sh` | Moving helper requires corresponding regression-test update |
| `.github/workflows/offline-validation.yml` | Glob `scripts/*.sh`, Python glob `scripts/*.py`, and `scripts/check-doc-links.py` | **Nested scripts would no longer receive syntax checks automatically**; update workflow before any move |
| README and `docs/` | Literal `scripts/...` commands and links | Existing users may depend on stable commands; preserve compatibility or retain old paths |

## Recommendation

**Do not physically reorganize executables yet.** The current flat scripts directory is not causing a demonstrated maintenance failure. Organizing navigation through [script reference](script-reference.md), [installation matrix](installation-matrix.md), and [documentation index](INDEX.md) delivers most of the discoverability benefit without breaking installations.

If restructuring becomes necessary, use one subsystem per PR, provide compatibility wrappers at prior script paths, update tests and the CI glob to recursive paths, verify docs and rollback in a clean clone, and only then consider a real MacBook test. Never relocate the installed CPU helper or modify the SPI/DMA blacklist as part of cosmetic repository cleanup.

## Open gates

- [ ] Full dependency search across all tracked text, historical versions and shell imports.
- [ ] Confirm local checkout state, including untracked and ignored files.
- [ ] Test install/uninstall and kernel-update workflows on the original MacBook after backups.
- [ ] Complete pending third-party driver/firmware provenance and private-history scan.
- [ ] Confirm there is measurable benefit before any physical move.

**Decision:** keep script paths stable in Phase 3; continue improving targeted tests instead of introducing unnecessary path churn.
