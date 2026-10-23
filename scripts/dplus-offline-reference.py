#!/usr/bin/env python3
"""Offline-only MacBook8,1 D+ v4 reference renderer.

Reads a separately supplied JSON profile, generates synthetic stereo fixtures,
renders the original FFmpeg DSP sequence to WAV, and records measurements.
No PipeWire, ALSA, speaker, systemd, sudo, or configuration operations.
The files are reference data, NOT a real-time engine or speaker-safe preset.
"""

import argparse
import ast
import hashlib
import json
import math
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import wave

RATE = 44100
SOURCE_SHA256 = '43da928c7b1b7cd1b1628e47276820dcb2eeeeb841136a425ea25d280ec4076b'
COEF_KEYS = ('b0', 'b1', 'b2', 'a0', 'a1', 'a2')
CASE_SECONDS = {'silence': 0.4, 'impulse_left': 0.6, 'impulse_right': 0.6,
                'quiet_music': 1.6, 'loud_music': 1.6}


def load_profile(path):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    stages = data.get('stages', [])
    if ([x.get('type') for x in stages] !=
            ['biquad_cascade', 'equalizer', 'gain', 'resample', 'limiter',
             'resample', 'gain', 'channel_mapping', 'resample_format']):
        raise ValueError('Profile stages/order differ from reviewed D+ v4')
    if data.get('source', {}).get('file_sha256') != SOURCE_SHA256:
        raise ValueError('Unrecognized reference-engine source checksum')
    if data.get('input') != {'channels': 2, 'rate_hz': RATE,
                              'sample_format': 'float32le', 'positions': ['FL', 'FR']}:
        raise ValueError('Unexpected input format')
    output = data.get('output', {})
    if (output.get('channels'), output.get('rate_hz'), output.get('mapping')) != (4, RATE, ['left', 'right', 'zero', 'zero']):
        raise ValueError('Unexpected output channel mapping')
    biquad = stages[0]
    if (len(biquad.get('coefficients', [])) != 11 or biquad.get('count_per_channel') != 11 or
        biquad.get('ffmpeg_options') != {'precision': 'f64', 'transform': 'tdii', 'normalize': False}):
        raise ValueError('Incorrect biquad layout/options')
    for row in biquad['coefficients']:
        if set(row) != set(COEF_KEYS) or not all(isinstance(row[k], (int, float)) and math.isfinite(row[k]) for k in COEF_KEYS):
            raise ValueError('Invalid biquad coefficients')
        if row['a0'] != 1:
            raise ValueError('Unexpected biquad normalization')
    if (stages[1].get('ffmpeg_filter') != 'equalizer=f=3000:t=q:w=1.0:g=1.0' or
        stages[2].get('db') != 8.310000000000002 or
        stages[3].get('rate_hz') != 176400 or
        stages[4].get('limit_linear') != 0.6683439175686147 or
        stages[4].get('attack_ms') != 5 or stages[4].get('release_ms') != 80 or
        stages[5].get('rate_hz') != RATE or
        stages[6].get('db') != -0.009999999999999787 or
        stages[7].get('ffmpeg_filter') != 'pan=quad|c0=c0|c1=c1|c2=0*c0|c3=0*c0' or
        stages[8].get('rate_hz') != RATE or stages[8].get('sample_format') != 's16le'):
        raise ValueError('Unexpected D+ v4 processing parameters')
    if {k: stages[4].get(k) for k in ('level_in', 'level_out', 'asc', 'level', 'latency')} != {'level_in': 1, 'level_out': 1, 'asc': False, 'level': False, 'latency': True}:
        raise ValueError('Unexpected limiter controls')
    return data


