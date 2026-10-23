"""Non-hardware tests for D+ biquad graph draft and reference math."""
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'dplus-biquad-parity.py'
spec = importlib.util.spec_from_file_location('dplus_biquad', SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def fixture_profile():
    return {'source': {'file_sha256': mod.ENGINE_DIGEST},
            'input': {'rate_hz': 44100, 'channels': 2},
            'stages': [
                {'type': 'biquad_cascade', 'count_per_channel': 11,
                 'order': 'sequential ascending 1..11',
                 'ffmpeg_options': {'precision': 'f64', 'transform': 'tdii', 'normalize': False},
                 'coefficients': [{'b0': 1., 'b1': 0., 'b2': 0., 'a0': 1., 'a1': 0., 'a2': 0.} for _ in range(11)]},
                {'ffmpeg_filter': 'equalizer=f=3000:t=q:w=1.0:g=1.0'},
                {}, {}, {'ffmpeg_filter': 'alimiter'}, {}, {},
                {'ffmpeg_filter': 'pan=quad|c0=c0|c1=c1|c2=0*c0|c3=0*c0'}, {}]}


class BiquadParityTests(unittest.TestCase):
    def read(self, profile):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'reference.json'
            path.write_text(json.dumps(profile), encoding='utf-8')
            return mod.load_rows(path)

    def test_expected_11_coefficient_sets(self):
        self.assertEqual(len(self.read(fixture_profile())), 11)

    def test_rejects_wrong_source(self):
        d = fixture_profile()
        d['source']['file_sha256'] = 'bad'
        with self.assertRaises(ValueError):
            self.read(d)

    def test_rejects_unexpected_biquad_count(self):
        d = fixture_profile()
        d['stages'][0]['coefficients'].pop()
        with self.assertRaises(ValueError):
            self.read(d)

    def test_rejects_changed_processing_order(self):
        d = fixture_profile()
        d['stages'][1]['ffmpeg_filter'] = 'equalizer=f=9000:t=q:w=1.0:g=1.0'
        with self.assertRaises(ValueError):
            self.read(d)

    def test_graph_has_two_isolated_11_stage_chains(self):
        s = mod.pipewire_graph(self.read(fixture_profile()))
        self.assertEqual(s.count('label = bq_raw'), 22)
        self.assertEqual(s.count('output = "L'), 10)
        self.assertEqual(s.count('output = "R'), 10)
        self.assertIn('inputs = [ "L01:In" "R01:In" ]', s)
        self.assertNotIn('libpipewire-module-filter-chain', s)

    def test_identity_filter_passes_stereo_input(self):
        raw = struct.pack('<ffffff', .25, -.25, 0.5, -.125, 0., 0.)
        self.assertEqual(mod.tdii_cascade(raw, self.read(fixture_profile())), [.25, -.25, .5, -.125, 0., 0.])

    def test_four_synthetic_fixtures_are_stereo(self):
        for name in ('silence','left_impulse','right_impulse','stereo_tones'):
            self.assertEqual(len(mod.generate_fixture(name)), mod.FRAMES*8)

    def test_bilinear_identity_at_matching_rates(self):
        coeffs = self.read(fixture_profile())[0]
        new = mod.bilinear_rate_convert(coeffs, 44100, 44100)
        for k in mod.COEF_NAMES:
            self.assertAlmostEqual(coeffs[k], new[k], places=12)

    def test_bilinear_stable_candidate(self):
        row = {'b0': 0.2, 'b1': 0.0, 'b2': 0.0,
               'a0': 1., 'a1': -0.7, 'a2': 0.1}
        converted = mod.bilinear_rate_convert(row)
        self.assertEqual(converted['a0'], 1.)
        self.assertTrue(all(mod.math.isfinite(v) for v in converted.values()))

    def test_frequency_response_identity(self):
        row = self.read(fixture_profile())
        for hz in [50, 1000, 10000]:
            self.assertAlmostEqual(mod.cascade_response_db(row, 44100, hz), 0, places=12)

    def test_audit_identity_has_no_difference(self):
        row = self.read(fixture_profile())
        report = mod.rate_audit(row)
        for item in report['sampled_max_abs_difference_db'].values():
            self.assertLess(abs(item['unchanged_44k_coeffs_at_48k']['delta_db']), 1e-7)
            self.assertLess(abs(item['bilinear_remap_48k']['delta_db']), 1e-7)

    def test_do_not_overwrite_output_directory(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'reference.json'
            p.write_text(json.dumps(fixture_profile()))
            out = Path(d) / 'output'
            out.mkdir()
            (out/'existing').write_text('keep')
            with self.assertRaisesRegex(ValueError, 'refusing overwrite'):
                mod.execute(p, out)
            self.assertEqual((out/'existing').read_text(), 'keep')


if __name__ == '__main__':
    unittest.main()
