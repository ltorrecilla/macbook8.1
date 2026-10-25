#!/usr/bin/env python3
"""Topology-corrected native D+ listening trial for direct PCM only.

Fix: 2-stage copy graph outputs; does not change EQ,
limiter, channel mapping, conservative gain or default-node safety policy.

No autostart, PipeWire service restart, kernel changes, privileged commands,
or root access. Optional --restore-raw-on-wake changes the global default ONLY
from this exact preview node back to Raw, and at most once per wake.
Experimental reduced-gain preview only;
not a source-identical or speaker-certified D+ v4 release.

Commands: --check, --show-config, --start [--restore-raw-on-wake]. Requires privately held approved JSON
reference and an installed LSP Limiter Stereo LV2 plugin for --start.
"""
from __future__ import annotations
import argparse
import cmath
import json
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time

RAW = "MacBook_Speaker_Raw"
SINK = "MacBook_Speaker_D_Preview"
STREAM = "dplus_preview_to_raw"
ENGINE_SHA = "43da928c7b1b7cd1b1628e47276820dcb2eeeeb841136a425ea25d280ec4076b"
URI = "http://lsp-plug.in/plugins/lv2/limiter_stereo"
IN_RATE, GRAPH_RATE = 44100, 48000
COEF = ("b0", "b1", "b2", "a0", "a1", "a2")
# Four magnitude-only EQ corrections, tuned OFFLINE against the approved 44.1 kHz
# filter-chain over 600 logarithmic points 20..20000 Hz. NOT phase/limiter parity.
CORRECTIONS = (
    (4360.671910562485, 6.6227714539280855, -0.17816690279308145),
    (12540.723136790977, 0.7018842114192533, -7.326963131642182),
    (13406.669726713573, 0.5834551154267515, 7.116159652713059),
    (20599.027318228822, 0.7326051917863593, 1.8716124944527166),
)
# SAFETY: no original +8.31 dB pregain until live limiter equivalence measured.
# Limiter output is further attenuated, with a final hard maximum as a backstop.
LIM_IN = 1.0
LIM_OUT = 0.35
LIMIT = 0.6683439175686147
FINAL_CLAMP = 0.45


class PreviewError(RuntimeError):
    pass


def profile_rows(path):
    p = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    if p.get("source", {}).get("file_sha256") != ENGINE_SHA:
        raise PreviewError("Reference file identity differs from the approved D+ engine")
    if p.get("input", {}).get("rate_hz") != IN_RATE:
        raise PreviewError("Profile is not the approved 44100-Hz reference")
    stages = p.get("stages", [])
    if len(stages) != 9 or [x.get("type") for x in stages] != [
        "biquad_cascade", "equalizer", "gain", "resample", "limiter",
        "resample", "gain", "channel_mapping", "resample_format"]:
        raise PreviewError("Unexpected D+ processing stage sequence")
    if (stages[1].get("gain_db") != 1.0 or stages[1].get("frequency_hz") != 3000 or
        stages[2].get("db") != 8.310000000000002 or
        stages[4].get("limit_linear") != LIMIT or
        stages[7].get("positions") != ["FL", "FR", "RL", "RR"]):
        raise PreviewError("D+ source parameters changed; refusing unsupported profile")
    rows = stages[0].get("coefficients")
    if not isinstance(rows, list) or len(rows) != 11:
        raise PreviewError("Expected eleven reference biquad stages")
    for row in rows:
        if not isinstance(row, dict) or set(row) != set(COEF):
            raise PreviewError("Unexpected coefficient keys")
        if any(isinstance(v, bool) or not isinstance(v, (int,float)) or
               not math.isfinite(v) for v in row.values()) or row["a0"] != 1.0:
            raise PreviewError("Invalid biquad coefficients")
    return rows