def verify_engine_source(engine_path, profile):
    source = Path(engine_path).read_bytes()
    digest = hashlib.sha256(source).hexdigest()
    if digest != SOURCE_SHA256 or digest != profile['source']['file_sha256']:
        raise ValueError('Engine file is not the exact approved reference')
    tree = ast.parse(source, filename=str(engine_path))
    names = {'RATE', 'COEFFICIENTS', 'PREGAIN_DB', 'FINAL_TRIM_DB', 'LIMIT'}
    found = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in names:
                found[name] = ast.literal_eval(node.value)
    if set(found) != names:
        raise ValueError('Engine constants incomplete')
    stages = profile['stages']
    for actual, expected in [
        (found['RATE'], RATE),
        (found['PREGAIN_DB'], stages[2]['db']),
        (found['FINAL_TRIM_DB'], stages[6]['db']),
        (found['LIMIT'], stages[4]['limit_linear']),
        (found['COEFFICIENTS'], tuple(tuple(row[k] for k in COEF_KEYS)
                                      for row in stages[0]['coefficients']))
    ]:
        if actual != expected:
            raise ValueError('Profile differs from original engine constants')
    return digest


def ffmpeg_chain(profile):
    stages = profile['stages']
    pieces = []
    for row in stages[0]['coefficients']:
        pieces.append('biquad=' + ':'.join(f'{k}={row[k]:.17g}' for k in COEF_KEYS)
                      + ':precision=f64:transform=tdii:normalize=false')
    pieces += [
        stages[1]['ffmpeg_filter'],
        f"volume={stages[2]['db']:.17g}dB:precision=double",
        'aresample=176400:osf=dbl:tsf=dblp',
        f"alimiter=limit={stages[4]['limit_linear']:.17g}:attack=5:release=80:level_in=1:level_out=1:asc=false:level=false:latency=true",
        'aresample=44100:osf=dbl:tsf=dblp',
        f"volume={stages[6]['db']:.17g}dB:precision=double",
        stages[7]['ffmpeg_filter'],
        'aresample=44100:osf=s16:dither_method=none',
    ]
    return ','.join(pieces)


def synthesize(name):
    total = round(CASE_SECONDS[name] * RATE)
    audio = bytearray()
    for i in range(total):
        t = i / RATE
        if name == 'silence':
            left, right = 0., 0.
        elif name == 'impulse_left':
            left, right = (0.25 if i == 1103 else 0.), 0.
        elif name == 'impulse_right':
            left, right = 0., (0.25 if i == 1103 else 0.)
        else:
            amp = 0.025 if name == 'quiet_music' else 0.53
            fade = min(1., i / (RATE * 0.025), (total - i) / (RATE * 0.025))
            left = amp * fade * (0.63 * math.sin(2 * math.pi * 180 * t) +
                                 0.22 * math.sin(2 * math.pi * 800 * t) +
                                 0.15 * math.sin(2 * math.pi * 3000 * t))
            right = amp * fade * (0.58 * math.sin(2 * math.pi * 240 * t) +
                                  0.27 * math.sin(2 * math.pi * 1250 * t) +
                                  0.15 * math.sin(2 * math.pi * 5100 * t))
        audio.extend(struct.pack('<ff', left, right))
    return bytes(audio)


def render(ffmpeg, source_bytes, chain):
    cmd = [ffmpeg, '-hide_banner', '-nostdin', '-loglevel', 'error', '-filter_threads', '1',
           '-probesize', '32', '-analyzeduration', '0', '-f', 'f32le', '-ar', str(RATE),
           '-ac', '2', '-channel_layout', 'stereo', '-i', 'pipe:0', '-af', chain,
           '-ar', str(RATE), '-ac', '4', '-channel_layout', 'quad', '-c:a', 'pcm_s16le',
           '-f', 's16le', 'pipe:1']
    res = subprocess.run(cmd, input=source_bytes, capture_output=True, timeout=45, check=False)
    if res.returncode:
        raise RuntimeError('FFmpeg offline render failed: ' + res.stderr.decode('utf-8', 'replace')[-1200:])
    if not res.stdout or len(res.stdout) % 8:
        raise RuntimeError('FFmpeg output was empty or not 4-channel signed-16 PCM')
    return res.stdout


