# MacBook8,1 sleep battery drain — 2026-10-23 tests

**Status: investigated, not fixed.** CachyOS `7.3.0-2-cachyos`; `/sys/power/mem_sleep` reports `[s2idle] deep`. Two actual `s2idle` sessions resumed successfully. Battery readings suggest high sleep consumption. A runtime EC wakeup tweak **may** have lowered consumption, but the brief unmatched measurements do not establish causality. No persistent boot or sleep setting is recommended yet.

## What was discovered

- **KDE PowerDevil controls lid actions.** Lid close originally requested hibernation, with an unsuccessful apparent restore/fresh boot. A subsequent choice selected **hybrid-sleep**, which resumed, but was not a valid plain suspend baseline. Changing KDE to **Standby** produced logged `PM: suspend entry (s2idle)` and `PM: suspend exit`.
- **Use the battery exposed by the actual driver:** `/sys/class/power_supply/macsmc-battery`, not `BAT0`. Its `energy_now` field is in micro-Wh. `power_now` is unsupported (error -95) and should not be queried repeatedly. Battery percentage/energy readings have previously been inconsistent.
- EC workaround under consideration: runtime `acpi.ec_no_wakeup=1` (the sysfs parameter is `/sys/module/acpi/parameters/ec_no_wakeup`); it may change lid-triggered wake behavior and has **not** been justified as a permanent Limine argument. Discussion: https://discuss.cachyos.org/t/battery-discharge-in-sleep/4836

## Two short measurements

| Item | Ordinary s2idle, EC=N | Second s2idle, EC=Y assumed |
|---|---:|---:|
| Battery before (local time) | 21:12:48; 37,637,875 µWh; 96% | 21:28:34; 36,018,422 µWh; 92% |
| Battery after (local time) | 21:24:09; 36,810,840 µWh; 94% | 21:36:40; 35,511,350 µWh; 91% |
| Suspend entry / exit | 21:13:19 / 21:23:55 | 21:28:44 / 21:36:24 |
| Actual suspend duration | 636 s (10m36s) | 460 s (7m40s) |
| Full measurement interval | 681 s | 486 s |
| Energy lost over **full** interval | 0.827035 Wh | 0.507072 Wh |
| Energy / suspend time (biased power estimate) | 4.68 W | 3.97 W |
| Energy / full measurement interval | 4.37 W | 3.76 W |
| Resume | Confirmed via same-boot log | Confirmed via same-boot log |

**Interpretation:** estimated power is about 14–15% lower in the second interval, but **neither estimate is a measurement of suspend-only power**. Both battery samples include awake time before/after suspend. The tests differ in duration, battery charge state, and prior activity; the fuel gauge is imperfect. The user did not include a direct readback confirming `ec_no_wakeup=Y` during test two; it is inferred from the intended procedure. The consumption is still high even under that assumption.

The earlier hybrid-sleep measurement must **not** be compared as if it were plain s2idle. The machine was reported warm during the earlier non-plain-suspend test.

## Safety and next steps

1. **Return to baseline if still enabled:** `echo N | sudo tee /sys/module/acpi/parameters/ec_no_wakeup`, then verify `cat /sys/module/acpi/parameters/ec_no_wakeup`. This runtime change is not in Limine.
2. Keep KDE lid close set to **Standby**, not Hibernate, Hybrid Sleep, or Suspend-then-Hibernate until resume reliability is established. Preserve working `mem_sleep_default=s2idle` and the kernel-specific DesignWare DMA `initcall_blacklist`.
3. For any later comparison, log the **actual** EC value immediately before and after each interval, require similar charge level and equal suspend durations, minimize awake measurement overhead, and record `date -Is`, `energy_now`, `charge_now`, `capacity`, and the journal suspend timestamps.
4. If repeated tests still show high drain, investigate device/runtime power states and wake events. Do not assume the EC is responsible merely because ACPI advertises wake-capable devices.
5. **Do not permanently add `acpi.ec_no_wakeup=1` to Limine** or switch to `deep` on the basis of these two tests. Test wake from lid and power button separately before any persistent change.

Hibernation is separate and remains experimentally configured/unverified for reliable restore; see [hibernation notes](hibernation.md). The original per-kernel DMA workaround stays intact. No script or installed configuration was modified by this documentation update.
