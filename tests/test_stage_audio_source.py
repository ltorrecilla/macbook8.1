#!/usr/bin/env python3
"""Test the audio archive stager without hardware, root or real user files."""
import importlib.util
from io import BytesIO
from pathlib import Path
import tarfile
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1] / "scripts" / "stage-audio-source.py"
spec = importlib.util.spec_from_file_location("mb81_stager", MODULE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class StageTests(unittest.TestCase):
    @staticmethod
    def make_archive(path, omitted=None, extra=None):
        with tarfile.open(path, "w:gz") as tf:
            for name in sorted(mod.REQUIRED):
                if name == omitted:
                    continue
                data = (b'PACKAGE_NAME="macbook12-audio"\nsnd-hda-codec-cs420x\n'
                        b'snd-hda-codec-generic\nsnd-hda-intel\n') if name == "source/dkms.conf" else (name + "\n").encode()
                info = tarfile.TarInfo("./" + name)
                info.size = len(data)
                tf.addfile(info, BytesIO(data))
            if extra:
                data = b'private report not to be staged'
                info = tarfile.TarInfo("./" + extra)
                info.size = len(data)
                tf.addfile(info, BytesIO(data))

    def test_allowlisted_files_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            archive = root / "input.tar.gz"
            self.make_archive(archive, extra="report.txt")
            out = root / "bundle"
            self.assertEqual(mod.stage(archive, out), len(mod.REQUIRED))
            self.assertTrue((out / "source/dkms.conf").is_file())
            self.assertTrue((out / "MANIFEST.json").is_file())
            self.assertFalse((out / "report.txt").exists())
            with self.assertRaises(ValueError):
                mod.stage(archive, out)

    def test_missing_file_has_no_partial_output(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            archive = root / "input.tar.gz"
            self.make_archive(archive, omitted="source/dkms.conf")
            out = root / "bundle"
            with self.assertRaises(ValueError):
                mod.stage(archive, out)
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
