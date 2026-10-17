#!/usr/bin/env python3
"""Hardware-free tests for the read-only source/support archive audit."""
import importlib.util
from io import BytesIO
from pathlib import Path
import tarfile
import tempfile
import unittest

module_path = Path(__file__).resolve().parents[1] / "scripts" / "audit-audio-bundles.py"
spec = importlib.util.spec_from_file_location("mb81_audit", module_path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def mkarchive(path, entries):
    with tarfile.open(path, "w:gz") as t:
        for name, data in entries.items():
            info = tarfile.TarInfo("./" + name)
            info.size = len(data)
            t.addfile(info, BytesIO(data))


class AudioAuditTests(unittest.TestCase):
    def fixtures(self, root, corrupt=False):
        src = root / "details.tar.gz"
        support = root / "support.tar.gz"
        sources = {name: b"header\n" for name in mod.SOURCE_FILES}
        sources["source/dkms.conf"] = b"snd-hda-codec-cs420x snd-hda-codec-generic snd-hda-intel"
        sources["source/install.sh"] = b"update-initramfs"
        sources["source/dkms.sh"] = b"rm -rf $var_dkms_dir"
        sources["source/mb81-jack-switch.sh"] = b"input.MacBook_Speaker"
        mkarchive(src, sources)
        contents = {
            "efi_recover.py": b'os.open(f"{PCIDEV}/resource0"',
            "mb81-resume-recover.service": b"ExecStart=/usr/local/bin/mb81-resume-recover",
            "mb81-jack-switch.service": b"ExecStart=/usr/local/bin/mb81-jack-switch",
        }
        entries = {}
        for i, (name, data) in enumerate(contents.items(), 1):
            entries[f"files/{i:03d}-{name}"] = data
            entries[f"files/{i+3:03d}-{name}"] = data + (b"oops" if corrupt and i == 1 else b"")
        mkarchive(support, entries)
        return src, support

    def test_complete_consistent_bundle(self):
        with tempfile.TemporaryDirectory() as temp:
            src, support = self.fixtures(Path(temp))
            ok, errors, notes = mod.audit(src, support)
            self.assertTrue(ok)
            self.assertFalse(errors)
            self.assertTrue(any("RISK" in note for note in notes))

    def test_disagreeing_copies_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            src, support = self.fixtures(Path(temp), corrupt=True)
            ok, errors, _ = mod.audit(src, support)
            self.assertFalse(ok)
            self.assertTrue(any("differ" in error for error in errors))

    def test_unsafe_archive_member_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            archive = Path(temp) / "bad.tar.gz"
            mkarchive(archive, {"../malicious.txt": b"evil"})
            with self.assertRaises(mod.AuditFailure):
                mod.read_tar(archive, allow_support=True)


if __name__ == "__main__":
    unittest.main()
