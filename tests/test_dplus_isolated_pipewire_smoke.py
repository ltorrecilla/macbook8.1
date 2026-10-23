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

    def test_only_private_test_sockets_get_access(self):
        config = mod.config_text()
        self.assertIn("libpipewire-module-access", config)
        self.assertIn('dplus-test-0-manager = "unrestricted"', config)
        self.assertIn('dplus-test-0 = "unrestricted"', config)
        self.assertNotIn("access.legacy", config)
        self.assertNotIn('pipewire-0 = "unrestricted"', config)
        self.assertNotIn('pipewire-0-manager = "unrestricted"', config)
        self.assertIn('socket_path = runtime / (SOCKET + "-manager")',
                      SCRIPT.read_text(encoding="utf-8"))

    def test_object_summary_reports_types_and_names(self):
        objects = [
            {"type": "PipeWire:Interface:Node",
             "info": {"props": {"node.name": mod.CAPTURE}}},
            {"type": "PipeWire:Interface:Module", "info": {"props": {}}},
            {"type": "PipeWire:Interface:Node",
             "info": {"props": {"node.name": mod.PLAYBACK}}},
        ]
        summary = mod.inventory_summary(objects)
        self.assertEqual(summary["object_types"]["PipeWire:Interface:Node"], 2)
        self.assertEqual(summary["object_types"]["PipeWire:Interface:Module"], 1)
        self.assertEqual(set(summary["advertised_node_names"]), {mod.CAPTURE, mod.PLAYBACK})

    def test_empty_inventory_distinct_from_missing_expected_nodes(self):
        self.assertEqual(mod.inventory_summary([]),
                         {"object_types": {}, "advertised_node_names": []})
        self.assertEqual(mod.inventory_summary([
            {"type": "PipeWire:Interface:Metadata", "info": None},
            {"type": "PipeWire:Interface:Core"}
        ])["advertised_node_names"], [])

    def test_both_private_phases_load_access_module(self):
        core = mod.config_text(include_filter=False)
        full = mod.config_text(include_filter=True)
        self.assertIn("libpipewire-module-access", core)
        self.assertIn("libpipewire-module-access", full)
        self.assertNotIn("libpipewire-module-filter-chain", core)
        self.assertIn("libpipewire-module-filter-chain", full)

    def test_metadata_module_available_in_both_disposable_phases(self):
        for with_filter in (False, True):
            config = mod.config_text(include_filter=with_filter)
            self.assertIn("libpipewire-module-protocol-native", config)
            self.assertIn("libpipewire-module-metadata", config)
            self.assertEqual(config.count("libpipewire-module-metadata"), 1)
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("Relevant private log messages:", source)

    def test_private_filter_port_inventory_is_filtered_by_node(self):
        objects = [
            {"id": 21, "type": "PipeWire:Interface:Node",
             "info": {"props": {"node.name": mod.CAPTURE}}},
            {"id": 22, "type": "PipeWire:Interface:Node",
             "info": {"props": {"node.name": mod.PLAYBACK}}},
            {"id": 31, "type": "PipeWire:Interface:Port",
             "info": {"direction": "input",
                      "props": {"node.id": 21, "port.name": "input_FL", "audio.channel": "FL"}}},
            {"id": 32, "type": "PipeWire:Interface:Port",
             "info": {"direction": "output",
                      "props": {"node.id": 22, "port.name": "output_FR", "audio.channel": "FR"}}},
            {"id": 33, "type": "PipeWire:Interface:Port",
             "info": {"props": {"node.id": 999, "port.name": "unknown"}}},
        ]
        ports = mod.private_filter_ports(objects)
        self.assertEqual(len(ports), 2)
        self.assertEqual({p["node"] for p in ports}, {mod.CAPTURE, mod.PLAYBACK})
        self.assertEqual({p["channel"] for p in ports}, {"FL", "FR"})

    def test_private_port_inventory_handles_missing_properties(self):
        entries = [{"type": "PipeWire:Interface:Node", "info": None},
                   {"type": "PipeWire:Interface:Port", "info": None}]
        self.assertEqual(mod.private_filter_ports(entries), [])

    def test_private_summary_distinguishes_unmatched_from_no_ports(self):
        objects = [
            {"id": 20, "type": "PipeWire:Interface:Node",
             "info": {"state": "idle", "n_input_ports": 2, "n_output_ports": 0,
                      "props": {"node.name": mod.CAPTURE}}},
            {"id": 30, "type": "PipeWire:Interface:Port",
             "info": {"direction": "input",
                      "props": {"port.name": "input_FL", "node.id": 999}}},
        ]
        report = mod.private_graph_summary(objects)
        self.assertEqual(report["total_published_port_objects"], 1)
        self.assertEqual(report["matched_filter_port_count"], 0)
        self.assertEqual(report["test_nodes"][0]["n_input_ports"], 2)
        self.assertEqual(report["test_nodes"][0]["state"], "idle")

    def test_private_summary_without_ports_and_unknown_info(self):
        objects = [
            {"id": 1, "type": "PipeWire:Interface:Node",
             "info": {"props": {"node.name": mod.PLAYBACK}}},
            {"id": 3, "type": "PipeWire:Interface:Metadata", "info": None}
        ]
        report = mod.private_graph_summary(objects)
        self.assertEqual(report["total_published_port_objects"], 0)
        self.assertEqual(report["test_nodes"][0]["n_output_ports"], "not reported")
        self.assertEqual(report["published_port_sample"], [])

    def test_no_service_or_pulse_actions(self):
        s = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("systemctl", s)
        self.assertNotIn("pactl", s)
        self.assertNotIn("pw-link", s)
        self.assertIn("daemon.send_signal(signal.SIGTERM)", s)


if __name__ == "__main__":
    unittest.main()
