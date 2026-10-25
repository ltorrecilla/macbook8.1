## Route one normal application through the managed D+ service (experimental)

**Hardware status:** the managed user service has already produced audible sound with the explicit `pw-play --target` test. Ordinary application routing **has not been verified yet**. This tool is a narrow test of that missing step; it does not change D+ DSP, the service, any default device, or WirePlumber configuration.

Use the helper from the repository root, as your **ordinary desktop user** (never `sudo`). Stop any old temporary preview first. Verify that `MacBook_Speaker_Raw` is still the system default and the managed service is running:

```bash
cd ~/git/macbook/macbook8.1
python3 scripts/dplus/manage-native.py status
# If the managed service is stopped, use:
python3 scripts/dplus/manage-native.py start
```

Start a Firefox video with audible playback (not paused). List actual **playing** application streams; unlike the KDE tray menu, this shows the PulseAudio-compatible sink assignment directly:

```bash
python3 scripts/dplus/route-app.py list
```

If Firefox has **exactly one actively playing stream**, route it to D+:

```bash
python3 scripts/dplus/route-app.py dplus --app Firefox
```

If multiple Firefox streams are playing, the helper **refuses to guess**. Copy the exact stream ID from `list` and use `python3 scripts/dplus/route-app.py dplus --id <ID>`. The tool confirms both that the stream's sink actually changed and that Raw remains the system default; it reports failure instead of silently retrying when WirePlumber refuses or reverts the move.

**Restore the application to Raw before stopping the service** (replace the number with the ID shown in the successful route message):

```bash
python3 scripts/dplus/route-app.py raw --id <ID>
python3 scripts/dplus/manage-native.py stop
```

If you see the application's audio fall silent, first try the `raw --id <ID>` reversal. If a stream has disappeared or been recreated with a new ID, run `list` again to identify the current playing stream. The route helper refuses to move an application from headphones/Bluetooth/HDMI, refuses to move an unnamed or known internal bridge (especially `dplus_preview_to_raw`) into D+ where it could create feedback, and refuses to operate when D+ is duplicated, the native service is inactive, Raw is unavailable, or the global default is not Raw. **Never change the KDE global output to D+ for this test.** Some session managers remember application-specific target selection; route back to Raw before ending the test. The tool does not restore routing automatically after wake or application restart.

The routing helper uses only standard Python and `pactl`; its offline safety tests can be run without live audio:

```bash
python3 scripts/dplus/test_route_app.py
```

A successful test means Firefox is audible through D+ while it is running, and normal audio returns when the selected application stream is moved back to Raw. It does **not** establish video synchronization, long-term stability, limiter parity or suspend recovery.
