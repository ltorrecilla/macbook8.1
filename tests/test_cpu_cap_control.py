"""Isolated tests for the CPU cap runtime helper.

All sysfs paths point to temporary files. Never run the privileged installer.
"""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

HELPER = Path(__file__).resolve().parents[1] / "scripts/cpu-cap-control.sh"


class CpuCapTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.sysfs = self.base / "cpufreq"
        self.run_dir = self.base / "runtime"
        self.config = self.base / "max-khz"
        self.sysfs.mkdir()
        self.config.write_text("1600000\n")
        self.env = dict(os.environ, MACBOOK81_CPU_SYSFS=str(self.sysfs),
                        MACBOOK81_CPU_RUN=str(self.run_dir),
                        MACBOOK81_CPU_CONFIG=str(self.config))
        self.policy(0)
        self.policy(1)

    def policy(self, number, *, minimum=500000, maximum=2600000):
        p = self.sysfs / f"policy{number}"
        p.mkdir()
        (p / "scaling_min_freq").write_text(f"{minimum}\n")
        (p / "cpuinfo_max_freq").write_text("2600000\n")
        (p / "scaling_max_freq").write_text(f"{maximum}\n")
        return p

    def call(self, action):
        return subprocess.run(["bash", str(HELPER), action], env=self.env,
                              text=True, capture_output=True, check=False)

    def maximum(self, n):
        return int((self.sysfs / f"policy{n}" / "scaling_max_freq").read_text())

    def test_status_has_no_changes(self):
        r = self.call("status")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("configured-max=2600 MHz", r.stdout)
        self.assertEqual(self.maximum(0), 2600000)
        self.assertFalse(self.run_dir.exists())

    def test_apply_caps_all_policies_and_records_original(self):
        r = self.call("apply")
        self.assertEqual(r.returncode, 0, r.stderr)
        for n in (0, 1):
            self.assertEqual(self.maximum(n), 1600000)
            self.assertEqual((self.run_dir / f"policy{n}").read_text().split(),
                             ["2600000", "1600000"])

    def test_restore_returns_previous_values(self):
        self.assertEqual(self.call("apply").returncode, 0)
        r = self.call("restore")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual([self.maximum(n) for n in (0, 1)], [2600000, 2600000])
        self.assertFalse(self.run_dir.exists())

    def test_repeated_apply_keeps_original_backup(self):
        self.assertEqual(self.call("apply").returncode, 0)
        self.assertEqual(self.call("apply").returncode, 0)
        self.assertEqual((self.run_dir / "policy0").read_text().split(),
                         ["2600000", "1600000"])

    def test_external_change_is_not_overwritten(self):
        self.assertEqual(self.call("apply").returncode, 0)
        (self.sysfs / "policy0" / "scaling_max_freq").write_text("1800000\n")
        r = self.call("restore")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("not overwriting", r.stderr)
        self.assertEqual(self.maximum(0), 1800000)
        self.assertEqual(self.maximum(1), 2600000)

    def test_invalid_cap_stops_before_any_policy_changes(self):
        self.config.write_text("3000000\n")
        r = self.call("apply")
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual([self.maximum(n) for n in (0, 1)], [2600000, 2600000])
        self.assertFalse(self.run_dir.exists())

    def test_invalid_second_policy_stops_before_first_change(self):
        (self.sysfs / "policy1" / "scaling_min_freq").write_text("1900000\n")
        r = self.call("apply")
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(self.maximum(0), 2600000)
        self.assertFalse(self.run_dir.exists())

    def test_malformed_config_is_rejected(self):
        self.config.write_text("not-a-number\n")
        r = self.call("apply")
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(self.maximum(0), 2600000)

    def test_unknown_action_does_not_change_policy(self):
        r = self.call("unsupported")
        self.assertEqual(r.returncode, 2)
        self.assertEqual(self.maximum(0), 2600000)


if __name__ == "__main__":
    unittest.main()
