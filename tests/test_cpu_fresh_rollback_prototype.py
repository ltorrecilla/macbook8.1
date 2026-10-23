"""Test a prototype rollback helper using temporary files; no system writes."""
import hashlib
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/cpu-fresh-rollback-prototype.sh"

class RollbackPrototypeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.manifest = self.root / "manifest"
        self.file = self.root / "managed"
        self.file.write_text("our install\n")
        self.digest = hashlib.sha256(self.file.read_bytes()).hexdigest()

    def run_rollback(self, line=None):
        self.manifest.write_text(line if line is not None else
                                 f"{self.digest}\t{self.file}\n")
        cmd = 'source "$1"; CPU_ROLLBACK_ROOT="$2"; cpu_fresh_rollback "$3"'
        return subprocess.run(["bash", "-c", cmd, "test", str(SCRIPT),
                               str(self.root), str(self.manifest)],
                              capture_output=True, text=True)

    def test_exact_owned_fixture_is_removed(self):
        result = self.run_rollback()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.file.exists())

    def test_modified_fixture_is_preserved(self):
        self.file.write_text("external change\n")
        result = self.run_rollback()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.file.read_text(), "external change\n")

    def test_symlink_fixture_is_not_followed(self):
        target = self.root / "real"
        target.write_text("important\n")
        self.file.unlink()
        self.file.symlink_to(target)
        result = self.run_rollback()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(target.read_text(), "important\n")

    def test_path_outside_allowlist_is_refused(self):
        result = self.run_rollback(f"{self.digest}\t/etc/example\n")
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(self.file.exists())

    def test_invalid_manifest_is_rejected(self):
        result = self.run_rollback(f"invalid\t{self.file}\n")
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(self.file.exists())

if __name__ == "__main__":
    unittest.main()