def measure_quad(data):
    count = len(data) // 8
    sums = [0.] * 4
    peaks = [0] * 4
    nonzero = [0] * 4
    for frame in struct.iter_unpack('<hhhh', data):
        for ch, v in enumerate(frame):
            sums[ch] += v * v
            peaks[ch] = max(peaks[ch], abs(v))
            nonzero[ch] += (v != 0)
    if nonzero[2] or nonzero[3]:
        raise ValueError('D+ profile wrote nonzero rear channels; DO NOT ROUTE TO SPEAKERS')
    return {'frames': count,
            'rms_dbfs': [round(20 * math.log10(math.sqrt(s / count) / 32768), 3)
                         if s else None for s in sums],
            'sample_peak_dbfs': [round(20 * math.log10(p / 32768), 3) if p else None for p in peaks],
            'nonzero_samples': nonzero,
            'clipped_samples': sum(1 for frame in struct.iter_unpack('<hhhh', data)
                                   for val in frame[:2] if abs(val) >= 32767)}


def run(profile_path, engine_path, output_dir, ffmpeg):
    profile = load_profile(profile_path)
    if engine_path:
        verify_engine_source(engine_path, profile)
    if not shutil.which(ffmpeg):
        raise ValueError('ffmpeg not found; no installation is attempted')
    root = Path(output_dir).expanduser()
    if root.exists() and (not root.is_dir() or any(root.iterdir())):
        raise ValueError('Output directory must be absent or empty (no overwrites)')
    root.mkdir(parents=True, exist_ok=True)
    chain = ffmpeg_chain(profile)
    version = subprocess.run([ffmpeg, '-version'], capture_output=True, text=True, timeout=5, check=True).stdout.splitlines()[0]
    manifest = {'description': 'D+ v4 synthetic OFFLINE baseline; do not play on speakers',
                'profile_sha256': hashlib.sha256(Path(profile_path).read_bytes()).hexdigest(),
                'engine_source_sha256': profile['source']['file_sha256'],
                'ffmpeg_version': version, 'ffmpeg_filter_sha256': hashlib.sha256(chain.encode()).hexdigest(),
                'reference_is_not_speaker_safety_approval': True, 'cases': {}}
    for name in CASE_SECONDS:
        source = synthesize(name)
        pcm = render(ffmpeg, source, chain)
        metrics = measure_quad(pcm)
        if metrics['frames'] != len(source) // 8:
            raise ValueError(f'{name}: frame count changed ({metrics["frames"]} vs {len(source)//8})')
        if name == 'silence' and any(metrics['nonzero_samples']):
            raise ValueError('Silence input produced nonzero output')
        if name == 'impulse_left' and metrics['nonzero_samples'][1]:
            raise ValueError('Left-only test leaked into right speaker channel')
        if name == 'impulse_right' and metrics['nonzero_samples'][0]:
            raise ValueError('Right-only test leaked into left speaker channel')
        if name != 'silence' and not (metrics['nonzero_samples'][0] or metrics['nonzero_samples'][1]):
            raise ValueError('Unexpected silent front output')
        outfile = root / (name + '.wav')
        with wave.open(str(outfile), 'wb') as wav:
            wav.setnchannels(4)
            wav.setsampwidth(2)
            wav.setframerate(RATE)
            wav.writeframes(pcm)
        manifest['cases'][name] = {'wav': outfile.name, 'wav_sha256': hashlib.sha256(outfile.read_bytes()).hexdigest(),
                                    'input_sha256': hashlib.sha256(source).hexdigest(), **metrics}
        print(f'{name:15} {metrics["frames"]:>7} frames  peak={metrics["sample_peak_dbfs"][:2]}  rear=[0, 0]')
    (root / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print('Offline baseline saved to:', root)
    print('No sound played. No PipeWire, systemd, ALSA or kernel changes.')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--profile', type=Path, required=True, help='Private extracted D+ v4 JSON profile')
    ap.add_argument('--engine-source', type=Path, help='Optional original engine .py, verified by SHA and static constants only')
    ap.add_argument('--output-dir', type=Path, required=True, help='New or empty local output folder')
    ap.add_argument('--ffmpeg', default='ffmpeg')
    args = ap.parse_args(argv)
    try:
        run(args.profile, args.engine_source, args.output_dir, args.ffmpeg)
        return 0
    except (ValueError, OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        print('ERROR:', exc, file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
