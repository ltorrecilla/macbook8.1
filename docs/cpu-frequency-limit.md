# Optional CPU frequency ceiling

On the tested MacBook8,1 (Core M-5Y51), the CPUFreq policy originally allowed up to 2.60 GHz. The installer checks the model and hardware limits, leaves the governor intact and enables a systemd oneshot cap on startup.

```bash
sudo bash scripts/install-cpu-limit.sh 1600
bash scripts/check-cpu-limit.sh
sudo bash scripts/uninstall-cpu-limit.sh
```

Suggested frequency ceilings in MHz: 1300, 1600 (default), 2000. These are **not measured thermal targets**. Service files are `/etc/systemd/system/macbook81-cpu-cap.service`, `/usr/local/libexec/macbook81-cpu-cap`, and `/etc/macbook81-cpu-cap.max-khz`.

Other CPU management utilities may overwrite the cap. Check after each reboot and suspend/resume; when necessary, reapply with `sudo systemctl restart macbook81-cpu-cap.service`. Kernel thermal protections are untouched. Initial installation was verified by the owner; update and resume persistence still need testing.
