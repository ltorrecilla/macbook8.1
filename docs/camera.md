# FaceTime HD camera on MacBook8,1

**Live camera capture works on the owner's Early 2015 12-inch MacBook. Application discovery is still being investigated.** On 2026-10-18, the owner confirmed a normal moving image in `mpv` after installing the `facetimehd` driver and the firmware described below. An unnamed camera app subsequently reported no devices; its name, installation method, and diagnostic outputs have not yet been supplied.

The hardware confirmation comes from the original **manual installation**. The optional scripts added to this repository reproduce that driver/firmware combination with additional checks, but have not themselves been tested on the physical laptop. Browser, Flatpak, reboot, suspend/resume, and kernel-update behavior are not confirmed by the `mpv` test.

## Confirmed setup

| Item | Observed or installed state |
|---|---|
| Model | `MacBook8,1` — 12-inch, Early 2015 |
| Camera | Broadcom PCIe FaceTime HD, PCI ID `14e4:1570`, at `02:00.0` on this machine |
| OS/kernel | CachyOS, `7.2.9-2-cachyos` |
| Kernel packages | `linux-cachyos 7.2.9-2` and `linux-cachyos-headers 7.2.9-2` |
| DKMS tool | `3.4.3-1` |
| Driver source | Upstream [`patjak/facetimehd` release `0.7.2`](https://github.com/patjak/facetimehd/releases/tag/0.7.2) |
| DKMS package identity | `facetimehd/0.7.0.1` — the version declared in that release's `dkms.conf` |
| Firmware | `5.60.0`, extracted using `patjak/facetimehd-firmware` |
| Sensor calibration | `1675_01XX.dat`, included in the upstream extraction |
| Live test | `mpv av://v4l2:/dev/video0`: moving image, reported `848x588`, 30 fps |

Before installation, `lspci` detected the camera but `modinfo facetimehd` failed, `/usr/lib/firmware/facetimehd` was absent, and `/sys/class/video4linux` was absent. Those findings established that the driver and firmware were missing.

The `848x588` mode is what this test reported; it is not a claim about the sensor's maximum resolution or a mode that every application must use.

## If the camera already works in mpv

Run the diagnostic helper from this repository:

```sh
bash scripts/check-camera.sh
```

There is no need to reinstall the working manual setup merely to use these scripts. If another app still reports no devices, continue with [application discovery](#application-discovery-still-open).

The checker returns a nonzero status if a core module, expected firmware/calibration file, or camera video node is missing or cannot be verified. Read its output to identify the failing check; it does not install or load a driver, change permissions, or restart services.

The installer does not take ownership of an existing manual or package-managed installation. When the required firmware and current-kernel module are already present, it reports that state and exits. Conflicting or incomplete existing installations need diagnosis before replacement.

## Optional installation on a matching MacBook

Run the following commands on the CachyOS laptop, from the repository directory. Explicit `bash` invocations also work when the interactive shell is fish. The installer supports `MacBook8,1` with camera ID `14e4:1570`; this repository has not validated other models.

### 1. Install prerequisites and check the running kernel

```sh
sudo pacman -S --needed base-devel dkms git curl xz gzip which v4l-utils mpv psmisc

uname -r
pacman -Q linux-cachyos linux-cachyos-headers dkms
```

Install the header package for the kernel you actually run. For the regular CachyOS kernel it is `linux-cachyos-headers`; a different kernel flavor needs its corresponding headers. The original installation already had matching kernel and header packages, so no kernel change was needed.

If the regular CachyOS kernel's headers are missing:

```sh
sudo pacman -S --needed linux-cachyos-headers
```

If you have updated the installed kernel since boot, reboot into that kernel before building against its headers. Do not force a build against headers for a different kernel. The helper checks the running kernel's build directory and release before installation; it does not update the operating system or install packages.

### 2. Run the optional installer as your ordinary user

```sh
bash scripts/install-camera.sh
```

Do not prefix this command with `sudo`: downloads and firmware extraction run as the ordinary user, and the script uses `sudo` for its system installation steps.

The installer uses fixed upstream revisions:

| Source | Pinned revision |
|---|---|
| `patjak/facetimehd`, release `0.7.2` | [`54fb8f25fcf76d4d5af682875f044dc0b6fa0b65`](https://github.com/patjak/facetimehd/tree/54fb8f25fcf76d4d5af682875f044dc0b6fa0b65) |
| `patjak/facetimehd-firmware` extractor | [`60ee21228d9ca00a7bd84fdaefaff00a81f1db91`](https://github.com/patjak/facetimehd-firmware/tree/60ee21228d9ca00a7bd84fdaefaff00a81f1db91) |

It downloads the source into a fresh temporary directory, extracts firmware with `make FW_VER=5.60.0`, checks the expected firmware/calibration hashes, installs the two required files, and builds the module for the running kernel using DKMS. Temporary downloads are removed when the script exits.

System paths used by this installation are:

| Path | Purpose |
|---|---|
| `/usr/lib/firmware/facetimehd/firmware.bin` | Firmware `5.60.0` |
| `/usr/lib/firmware/facetimehd/1675_01XX.dat` | Calibration data needed for this model |
| `/usr/src/facetimehd-0.7.0.1` | Driver source registered with DKMS |
| `/usr/src/facetimehd-0.7.0.1/.macbook81-camera-owner` | Marker identifying source installed by this wrapper |
| `/usr/src/facetimehd-0.7.0.1/.macbook81-camera-sha256` | Recorded source checksums, verified before retry/removal |

Existing firmware files with matching contents are preserved. Different contents, symbolic links/compressed firmware copies, or conflicting driver ownership cause the installer to stop for inspection. Firmware and calibration binaries are downloaded/extracted on the laptop; they are not distributed in this repository.

The original manual procedure installed all sensor files produced by the upstream firmware Makefile. This wrapper installs only `firmware.bin` and `1675_01XX.dat`, the pair required here. It preserves other existing calibration files.

The driver release number and DKMS version are deliberately different: upstream release `0.7.2` still declares `PACKAGE_VERSION=0.7.0.1` in its [`dkms.conf`](https://github.com/patjak/facetimehd/blob/54fb8f25fcf76d4d5af682875f044dc0b6fa0b65/dkms.conf). Do not substitute `0.7.2` in commands that select this DKMS registration.

### 3. Verify live capture

```sh
dkms status -m facetimehd
sudo modprobe facetimehd
v4l2-ctl --list-devices
```

For the originally tested kernel, DKMS should report an installed entry such as:

```text
facetimehd/0.7.0.1, 7.2.9-2-cachyos, x86_64: installed
```

Use the device path reported by `v4l2-ctl`; it was `/dev/video0` on the owner's machine:

```sh
mpv av://v4l2:/dev/video0
```

Confirm that the image moves normally, then close `mpv` before opening another camera app. A device listing or a progressing playback timer alone does not establish a usable picture.

The successful test logged a Mesa `FINISHME` warning, pixel-format conversion from `yuyv422` to `yuv422p`, and buffer/`VIDIOC_QBUF` messages during shutdown. The owner still saw a live image. Preserve those messages if reporting a problem, but their presence in that successful run is not a reason on its own to replace the driver.

## Application discovery: still open

**The unnamed app's “no devices” result remains unresolved.** Successful direct V4L2 capture in `mpv` does not establish that an app using a different camera backend or a sandbox can discover/access the camera.

First close `mpv` completely, then fully quit and reopen the other camera app. If it still fails, record the exact app name and version, and whether it came from `pacman`, Flatpak, or another source. Run:

```sh
v4l2-ctl --list-devices
wpctl status
fuser -v /dev/video0
```

Replace `/dev/video0` if the device listing gives a different path. `fuser` is supplied by `psmisc`; no output can mean that it found no process holding the device open. Some process details may be hidden from an unprivileged user. A listed process does not by itself prove a capture conflict; PipeWire may legitimately hold the device open.

These results distinguish the kernel's camera listing, PipeWire's video sources, and processes currently using the device. WirePlumber's [camera configuration documentation](https://pipewire.pages.freedesktop.org/wireplumber/daemon/configuration/video.html) describes its V4L2/libcamera discovery and sandbox access controls. A camera missing from PipeWire is relevant to apps that use PipeWire, while direct V4L2 apps use a different access path.

Choose an app-specific fix after obtaining those results. No PipeWire/WirePlumber restart, replacement of audio configuration, broad device-permission change, or Flatpak override has been validated as the fix for this open issue. The camera helpers do not alter the working speaker configuration.

## Driver loading or update problems

For a missing video device or module initialization failure, collect:

```sh
bash scripts/check-camera.sh
sudo journalctl -k -b --no-pager -g 'facetimehd|fthd|1570|DMAR|IOMMU' -n 100
```

The [upstream firmware extractor](https://github.com/patjak/facetimehd-firmware/blob/60ee21228d9ca00a7bd84fdaefaff00a81f1db91/extract-firmware.sh) explicitly requires **firmware `5.60.0`** for the 12-inch MacBook and identifies `1675_01XX.dat` as its sensor calibration file. An older firmware package is not a substitute just because it provides a file named `firmware.bin`. The helper checks the known contents rather than relying only on the filename.

The pinned upstream `dkms.conf` sets `AUTOINSTALL="yes"`, so DKMS is configured to rebuild the registered module for kernels whose matching headers are installed. Release `0.7.2` explicitly adds Linux 7.2 build compatibility. Neither fact guarantees that a future kernel change will remain compatible. Keep matching headers installed and check DKMS build results after updates.

Reboot and suspend/resume behavior still need physical testing. If the camera stops working after either event, collect the current kernel, DKMS status, and camera kernel messages before attempting a reinstall. Do not assume the existing audio recovery scripts apply to the camera.

If a new wrapper installation stops during the build, it retains its owned source and any DKMS state for diagnosis. Read the DKMS build log path printed by the installer, correct the reported problem, and retry `bash scripts/install-camera.sh`. Source checksum changes or conflicting installations cause a retry to stop for inspection. Use the removal helper below if you decide to remove the wrapper-owned driver instead; installed firmware is retained.

## Removal

For a driver installed by this repository's wrapper:

```sh
sudo bash scripts/uninstall-camera.sh
```

Close camera applications first. Removal is restricted to the driver/source carrying the wrapper's ownership marker and matching recorded source checksums. A busy driver or changed source requires inspection before removal can continue. The helper leaves firmware, calibration files, and distribution packages in place. It refuses to remove an existing manual installation that it did not create; there is no force/adoption option.

The install, check, and uninstall helpers accept `--help` (or `-h`); there are no installation/removal override options. The source/firmware downloads and optional installation are separate from the CPU limiter and ongoing audio work.

## Local script validation

The camera tests exercise installation guards, preservation of existing files, retries, rollback, and read-only diagnostics using temporary fixtures:

```sh
python3 -m unittest discover -s tests -p 'test_camera_scripts.py' -v
```

Git, firmware extraction, sudo, DKMS, and module operations are simulated. These tests require neither root nor camera hardware; they do not replace a real kernel build or physical camera test.

## Upstream references

- [Driver release `0.7.2`, including Linux 7.2 build compatibility](https://github.com/patjak/facetimehd/releases/tag/0.7.2).
- [Pinned driver DKMS configuration](https://github.com/patjak/facetimehd/blob/54fb8f25fcf76d4d5af682875f044dc0b6fa0b65/dkms.conf).
- [Pinned firmware Makefile: download, `FW_VER=5.60.0`, and installation](https://github.com/patjak/facetimehd-firmware/blob/60ee21228d9ca00a7bd84fdaefaff00a81f1db91/Makefile).
- [Pinned firmware extractor: supported models, sensor files, and checksums](https://github.com/patjak/facetimehd-firmware/blob/60ee21228d9ca00a7bd84fdaefaff00a81f1db91/extract-firmware.sh).
- [WirePlumber video and camera configuration](https://pipewire.pages.freedesktop.org/wireplumber/daemon/configuration/video.html).

The driver and extraction work are upstream projects. This repository supplies a CachyOS installation wrapper and the owner's validation record; upstream licenses continue to apply to downloaded code and firmware.
