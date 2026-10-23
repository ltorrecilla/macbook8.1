"""Offline D+ reference renderer tests; no PipeWire or hardware access."""
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'dplus-offline-reference.py'
spec = importlib.util.spec_from_file_location('dplus_offline_reference', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def profile_example():
    return {
        'source': {'file_sha256': module.SOURCE_SHA256},
        'input': {'channels': 2, 'rate_hz': 44100, 'sample_format': 'float32le',
                  'positions': ['FL', 'FR']},
        'output': {'channels': 4, 'rate_hz': 44100, 'mapping': ['left', 'right', 'zero', 'zero']},
        'stages': [
            {'type': 'biquad_cascade', 'count_per_channel': 11,
             'ffmpeg_options': {'precision': 'f64', 'transform': 'tdii', 'normalize': False},
             'coefficients': [dict(zip(module.COEF_KEYS, (1, 0, 0, 1, 0, 0))) for _ in range(11)]},
            {'type': 'equalizer', 'ffmpeg_filter': 'equalizer=f=3000:t=q:w=1.0:g=1.0'},
            {'type': 'gain', 'db': 8.310000000000002},
            {'type': 'resample', 'rate_hz': 176400},
            {'type': 'limiter', 'limit_linear': 0.6683439175686147,
             'attack_ms': 5, 'release_ms': 80, 'level_in': 1, 'level_out': 1,
             'asc': False, 'level': False, 'latency': True},
            {'type': 'resample', 'rate_hz': 44100},
            {'type': 'gain', 'db': -0.009999999999999787},
            {'type': 'channel_mapping', 'ffmpeg_filter': 'pan=quad|c0=c0|c1=c1|c2=0*c0|c3=0*c0'},
            {'type': 'resample_format', 'rate_hz': 44100, 'sample_format': 's16le'},
        ]
    }


class OfflineDPlusTests(unittest.TestCase):
    def load(self, data):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'profile.json'
            p.write_text(json.dumps(data), encoding='utf-8')
            return module.load_profile(p)

    def test_accepts_reference_schema(self):
        self.assertEqual(len(self.load(profile_example())['stages'][0]['coefficients']), 11)

    def test_rejects_missing_coefficients(self):
        p = profile_example()
        p['stages'][0]['coefficients'].pop()
        with self.assertRaises(ValueError):
            self.load(p)

    def test_rejects_changed_default_channel_layout(self):
        p = profile_example()
        p['output']['mapping'] = ['left', 'right', 'left', 'right']
        with self.assertRaises(ValueError):
            self.load(p)

    def test_rejects_changed_limiter_threshold(self):
        p = profile_example()
        p['stages'][4]['limit_linear'] = 0.9
        with self.assertRaises(ValueError):
            self.load(p)

    def test_filter_graph_contains_exact_11_biquads(self):
        graph = module.ffmpeg_chain(self.load(profile_example()))
        self.assertEqual(graph.count('biquad='), 11)
        self.assertIn('latency=true', graph)
        self.assertTrue(graph.endswith('aresample=44100:osf=s16:dither_method=none'))

    def test_synthetic_audio_is_stereo(self):
        for name in module.CASE_SECONDS:
            audio = module.synthesize(name)
            self.assertEqual(len(audio), round(module.CASE_SECONDS[name] * 44100) * 8)

    def test_rear_channel_gate(self):
        self.assertEqual(module.measure_quad(struct.pack('<hhhh', 500, -500, 0, 0))['nonzero_samples'], [1, 1, 0, 0])
        with self.assertRaises(ValueError):
            module.measure_quad(struct.pack('<hhhh', 500, -500, 1, 0))

    def test_rejects_wrong_engine_hash(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'engine.py'
            p.write_text('PREGAIN_DB=8.31\n')
            with self.assertRaises(ValueError):
                module.verify_engine_source(p, profile_example())


if __name__ == '__main__':
    unittest.main()
