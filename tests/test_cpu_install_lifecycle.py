"""Exercise a rewritten CPU installer using private temporary fixtures only.

All absolute system paths and privileged commands are redirected or mocked.
This tests failure reporting and preserved files; it does not claim atomic rollback.
"""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts/install-cpu-limit.sh"
OWNER = ROOT / "scripts/cpu-config-ownership.sh"


class CpuInstallLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for path in ("bin", "scripts", "systemd", "etc", "libexec", "sysfs/policy0", "run/systemd/system"):
            (self.root / path).mkdir(parents=True, exist_ok=True)
        self.unit = self.root / "etc/macbook81-cpu-cap.service"
        self.helper = self.root / "libexec/macbook81-cpu-cap"
        self.config = self.root / "etc/macbook81-cpu-cap.max-khz"
        self.marker = self.root / "etc/macbook81-cpu-cap.max-khz.owner"
        (self.root / "model").write_text("MacBook8,1\n")
        policy = self.root / "sysfs/policy0"
        (policy / "scaling_min_freq").write_text("500000\n")
        (policy / "cpuinfo_max_freq").write_text("2600000\n")
        (self.root / "scripts/cpu-config-ownership.sh").write_text(OWNER.read_text())
        (self.root / "scripts/cpu-cap-control.sh").write_text(
            "#!/bin/sh\n# macbook81-cpu-cap runtime helper.\nexit 0\n")
        (self.root / "systemd/macbook81-cpu-cap.service").write_text(
            "# Managed by macbook81-starter\n[Unit]\nDescription=Fixture\n")
        installer = INSTALLER.read_text()
        start = 'source_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"'
        self.assertIn(start, installer)
        installer = installer.replace(start, 'source_dir="' + str(self.root) + '"')
        replacements = {
            '[[ $EUID -eq 0 ]]': '[[ 1 -eq 1 ]]',
            '/sys/class/dmi/id/product_name': str(self.root / "model"),
            '/run/systemd/system': str(self.root / "run/systemd/system"),
            '/sys/devices/system/cpu/cpufreq': str(self.root / "sysfs"),
            '/etc/systemd/system/macbook81-cpu-cap.service': str(self.unit),
            '/usr/local/libexec/macbook81-cpu-cap': str(self.helper),
            '/etc/macbook81-cpu-cap.max-khz': str(self.config),
        }
        for old, new in replacements.items():
            self.assertIn(old, installer)
            installer = installer.replace(old, new)
        self.script = self.root / "install-cpu-limit.sh"
        self.script.write_text(installer)
        self.mockbin = self.root / "bin"
        systemctl = self.mockbin / "systemctl"
        systemctl.write_text(
            '#!/bin/sh\n'
            'case "$1" in\n'
            ' is-active) exit 1;;\n'
            'esac\n'
            '[ "${FAIL_STAGE:-}" != "$1" ]\n'
        )
        systemctl.chmod(0o755)
        fake_install = self.mockbin / "install"
        fake_install.write_text(
            '#!/bin/sh\n'
            'if [ "${FAIL_STAGE:-}" = install ]; then exit 11; fi\n'
            'exec /usr/bin/install "$@"\n'
        )
        fake_install.chmod(0o755)
        self.env = dict(os.environ, PATH=str(self.mockbin) + ":" + os.environ["PATH"])

    def run_install(self, failure=""):
        return subprocess.run(["bash", str(self.script), "1600"],
                              env=dict(self.env, FAIL_STAGE=failure),
                              capture_output=True, text=True)

    def test_fresh_install_creates_owned_configuration(self):
        result = self.run_install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.config.read_text(), "1600000\n")
        self.assertTrue(self.marker.exists())
        self.assertTrue(self.unit.exists())
        self.assertTrue(self.helper.exists())

    def test_failed_install_copy_does_not_create_config(self):
        result = self.run_install("install")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.config.exists())
        self.assertFalse(self.marker.exists())

    def test_failed_daemon_reload_is_reported_without_success(self):
        result = self.run_install("daemon-reload")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("CPU cap installed and enabled", result.stdout)
        self.assertTrue(self.config.exists())
        self.assertTrue(self.marker.exists())

    def test_failed_enable_is_reported_and_keeps_owned_files_for_review(self):
        result = self.run_install("enable")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("CPU cap installed and enabled", result.stdout)
        self.assertTrue(self.unit.exists())
        self.assertTrue(self.marker.exists())

    def test_failed_restart_is_not_reported_as_success(self):
        result = self.run_install("restart")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("CPU cap installed and enabled", result.stdout)

    def test_unowned_preexisting_config_remains_unchanged(self):
        self.config.write_text("1400000\n")
        result = self.run_install()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.config.read_text(), "1400000\n")
        self.assertFalse(self.unit.exists())


if __name__ == "__main__":
    unittest.main()
