# Sleep battery drain: EC wakeup experiment (2026-10-23)

**Status: proposed test, not yet applied or validated on hardware.** Do not claim a battery improvement or a working lid-wake behavior.

## Machine observations

- Model: MacBook8,1 (12-inch, Early 2015); CachyOS kernel `7.3.0-2-cachyos`.
- `cat /sys/power/mem_sleep`: `[s2idle] deep` (s2idle is active; deep merely advertised).
- `cat /sys/module/acpi/parameters/ec_no_wakeup`: `N`.
- Current command line includes `mem_sleep_default=s2idle` and the *working, kernel-specific* DesignWare DMA initcall blacklist:
  `initcall_blacklist=dw_pci_driver_init,__initstub__kmod_dw_dmac_pci__437_139_dw_pci_driver_init6,__initstub__kmod_dw_dmac_pci__442_139_dw_pci_driver_init6`.
- Apple ACPI embedded controller initialized; log says `ACPI: EC: GPE=0x4e`. The provided output was EC initialization, **not** evidence of premature wakeups.
- Battery percentage and charge/energy reports have previously disagreed; do not trust a single percentage reading as proof of drain.

Discussion prompting investigation: https://discuss.cachyos.org/t/battery-discharge-in-sleep/4836

## Hypothesis and risks

`acpi.ec_no_wakeup=1` may prevent EC wake interrupts during s2idle. This is **not a proven fix** for this laptop. It can disable lid-related wake events. Suspend, lid reopening, power-button wake, battery usage, and recovery need to be tested. Never casually replace s2idle with deep: Apple SPI keyboard/trackpad resume reliability is a concern, and a working configuration already uses s2idle.

## Test, in order

1. Save work; ensure an alternative way to power on and a known-good boot entry. Unplug charger for drain measurements. Record `date`, `cat /sys/power/mem_sleep`, `cat /sys/module/acpi/parameters/ec_no_wakeup`, `cat /proc/cmdline`, and battery raw values from `/sys/class/power_supply/BAT0/` (`energy_now` or `charge_now`, `voltage_now`, `capacity`, `status`, whichever exist).
2. If writable, enable **runtime only** with `echo Y | sudo tee /sys/module/acpi/parameters/ec_no_wakeup`. Verify it reads `Y`; verify `[s2idle] deep` remains unchanged. If write fails, stop; do not assume it applied.
3. Test one brief suspend, then reopen lid and/or press power to wake. Check keyboard, trackpad, speaker, camera and networking where practical. If unable to resume, use a controlled recovery and revert.
4. Only after reliable resume, make a measured unplugged comparison: same initial charge range and background conditions, identical sleep duration (a longer interval, e.g. several hours, is more informative). Record timestamps, `/sys/class/power_supply/BAT0/` raw units, percentages, and journal suspend entry/exit/wakeup reasons. Beware unreliable battery fuel-gauge values.
5. If safe and demonstrably helpful, **then** consider adding `acpi.ec_no_wakeup=1` to Limine while retaining `mem_sleep_default=s2idle` and the *verified for each installed kernel* DMA workaround. Back up Limine configuration first; verify effective `/proc/cmdline` and wake behavior after reboot. This is a separate approval/test milestone, not a change made in this document.

Rollback of runtime experiment: `echo N | sudo tee /sys/module/acpi/parameters/ec_no_wakeup`, verify `N`. A reboot should also restore boot default if no persistent parameter was added. If the system cannot wake, forced power off risks unsaved data; use only as a last resort. If added persistently later, remove only the new parameter from the boot config and regenerate boot entries following the documented Limine procedure.

## Open evidence checklist

- [ ] Runtime write accepted and read-back `Y`.
- [ ] Short suspend/resume works, including lid/power-button behavior.
- [ ] Repeated resume and peripheral regression checks complete.
- [ ] Baseline and modified measured sleep periods recorded with raw battery values.
- [ ] Logs show real suspend intervals and any EC-related wakes.
- [ ] Decision: revert / retain runtime only / propose persistent Limine setting.
- [ ] If persistent: boot configuration backed up, updated, reboot verified and rollback tested.
- [ ] Hibernation remains independent and **untested**; see [hibernation](hibernation.md).

Do not label this a fix until meaningful measurement and regression testing demonstrate improvement.