def rate_convert(r):
    ratio = GRAPH_RATE / IN_RATE
    p, q = 1 - ratio, 1 + ratio
    def trans(prefix):
        a,b,c = (r[prefix + str(i)] for i in range(3))
        return (a*q*q + b*p*q + c*p*p,
                2*a*p*q + b*(p*p+q*q) + 2*c*p*q,
                a*p*p + b*p*q + c*q*q)
    num, den = trans("b"),trans("a")
    if den[0] == 0:
        raise PreviewError("Unstable rate conversion")
    result=dict(zip(COEF, (v/den[0] for v in (*num,*den))))
    a1,a2=result["a1"],result["a2"]
    poles=[(-a1+sgn*cmath.sqrt(a1*a1-4*a2))/2 for sgn in (1,-1)]
    if not all(math.isfinite(v) for v in result.values()) or any(abs(z)>=1 for z in poles):
        raise PreviewError("Rate conversion produces unstable coefficients")
    return result


def peaking(freq,q,gain):
    a=10**(gain/40)
    w=2*math.pi*freq/GRAPH_RATE
    alpha=math.sin(w)/(2*q)
    c=math.cos(w)
    num=(1+alpha*a,-2*c,1-alpha*a)
    den=(1+alpha/a,-2*c,1-alpha/a)
    return dict(zip(COEF,(x/den[0] for x in (*num,*den))))


def response_db(rows, rate, freq):
    z=cmath.exp(-2j*math.pi*freq/rate)
    h=complex(1)
    for r in rows:
        h*= (r["b0"]+r["b1"]*z+r["b2"]*z*z)/(r["a0"]+r["a1"]*z+r["a2"]*z*z)
    return 20*math.log10(abs(h))


def transformed(rows):
    converted=[rate_convert(r) for r in rows]
    converted.extend(peaking(*spec) for spec in CORRECTIONS)
    diffs=[]
    for index in range(600):
        freq=20*(1000**(index/599))
        diffs.append(abs(response_db(rows,IN_RATE,freq)-response_db(converted,GRAPH_RATE,freq)))
    error=max(diffs)
    if error>0.12:
        raise PreviewError(f"48k response fit exceeds tolerance: {error:.4f} dB")
    return converted,error


def row_node(name,row):
    coeff=" ".join(f'{key} = {row[key]:.17g}' for key in COEF)
    return (f'    {{ type = builtin name = {name} label = bq_raw\n'
            f'      config = {{ coefficients = [ {{ rate = {GRAPH_RATE} {coeff} }} ] }}\n'
            f'    }}')


