"""CPU cap interrupted/invalid ownership-state tests, isolated to temporary paths."""
from pathlib import Path
import subprocess
import tempfile
import unittest

HELPER = Path(__file__).resolve().parents[1] / "scripts/cpu-config-ownership.sh"


class CpuOwnershipFailurePaths(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.config = Path(self.tmp.name) / "cap"
        self.marker = Path(self.tmp.name) / "cap.owner"

    def execute(self, command):
        return subprocess.run(
            ["bash", "-c", 'source "$1"; shift; ' + command,
             "test", str(HELPER), str(self.config), str(self.marker)],
            capture_output=True, text=True,
        )

    def test_orphan_marker_after_interrupted_install_is_rejected(self):
        self.marker.write_text("macbook81-cpu-cap-v1 " + "a" * 64 + "\n")
        result = self.execute('cpu_cap_config_preflight "$1" "$2" 1600000 no')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.config.exists())
        self.assertTrue(self.marker.exists())

    def test_config_written_but_marker_not_created_is_preserved(self):
        self.config.write_text("1600000\n")
        self.assertNotEqual(
            self.execute('cpu_cap_config_preflight "$1" "$2" 1600000 no').returncode, 0)
        self.assertEqual(
            self.execute('cpu_cap_config_removal_policy "$1" "$2"').stdout.strip(),
            "preserve",
        )
        self.assertEqual(self.config.read_text(), "1600000\n")

    def test_marker_rejects_same_length_but_changed_config(self):
        self.config.write_text("1600000\n")
        self.assertEqual(
            self.execute('cpu_cap_config_mark "$1" "$2"').returncode, 0)
        self.config.write_text("1300000\n")
        self.assertNotEqual(
            self.execute('cpu_cap_config_removal_policy "$1" "$2"').returncode, 0)
        self.assertEqual(self.config.read_text(), "1300000\n")
        self.assertTrue(self.marker.exists())

    def test_replaced_marker_symlink_is_rejected(self):
        self.config.write_text("1600000\n")
        elsewhere = Path(self.tmp.name) / "elsewhere"
        elsewhere.write_text("unrelated\n")
        self.marker.symlink_to(elsewhere)
        self.assertNotEqual(
            self.execute('cpu_cap_config_preflight "$1" "$2" 1600000 no').returncode, 0)
        self.assertEqual(elsewhere.read_text(), "unrelated\n")

    def test_valid_owned_config_allows_retry(self):
        self.config.write_text("1600000\n")
        self.assertEqual(
            self.execute('cpu_cap_config_mark "$1" "$2"').returncode, 0)
        self.assertEqual(
            self.execute('cpu_cap_config_preflight "$1" "$2" 1600000 no').returncode, 0)
        self.assertEqual(
            self.execute('cpu_cap_config_removal_policy "$1" "$2"').stdout.strip(),
            "managed",
        )


if __name__ == "__main__":
    unittest.main()
