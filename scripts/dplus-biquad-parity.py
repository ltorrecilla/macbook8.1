#!/usr/bin/env python3
"""Offline-only D+ v4 11-biquad parity test and inert PipeWire graph export.

This script loads a separately supplied local profile. It does not install,
load, connect or activate audio devices, services or PipeWire modules.
The generated graph is EQ ONLY: no extra 3 kHz peak, gain, limiter, resampling,
final trim or 4-channel mapping; NEVER install it as a speaker output.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import subprocess
import sys

RATE = 44100
ENGINE_DIGEST = "43da928c7b1b7cd1b1628e47276820dcb2eeeeb841136a425ea25d280ec4076b"
COEF_NAMES = ("b0", "b1", "b2", "a0", "a1", "a2")
FRAMES = 8192


def load_rows(profile_path):
    data = json.loads(Path(profile_path).read_text(encoding="utf-8"))
    if data.get("source", {}).get("file_sha256") != ENGINE_DIGEST:
        raise ValueError("Unexpected D+ source identity; refusing to compare")
    if data.get("input", {}).get("rate_hz") != RATE or data.get("input", {}).get("channels") != 2:
        raise ValueError("Reference input must be stereo 44100 Hz")
    stages = data.get("stages", [])
    if (len(stages) != 9 or stages[0].get("type") != "biquad_cascade"
        or stages[1].get("ffmpeg_filter") != "equalizer=f=3000:t=q:w=1.0:g=1.0"
        or stages[4].get("ffmpeg_filter") != "alimiter"
        or stages[7].get("ffmpeg_filter") != "pan=quad|c0=c0|c1=c1|c2=0*c0|c3=0*c0"):
        raise ValueError("Not the approved D+ v4 processing stage sequence")
    biquad = stages[0]
    if (biquad.get("count_per_channel") != 11 or biquad.get("order") != "sequential ascending 1..11" or
        biquad.get("ffmpeg_options") != {"precision": "f64", "transform": "tdii", "normalize": False}):
        raise ValueError("Different biquad processing order/options")
    rows = biquad.get("coefficients")
    if not isinstance(rows, list) or len(rows) != 11:
        raise ValueError("Expected exactly 11 coefficient sets")
    for index, row in enumerate(rows, 1):
        if (not isinstance(row, dict) or set(row) != set(COEF_NAMES) or
            any(isinstance(row[n], bool) or not isinstance(row[n], (int, float)) or
                not math.isfinite(row[n]) for n in COEF_NAMES) or row["a0"] != 1.0):
            raise ValueError(f"Invalid stage {index} coefficients")
    return rows


def generate_fixture(name):
    pcm = bytearray()
    for i in range(FRAMES):
        t = i / RATE
        if name == "silence":
            l = r = 0.0
        elif name == "left_impulse":
            l, r = (0.2 if i == 700 else 0.0), 0.0
        elif name == "right_impulse":
            l, r = 0.0, (0.2 if i == 700 else 0.0)
        elif name == "stereo_tones":
            l = 0.16 * math.sin(2 * math.pi * 200 * t) + 0.07 * math.sin(2 * math.pi * 3000 * t)
            r = 0.13 * math.sin(2 * math.pi * 325 * t) + 0.05 * math.sin(2 * math.pi * 5200 * t)
        else:
            raise ValueError("Unknown fixture")
        pcm.extend(struct.pack('<ff', l, r))
    return bytes(pcm)


def tdii_cascade(data, rows):
    """Reference transposed Direct Form II, double state, with f32 PCM input."""
    frames = list(struct.iter_unpack('<ff', data))
    channels = [[f[ch] for f in frames] for ch in (0, 1)]
    output = []
    for samples in channels:
        current = samples
        for row in rows:
            b0, b1, b2, _, a1, a2 = (row[n] for n in COEF_NAMES)
            state1 = state2 = 0.0
            next_samples = []
            for x in current:
                y = b0 * x + state1
                state1 = b1 * x - a1 * y + state2
                state2 = b2 * x - a2 * y
                next_samples.append(y)
            current = next_samples
        output.append(current)
    return [sample for pair in zip(*output) for sample in pair]


def ffmpeg_eq_chain(rows):
    return ','.join('biquad=' + ':'.join(f'{k}={row[k]:.17g}' for k in COEF_NAMES) +
                    ':precision=f64:transform=tdii:normalize=false' for row in rows)


def ffmpeg_render(data, rows):
    cmd = ['ffmpeg', '-hide_banner', '-nostdin', '-loglevel', 'error', '-filter_threads', '1',
           '-f', 'f32le', '-ar', str(RATE), '-ac', '2', '-channel_layout', 'stereo',
           '-i', 'pipe:0', '-af', ffmpeg_eq_chain(rows), '-f', 'f64le', '-ar', str(RATE),
           '-ac', '2', 'pipe:1']
    result = subprocess.run(cmd, input=data, capture_output=True, timeout=30, check=False)
    if result.returncode:
        raise RuntimeError('FFmpeg failed: ' + result.stderr.decode('utf-8', 'replace')[-800:])
    if len(result.stdout) != len(data) * 2:
        raise RuntimeError('FFmpeg output has unexpected sample count')
    return [s[0] for s in struct.iter_unpack('<d', result.stdout)]


def compare_python_ffmpeg(data, rows):
    python_samples = tdii_cascade(data, rows)
    ffmpeg_samples = ffmpeg_render(data, rows)
    errs = [abs(a - b) for a, b in zip(python_samples, ffmpeg_samples)]
    maximum = max(errs)
    rms = math.sqrt(sum(e*e for e in errs)/len(errs))
    magnitude = max(abs(x) for x in ffmpeg_samples)
    if not math.isfinite(maximum) or maximum > 1e-8:
        raise ValueError(f'Offline biquad parity mismatch: max absolute error = {maximum:.6g}')
    return {'sample_count': len(errs), 'max_abs_error': maximum, 'rms_error': rms,
            'ffmpeg_peak': magnitude, 'passed': True}


def bilinear_rate_convert(row, source_rate=44100, target_rate=48000):
    """Re-map a digital biquad via bilinear substitution (candidate, NOT parity)."""
    import cmath
    if source_rate <= 0 or target_rate <= 0:
        raise ValueError("Sample rates must be positive")
    ratio = target_rate / source_rate
    p = 1.0 - ratio
    q = 1.0 + ratio

    def transform(prefix):
        c0, c1, c2 = (row[prefix + str(i)] for i in range(3))
        return (c0*q*q + c1*p*q + c2*p*p,
                2*c0*p*q + c1*(p*p+q*q) + 2*c2*p*q,
                c0*p*p + c1*p*q + c2*q*q)

    numerator = transform("b")
    denominator = transform("a")
    if abs(denominator[0]) < 1e-15 or not all(math.isfinite(x) for x in numerator+denominator):
        raise ValueError("Invalid rate conversion")
    result = {name: float(value / denominator[0])
              for name, value in zip(COEF_NAMES, numerator+denominator)}
    a1, a2 = result["a1"], result["a2"]
    poles = [(-a1 + sign*cmath.sqrt(a1*a1 - 4*a2))/2 for sign in (1, -1)]
    if any(abs(x) >= 1.0 for x in poles):
        raise ValueError("Rate conversion creates unstable filter")
    return result


def cascade_response_db(rows, sample_rate, freq_hz):
    """Frequency-domain analysis only; no audio streams or PipeWire use."""
    import cmath
    if freq_hz <= 0 or freq_hz >= sample_rate/2:
        raise ValueError("Comparison frequency must be below Nyquist")
    z = cmath.exp(-2j * math.pi * freq_hz / sample_rate)
    result = 1.0 + 0j
    for row in rows:
        num = row["b0"] + row["b1"]*z + row["b2"]*z*z
        den = row["a0"] + row["a1"]*z + row["a2"]*z*z
        result *= num/den
    if abs(result) <= 0:
        return float("-inf")
    return 20*math.log10(abs(result))


def rate_audit(rows, old_rate=44100, new_rate=48000):
    """Quantify response drift; do not export potentially unsafe 48k coefficients."""
    transformed = [bilinear_rate_convert(x, old_rate, new_rate) for x in rows]
    intervals = ((20, 5000), (5000, 12000), (12000, 18000), (18000, 20000))
    result = {"source_hz": old_rate, "graph_hz": new_rate,
              "method": "digital-bilinear re-map (NOT a parity certificate)",
              "sampled_max_abs_difference_db": {}, "spot_check_db": {}}
    for lo, hi in intervals:
        worst = {"unchanged_44k_coeffs_at_48k": (0.0, lo),
                 "bilinear_remap_48k": (0.0, lo)}
        for i in range(201):
            f = lo * (hi/lo)**(i / 200)
            reference = cascade_response_db(rows, old_rate, f)
            for key, sample_rows in (("unchanged_44k_coeffs_at_48k", rows),
                                     ("bilinear_remap_48k", transformed)):
                delta = cascade_response_db(sample_rows, new_rate, f) - reference
                if abs(delta) > abs(worst[key][0]):
                    worst[key] = (delta, f)
        result["sampled_max_abs_difference_db"][f"{lo}-{hi}Hz"] = {
            key: {"delta_db": round(value[0], 4), "frequency_hz": round(value[1], 1)}
            for key, value in worst.items()}
    for f in (100, 300, 1000, 3000, 5000, 10000, 15000, 18000, 20000):
        ref = cascade_response_db(rows, old_rate, f)
        result["spot_check_db"][str(f)] = {
            "reference_44100": round(ref, 4),
            "unchanged_48000_delta": round(cascade_response_db(rows, new_rate, f)-ref, 4),
            "bilinear_48000_delta": round(cascade_response_db(transformed, new_rate, f)-ref, 4)}
    return result


def pipewire_graph(rows):
    """Inert filter.graph snippet, NOT a complete PipeWire module/sink."""
    lines = [
        '# GENERATED REVIEW-ONLY EQ GRAPH; NOT INSTALLABLE OR SPEAKER-SAFE',
        '# Only the 11 original biquads per channel. Missing +1dB 3k peak, gain,',
        '# limiter, oversampling, channel mapping and recovery logic.',
        '# Requires 44100 Hz PipeWire graph for approved coefficient response.',
        'filter.graph = {', '  nodes = [',
    ]
    for channel in ('L', 'R'):
        for index, row in enumerate(rows, 1):
            coeff = ' '.join(f'{name} = {row[name]:.17g}' for name in COEF_NAMES)
            lines.extend([f'    {{ type = builtin name = {channel}{index:02} label = bq_raw',
                          '      config = { coefficients = [',
                          f'        {{ rate = 44100 {coeff} }}',
                          '      ] }',
                          '    }'])
    lines.extend(['  ]', '  links = ['])
    for channel in ('L', 'R'):
        for i in range(1, len(rows)):
            lines.append(f'    {{ output = "{channel}{i:02}:Out" input = "{channel}{i+1:02}:In" }}')
    lines.extend(['  ]', '  inputs = [ "L01:In" "R01:In" ]',
                  '  outputs = [ "L11:Out" "R11:Out" ]', '}',''])
    return '\n'.join(lines)


def execute(profile, output_dir):
    root = Path(output_dir).expanduser()
    if root.exists() and (not root.is_dir() or any(root.iterdir())):
        raise ValueError('Output directory must be absent or empty; refusing overwrite')
    rows = load_rows(profile)
    report = {'tool': 'offline biquad-only parity; NO PipeWire runtime test',
              'engine_sha256': ENGINE_DIGEST,
              'profile_sha256': hashlib.sha256(Path(profile).read_bytes()).hexdigest(),
              'rate_hz': RATE, 'biquads_per_channel': len(rows), 'tests': {}}
    for case in ('silence', 'left_impulse', 'right_impulse', 'stereo_tones'):
        result = compare_python_ffmpeg(generate_fixture(case), rows)
        report['tests'][case] = result
        print(f"{case:15} max abs error = {result['max_abs_error']:.3g}")
    root.mkdir(parents=True, exist_ok=True)
    graph = pipewire_graph(rows)
    (root/'biquad-only-filter.graph').write_text(graph, encoding='utf-8')
    (root/'parity-report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print('Saved review-only graph and offline test report:', root)
    print('No playback, PipeWire config, user services or default sink changed.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', required=True, type=Path,
                        help='Private D+ v4 JSON reference profile')
    parser.add_argument('--rate-audit', action='store_true',
                        help='Compare 44.1k and 48k EQ responses offline; write nothing')
    parser.add_argument('--output-dir', type=Path,
                        help='Fresh or empty output folder')
    args = parser.parse_args()
    try:
        if args.rate_audit:
            if args.output_dir is not None:
                raise ValueError('--rate-audit does not accept --output-dir')
            results = rate_audit(load_rows(args.profile))
            print(json.dumps(results, indent=2))
            print('Comparison only; neither 48-kHz option is approved for playback.')
        else:
            if args.output_dir is None:
                raise ValueError('--output-dir is required unless --rate-audit is selected')
            execute(args.profile, args.output_dir)
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError, json.JSONDecodeError) as e:
        print('ERROR:', e, file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