def generate_config(profile):
    rows=profile_rows(profile)
    coeffs,error=transformed(rows)
    nodes=[];links=[]
    for side in ("L","R"):
        for i,row in enumerate(coeffs):
            name=f"{side}{i+1:02d}"
            nodes.append(row_node(name,row))
            if i:
                links.append(f'    {{ output = "{side}{i:02d}:Out" input = "{name}:In" }}')
        # additional +1 dB presence is NOT part of the 11 source rows
        nodes.append(row_node(f"{side}Presence",peaking(3000,1,1)))
        links.append(f'    {{ output = "{side}{len(coeffs):02d}:Out" input = "{side}Presence:In" }}')
        links.append(f'    {{ output = "{side}Presence:Out" input = "lim:in_{side.lower()}" }}')
        nodes.append(f'    {{ type = builtin name = clip{side} label = clamp\n'
                     f'      control = {{ "Min" = {-FINAL_CLAMP} "Max" = {FINAL_CLAMP} }} }}')
        links.append(f'    {{ output = "lim:out_{side.lower()}" input = "clip{side}:In" }}')
        nodes.append(f'    {{ type = builtin name = zero{side} label = linear\n'
                     f'      control = {{ "Mult" = 0 "Add" = 0 }} }}')
        # A graph output may NOT also be an internal link source. The first
        # copy is an INTERNAL tee; its only consumers are internal filters.
        # PipeWire's sink-make-LFE.conf uses this exact two-copy pattern:
        # copyIL:Out branches internally, copyOL:Out feeds the graph output.
        nodes.append(f'    {{ type = builtin name = copy{side} label = copy }}')
        nodes.append(f'    {{ type = builtin name = copyOut{side} label = copy }}')
        links.append(f'    {{ output = "clip{side}:Out" input = "copy{side}:In" }}')
        links.append(f'    {{ output = "copy{side}:Out" input = "zero{side}:In" }}')
        links.append(f'    {{ output = "copy{side}:Out" input = "copyOut{side}:In" }}')
    # LSP limiter: stereo-linked, oversampling half-x4, lookahead 5ms,
    # attack 5ms, release 80ms; conservative output gain instead of +8.31 dB.
    nodes.append('    { type = lv2 name = lim\n'
                 f'      plugin = "{URI}"\n'
                 '      control = { "bypass" = 0 "alr" = 0 "boost" = 0\n'
                 f'                  "g_in" = {LIM_IN} "g_out" = {LIM_OUT}\n'
                 f'                  "th" = {LIMIT:.17g} "at" = 5 "rt" = 80\n'
                 '                  "lk" = 5 "slink" = 100 "ovs" = 5 "dith" = 0 } }')
    graph='''# Generated from a private D+ profile. Temporary opt-in PREVIEW ONLY.
# Different limiter; no +8.31dB pregain; not source-identical D+ v4.
# Must be run as a filter-chain CLIENT with existing WirePlumber session.
context.properties = { log.level = 1 }
context.spa-libs = {
  audio.convert.* = audioconvert/libspa-audioconvert
  support.* = support/libspa-support
}
context.modules = [
 { name = libpipewire-module-rt flags = [ ifexists nofail ] }
 { name = libpipewire-module-protocol-native }
 { name = libpipewire-module-client-node }
 { name = libpipewire-module-adapter }
 { name = libpipewire-module-filter-chain
   args = {
     node.description = "MacBook8,1 D+ safe EQ preview"
     filter.graph = {
       nodes = [
'''
    graph+='\n'.join(nodes)+'\n       ]\n       links = [\n'+'\n'.join(links)+'\n       ]\n'
    graph+=('       inputs = [ "L01:In" "R01:In" ]\n'
             '       outputs = [ "copyOutL:Out" "copyOutR:Out" "zeroL:Out" "zeroR:Out" ]\n'
             '     }\n'
             '     capture.props = {\n'
             f'       node.name = "{SINK}"\n'
             '       node.description = "MacBook D+ EQ preview (low gain)"\n'
             '       media.class = "Audio/Sink"\n'
             '       priority.session = -200\n'
             '       node.autoconnect = false\n'
             '       audio.channels = 2\n'
             '       audio.position = [ FL FR ]\n'
             '     }\n'
             '     playback.props = {\n'
             f'       node.name = "{STREAM}"\n'
             '       media.class = "Stream/Output/Audio"\n'
             '       node.passive = true\n'
             '       node.dont-fallback = true\n'
             '       node.dont-move = true\n'
             '       node.dont-reconnect = true\n'
             f'       target.object = "{RAW}"\n'
             '       audio.format = "S16LE"\n'
             '       audio.rate = 44100\n'
             '       audio.channels = 4\n'
             '       audio.position = [ FL FR RL RR ]\n'
             '     }\n   }\n }\n]\n')
    return graph,error


def available_plugin():
    tool=shutil.which("lv2ls")
    if tool:
        try:
            result=subprocess.run([tool],capture_output=True,text=True,timeout=5)
            if result.returncode==0 and URI in result.stdout.splitlines():
                return True
        except (OSError,subprocess.TimeoutExpired):
            pass
    # Fall back to local manifest text, do not blindly assume a package is present.
    for base in (Path.home()/".lv2",Path("/usr/lib/lv2"),Path("/usr/local/lib/lv2")):
        if not base.is_dir():continue
        for manifest in base.glob("*/*.ttl"):
            try:
                if URI in manifest.read_text(encoding="utf-8",errors="replace"):
                    return True
            except OSError:
                continue
    return False


def get_default():
    r=subprocess.run(["pactl","get-default-sink"],capture_output=True,text=True,timeout=5,check=True)
    return r.stdout.strip()


def sink_names():
    r=subprocess.run(["pactl","list","short","sinks"],capture_output=True,text=True,timeout=5,check=True)
    return [line.split()[1] for line in r.stdout.splitlines() if len(line.split())>=2]


def preview_name(names):
    return next((n for n in (SINK, "input." + SINK) if n in names), None)


