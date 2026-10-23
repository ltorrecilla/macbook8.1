"""No-hardware tests of the isolated PipeWire bq_raw smoke-test launcher."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "dplus-isolated-pipewire-smoke.py"
spec = importlib.util.spec_from_file_location("dplus_isolated_smoke", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class IsolatedPipeWireSmokeTests(unittest.TestCase):
    def test_unity_biquad_graph(self):
        s = mod.config_text()
        self.assertEqual(s.count("label = bq_raw"), 2)
        self.assertEqual(s.count("rate = 48000 b0 = 1 b1 = 0 b2 = 0 a0 = 1 a1 = 0 a2 = 0"), 2)

    def test_no_hardware_or_default_sink_routing(self):
        s = mod.config_text().lower()
        for prohibited in ("macbook_speaker_raw", "alsa", "wireplumber",
                           "module-pulse", "target.object", "module-loopback"):
            self.assertNotIn(prohibited, s)

    def test_48k_and_passive_without_fallback(self):
        s = mod.config_text()
        self.assertIn("default.clock.allowed-rates = [ 48000 ]", s)
        self.assertIn("node.passive = true", s)
        self.assertIn("node.dont-fallback = true", s)
        self.assertIn("node.dont-reconnect = true", s)

    def test_socket_environment_is_private(self):
        with tempfile.TemporaryDirectory() as d:
            env = mod.safe_env(Path(d))
            self.assertEqual(env["PIPEWIRE_RUNTIME_DIR"], str(Path(d) / "runtime"))
            self.assertEqual(env["PIPEWIRE_CONFIG_DIR"], str(Path(d) / "config"))
            self.assertEqual(env["PIPEWIRE_REMOTE"], mod.SOCKET)
            client = mod.client_env(env)
            self.assertEqual(client["PIPEWIRE_REMOTE"], mod.SOCKET)
            self.assertNotIn("PIPEWIRE_DAEMON", client)
            self.assertNotIn("PIPEWIRE_CORE", client)
            self.assertNotIn("PIPEWIRE_CONFIG_DIR", client)

    def test_detects_only_both_expected_nodes(self):
        objects = [
            {"type": "PipeWire:Interface:Node", "info": {"props": {"node.name": mod.CAPTURE}}},
            {"type": "PipeWire:Interface:Node", "info": {"props": {"node.name": mod.PLAYBACK}}}
        ]
        self.assertTrue(mod.scan_objects(objects)[0])
        self.assertFalse(mod.scan_objects(objects[:1])[0])

    def test_core_phase_contains_protocol_but_no_filter(self):
        config = mod.config_text(include_filter=False)
        self.assertIn("libpipewire-module-protocol-native", config)
        self.assertNotIn("libpipewire-module-filter-chain", config)
        self.assertNotIn("bq_raw", config)
        self.assertTrue(config.strip().endswith("]"))

    def test_client_environment_preserves_private_socket_and_client_defaults(self):
        with tempfile.TemporaryDirectory() as d:
            env = mod.safe_env(Path(d))
            env["PIPEWIRE_NO_CONFIG"] = "true"
            client = mod.client_env(env)
            self.assertNotIn("PIPEWIRE_NO_CONFIG", client)
            self.assertNotIn("PIPEWIRE_DAEMON", client)
            self.assertNotIn("PIPEWIRE_CORE", client)
            self.assertEqual(client["PIPEWIRE_REMOTE"], mod.SOCKET)
            self.assertEqual(client["PIPEWIRE_RUNTIME_DIR"], str(Path(d) / "runtime"))

    def test_probe_uses_explicit_remote_and_socket_ready_check(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('"--remote=" + SOCKET', source)
        self.assertIn('socket_path.is_socket()', source)
        self.assertIn('private_phase(root, "core", with_filter=False)', source)
        self.assertIn('private_phase(root, "filter", with_filter=True)', source)

    def test_no_service_or_pulse_actions(self):
        s = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("systemctl", s)
        self.assertNotIn("pactl", s)
        self.assertNotIn("pw-link", s)
        self.assertIn("daemon.send_signal(signal.SIGTERM)", s)


if __name__ == "__main__":
    unittest.main()
