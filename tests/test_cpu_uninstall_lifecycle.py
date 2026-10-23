"""Uninstaller lifecycle tests using an isolated rewritten script and mock systemctl.

Never invokes sudo or accesses actual /etc, /usr/local or systemd.
"""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
UNINSTALL = ROOT / "scripts/uninstall-cpu-limit.sh"
OWNERSHIP = ROOT / "scripts/cpu-config-ownership.sh"

class CpuUninstallLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.etc = self.root / "etc"
        self.bin = self.root / "bin"
        self.libexec = self.root / "libexec"
        for d in (self.etc, self.bin, self.libexec):
            d.mkdir()
        self.unit = self.etc / "macbook81-cpu-cap.service"
        self.helper = self.libexec / "macbook81-cpu-cap"
        self.config = self.etc / "macbook81-cpu-cap.max-khz"
        self.marker = self.etc / "macbook81-cpu-cap.max-khz.owner"
        self.unit.write_text("# Managed by macbook81-starter\n")
        self.helper.write_text("# macbook81-cpu-cap runtime helper.\n")
        self.config.write_text("1600000\n")
        (self.root / "cpu-config-ownership.sh").write_text(OWNERSHIP.read_text())
        self.script = self.root / "uninstall.sh"
        source = UNINSTALL.read_text()
        source = source.replace('[[ $EUID -eq 0 ]]', '[[ 1 -eq 1 ]]')
        source = source.replace("/etc/systemd/system/macbook81-cpu-cap.service", str(self.unit))
        source = source.replace("/usr/local/libexec/macbook81-cpu-cap", str(self.helper))
        source = source.replace("/etc/macbook81-cpu-cap.max-khz", str(self.config))
        # Marker path above is a longer suffix; replace config prefix also rewrites it.
        self.script.write_text(source)
        self.systemctl = self.bin / "systemctl"
        self.systemctl.write_text('#!/bin/sh\ncase "${FAIL_SYSTEMCTL:-}" in yes) exit 1;; esac\nexit 0\n')
        self.systemctl.chmod(0o755)
        self.env = dict(os.environ, PATH=str(self.bin) + ":" + os.environ.get("PATH", ""))

    def mark(self):
        r = subprocess.run(["bash", "-c", 'source "$1"; cpu_cap_config_mark "$2" "$3"',
                            "test", str(self.root / "cpu-config-ownership.sh"),
                            str(self.config), str(self.marker)],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)

    def run_uninstall(self, fail=False):
        env = dict(self.env, FAIL_SYSTEMCTL="yes" if fail else "no")
        return subprocess.run(["bash", str(self.script)], env=env,
                              capture_output=True, text=True)

    def test_service_disable_failure_preserves_everything(self):
        self.mark()
        result = self.run_uninstall(fail=True)
        self.assertNotEqual(result.returncode, 0)
        for path in (self.unit, self.helper, self.config, self.marker):
            self.assertTrue(path.exists(), str(path))

    def test_modified_config_stops_before_service_disable(self):
        self.mark()
        self.config.write_text("1800000\n")
        result = self.run_uninstall()
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(self.unit.exists())
        self.assertEqual(self.config.read_text(), "1800000\n")

    def test_successful_managed_removal(self):
        self.mark()
        result = self.run_uninstall()
        self.assertEqual(result.returncode, 0, result.stderr)
        for path in (self.unit, self.helper, self.config, self.marker):
            self.assertFalse(path.exists(), str(path))

    def test_legacy_config_is_preserved(self):
        result = self.run_uninstall()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.config.exists())
        self.assertFalse(self.unit.exists())
        self.assertFalse(self.helper.exists())

    def test_unowned_service_not_removed(self):
        self.unit.write_text("# unrelated service\n")
        result = self.run_uninstall()
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(self.unit.exists())
        self.assertTrue(self.config.exists())

if __name__ == "__main__":
    unittest.main()