def preflight(profile,live=False):
    config,error=generate_config(profile)
    required=("pipewire","pactl") if live else ()
    missing=[t for t in required if not shutil.which(t)]
    if missing:raise PreviewError("Missing commands: "+", ".join(missing))
    if live:
        if os.geteuid()==0:raise PreviewError("Never run as root/sudo")
        if not available_plugin():
            raise PreviewError("LSP Limiter Stereo LV2 missing. Check: pacman -Q lsp-plugins-lv2")
        if get_default()!=RAW:raise PreviewError("Raw must be default for opt-in audition")
        current=sink_names()
        if RAW not in current:raise PreviewError("Raw physical sink absent")
        if preview_name(current):raise PreviewError("Preview sink already exists; stop its owning process")
        for key in ("PIPEWIRE_CONFIG_DIR","PIPEWIRE_REMOTE","PIPEWIRE_RUNTIME_DIR"):
            if os.environ.get(key):raise PreviewError("Inherited PipeWire environment override "+key+"; refusing")
    return config,error


# Experimental suspend/wake supervisor; no daemon is installed, no auto-default.
# A lost Raw node cannot be healed by this user-space program; it can only
# restart its own PipeWire client when Raw has returned.
RESUME_JUMP_SECONDS = 1.5
RAW_RETURN_TIMEOUT = 30.0
MAX_RECOVERIES = 3
MAX_RAW_DEFAULT_RESTORES_PER_WAKE = 1


def sleep_clock_offset():
    """CLOCK_BOOTTIME counts suspended time; MONOTONIC does not on Linux."""
    if not hasattr(time, "CLOCK_BOOTTIME"):
        return None
    return time.clock_gettime(time.CLOCK_BOOTTIME) - time.monotonic()


def wake_detected(previous, current, threshold=RESUME_JUMP_SECONDS):
    return previous is not None and current is not None and current - previous >= threshold


def stop_child(proc):
    """Stop ONLY the child PipeWire client we created (no global service)."""
    if proc is None:
        return
    if proc.poll() is None:
        proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(timeout=4)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=3)


def child_log_tail(log_path, limit=1600):
    try:
        return log_path.read_text(encoding="utf-8", errors="replace")[-limit:]
    except OSError:
        return "(log unavailable)"


def graph_activation_error(log_path):
    """Recognize previously reproduced fatal filter-graph activation errors.

    This is deliberately narrow; absence of these errors is NOT proof of PCM
    flow, and user playback validation remains mandatory.
    """
    if log_path is None:
        return None
    try:
        for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
            if "already used by link" in line or "can't start graph" in line:
                return line.strip()
    except OSError:
        pass
    return None


def is_preview_default(name):
    return name in (SINK, "input." + SINK)


def restore_raw_only_if_own_preview(default, names, budget):
    """Optionally undo ONLY this preview becoming default during a known wake.

    Never override a different explicitly selected device, never run at login,
    and never change the default unless the owner opted in and Raw is present.
    A mutable one-element remaining budget prevents repeated reassignments.
    """
    if default == RAW:
        return False
    if not is_preview_default(default):
        raise PreviewError(f"Global default is {default!r}, not Raw; preserving other device selection")
    if RAW not in names:
        raise PreviewError(f"Preview became default but Raw is absent; stopping, no output changed")
    if budget is None or budget[0] <= 0:
        raise PreviewError(
            f"Default changed to our preview {default!r} during wake; "
            "automatic restoration is disabled or budget exhausted. "
            "Select Raw globally before retrying."
        )
    # Consume exactly one permitted correction before invoking the command.
    budget[0] -= 1
    subprocess.run(["pactl", "set-default-sink", RAW], check=True,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                   text=True, timeout=5)
    print("Wake recovery: this preview became the default; restored Raw explicitly "
          "(one opt-in correction).", flush=True)
    return True


