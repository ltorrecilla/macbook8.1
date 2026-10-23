"""Safely exercise CPU configuration ownership on temporary files only."""
import pathlib
import subprocess
import tempfile
import unittest

HELPER = pathlib.Path(__file__).resolve().parents[1] / "scripts/cpu-config-ownership.sh"


class CpuConfigOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = pathlib.Path(self.tmp.name)
        self.config = self.path / "max-khz"
        self.marker = self.path / "max-khz.owner"

    def call(self, expression, *args):
        return subprocess.run(["bash", "-c", 'source "$1"; shift; ' + expression,
                               "test", str(HELPER), *(str(a) for a in args)],
                              capture_output=True, text=True)

    def preflight(self, request="1600000", legacy="no"):
        return self.call('cpu_cap_config_preflight "$1" "$2" "$3" "$4"',
                         self.config, self.marker, request, legacy)

    def mark(self):
        return self.call('cpu_cap_config_mark "$1" "$2"', self.config, self.marker)

    def removal(self):
        return self.call('cpu_cap_config_removal_policy "$1" "$2"',
                         self.config, self.marker)

    def test_fresh_install_may_create_config(self):
        self.assertEqual(self.preflight().returncode, 0)

    def test_existing_unowned_config_blocks_install(self):
        self.config.write_text("1600000\n")
        self.assertNotEqual(self.preflight().returncode, 0)
        self.assertEqual(self.config.read_text(), "1600000\n")

    def test_matching_owned_legacy_config_can_be_adopted(self):
        self.config.write_text("1600000\n")
        self.assertEqual(self.preflight(legacy="yes").returncode, 0)
        self.assertNotEqual(self.preflight("1300000", legacy="yes").returncode, 0)

    def test_managed_config_allows_valid_cap_update(self):
        self.config.write_text("1600000\n")
        self.assertEqual(self.mark().returncode, 0)
        self.assertEqual(self.preflight("1300000").returncode, 0)
        self.assertEqual(self.removal().stdout.strip(), "managed")

    def test_external_change_blocks_update_and_removal(self):
        self.config.write_text("1600000\n")
        self.assertEqual(self.mark().returncode, 0)
        self.config.write_text("1200000\n")
        self.assertNotEqual(self.preflight().returncode, 0)
        self.assertNotEqual(self.removal().returncode, 0)
        self.assertEqual(self.config.read_text(), "1200000\n")

    def test_unmarked_legacy_config_preserved_on_uninstall(self):
        self.config.write_text("1600000\n")
        result = self.removal()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "preserve")

    def test_symlink_is_rejected(self):
        other = self.path / "outside"
        other.write_text("1600000\n")
        self.config.symlink_to(other)
        self.assertNotEqual(self.preflight().returncode, 0)

    def test_bogus_marker_blocks_operations(self):
        self.config.write_text("1600000\n")
        self.marker.write_text("unknown 00\n")
        self.assertNotEqual(self.preflight().returncode, 0)
        self.assertNotEqual(self.removal().returncode, 0)


if __name__ == "__main__":
    unittest.main()