def wait_for_raw(timeout=RAW_RETURN_TIMEOUT, interval=0.5, restore_budget=None):
    """Wait for Raw, with one optional correction of only our own preview.

    No default is changed without --restore-raw-on-wake. Selection of any
    OTHER output (headphones, Bluetooth, USB, HDMI) is always respected.
    """
    until = time.monotonic() + timeout
    last = "PipeWire not responding"
    while time.monotonic() < until:
        try:
            default = get_default()
            names = sink_names()
            if RAW in names and default == RAW:
                return True
            if RAW in names and default != RAW:
                restore_raw_only_if_own_preview(default, names, restore_budget)
                last = "Waiting for Raw default to settle"
            else:
                last = f"Raw missing; current default={default!r}"
        except subprocess.SubprocessError:
            last = "PipeWire restarting or not responding"
        time.sleep(interval)
    raise PreviewError("Raw did not return within recovery limit (" + last + ")")


def wait_for_preview_seen(proc, timeout=12.0, interval=0.25,
                          restore_budget=None):
    """Wait for preview registration; retry transient post-wake API failures.

    No global default changes except a narrowly scoped and explicitly opt-in
    correction if the temporary preview itself became the default after wake.
    """
    deadline = time.monotonic() + timeout
    last = "Preview not yet registered"
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise PreviewError("D+ client exited during startup")
        try:
            default = get_default()
            names = sink_names()
        except subprocess.SubprocessError as exc:
            last = f"PulseAudio endpoint unavailable ({type(exc).__name__})"
            time.sleep(interval)
            continue
        if default != RAW:
            restore_raw_only_if_own_preview(default, names, restore_budget)
            last = "Waiting for Raw default after one explicit recovery"
        elif RAW not in names:
            last = "Raw disappeared while creating D+"
        elif preview_name(names):
            return True
        else:
            last = "Preview not yet registered"
        time.sleep(interval)
    raise PreviewError("D+ output did not reappear within startup limit (" + last + ")")


def wait_for_stale_preview_clear(timeout=5.0):
    """Never claim ownership of or unload an unknown/leftover preview node."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if not preview_name(sink_names()):
                return
        except subprocess.SubprocessError:
            pass
        time.sleep(0.2)
    raise PreviewError("Old preview sink still exists; refusing second client")


def start(profile, restore_raw_on_wake=False):
    conf, error = preflight(profile, live=True)
    with tempfile.TemporaryDirectory(prefix="dplus-live-resume-preview-") as work:
        folder = Path(work)
        cfg = folder / "preview.conf"
        cfg.write_text(conf, encoding="utf-8")
        env = os.environ.copy()
        env["PIPEWIRE_CONFIG_DIR"] = work
        env["PIPEWIRE_REMOTE"] = "pipewire-0"
        env.pop("PIPEWIRE_DAEMON", None)
        env.pop("PIPEWIRE_CORE", None)
        proc = None
        current_log = None
        open_log = None
        starts = 0
        recoveries = 0
        last_offset = sleep_clock_offset()
        restore_budget = [0]
        wake_recovery_grace_until = 0.0

        def launch(recovery=False):
            nonlocal proc, current_log, open_log, starts, restore_budget
            # The audio server and the Pulse compatibility socket often return
            # at different moments after resume. Both queries must succeed
            # before starting; after starting, intermittent pactl failures are
            # retried for a strictly bounded 12 seconds.
            if recovery:
                wait_for_raw(restore_budget=restore_budget)
            wait_for_stale_preview_clear()
            if recovery:
                wait_for_raw(restore_budget=restore_budget)
            elif get_default() != RAW or RAW not in sink_names():
                raise PreviewError("Raw must be present and default before starting D+")
            starts += 1
            current_log = folder / f"client-{starts}.log"
            open_log = current_log.open("w", encoding="utf-8")
            try:
                proc = subprocess.Popen(
                    ["pipewire", "-c", "preview.conf"], env=env,
                    stdin=subprocess.DEVNULL, stdout=open_log,
                    stderr=subprocess.STDOUT, start_new_session=True)
                wait_for_preview_seen(proc, restore_budget=restore_budget if recovery else None)
            except BaseException:
                stop_child(proc)
                raise

        def stop_current():
            nonlocal proc, open_log
            stop_child(proc)
            proc = None
            if open_log is not None:
                open_log.flush()
                open_log.close()
                open_log = None

        def restart_after_wake(reason):
            nonlocal last_offset, recoveries, restore_budget, wake_recovery_grace_until
            recoveries += 1
            if recoveries > MAX_RECOVERIES:
                raise PreviewError("Too many recovery attempts; stopping instead of looping")
            print("Detected " + reason + "; restarting only the temporary D+ client.", flush=True)
            restore_budget = [MAX_RAW_DEFAULT_RESTORES_PER_WAKE if restore_raw_on_wake else 0]
            stop_current()
            launch(recovery=True)
            last_offset = sleep_clock_offset()
            wake_recovery_grace_until = time.monotonic() + 8.0
            print("D+ preview recreated after recovery. Re-select your application output in KDE if needed.", flush=True)

        try:
            launch()
            print("Sink registered: " + (preview_name(sink_names()) or SINK) +
                  " (original +1 dB, AUDIO NOT YET VERIFIED)", flush=True)
            print("Test with pw-play --target=" + SINK + " in a separate terminal; no KDE selection.", flush=True)
            print("Do NOT select D+ in KDE for this test; only use pw-play --target.", flush=True)
            print("Raw remains the global default. Ctrl+C stops the trial. No suspend test yet.", flush=True)
            if restore_raw_on_wake:
                print("Opt-in: after wake, may reset the global default ONCE only if this preview was auto-selected.", flush=True)
            while True:
                now = sleep_clock_offset()
                woke = wake_detected(last_offset, now)
                last_offset = now
                if woke:
                    restart_after_wake("sleep/wake transition")
                    time.sleep(1)
                    continue
                if proc is None:
                    raise PreviewError("D+ client is unexpectedly unavailable")
                if proc.poll() is not None:
                    raise PreviewError("D+ client exited unexpectedly; stopping")
                failed_graph = graph_activation_error(current_log)
                if failed_graph:
                    raise PreviewError("PipeWire graph activation FAILED: " + failed_graph)
                try:
                    default = get_default()
                    names = sink_names()
                except subprocess.SubprocessError:
                    restart_after_wake("PipeWire connection loss")
                    time.sleep(1)
                    continue
                if default != RAW:
                    if time.monotonic() < wake_recovery_grace_until:
                        restore_raw_only_if_own_preview(default, names, restore_budget)
                        time.sleep(0.3)
                        continue
                    raise PreviewError(f"System default changed to {default!r}; stopping trial")
                if RAW not in names:
                    restart_after_wake("temporary Raw output disappearance")
                    time.sleep(1)
                    continue
                if not preview_name(names):
                    restart_after_wake("preview output disappearance")
                    time.sleep(1)
                    continue
                time.sleep(1)
        finally:
            stop_current()
            if current_log is not None and current_log.exists() and sys.exc_info()[0] is not None:
                print("D+ private client log (last lines): " + child_log_tail(current_log),
                      file=sys.stderr)


def main(argv=None):
    pa=argparse.ArgumentParser(description=__doc__)
    mode=pa.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check",action="store_true",help="Offline profile and 48k response validation only")
    mode.add_argument("--show-config",action="store_true",help="Show local, generated preview config; no connection")
    mode.add_argument("--start",action="store_true",help="Explicitly run preview against live PipeWire; stop with Ctrl+C")
    pa.add_argument("--profile",required=True,type=Path,help="Private approved D+ JSON reference")
    pa.add_argument("--restore-raw-on-wake", action="store_true",
                    help="OPT-IN: once per wake, restore Raw ONLY if our own D+ preview became global default")
    args=pa.parse_args(argv)
    if args.restore_raw_on_wake and not args.start:
        pa.error("--restore-raw-on-wake only applies with --start")
    try:
        if args.start:
            start(args.profile, restore_raw_on_wake=args.restore_raw_on_wake)
        else:
            cfg,error=preflight(args.profile)
            if args.show_config:print(cfg)
            print(f"PASS: approved 11-band profile loaded; 48-kHz magnitude fit max difference {error:.4f} dB")
            print("This is a LOWER-GAIN listening preview, NOT equivalent to the approved limiter.")
        return 0
    except (PreviewError,OSError,ValueError,subprocess.SubprocessError,json.JSONDecodeError) as e:
        print("STOP:",e,file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Preview stopped. No cleanup changed the default; optional wake recovery may have restored Raw.")
        return 130

if __name__=="__main__":
    raise SystemExit(main())
