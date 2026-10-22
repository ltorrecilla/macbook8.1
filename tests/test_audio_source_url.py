#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Regression cases for source archive naming (no hardware needed)."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    "repair_audio", Path(__file__).resolve().parents[1] / "scripts" / "repair-audio.py"
)
module = importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name] = module
spec.loader.exec_module(module)

class KernelUrlTests(unittest.TestCase):
    def url(self, version):
        return module.Kernel(version, "linux-cachyos", Path("/unused")).url

    def test_zero_patch_uses_shortened_upstream_archive(self):
        self.assertEqual(self.url("7.3.0-2-cachyos"),
            "https://cdn.kernel.org/pub/linux/kernel/v7.x/linux-7.3.tar.xz")

    def test_nonzero_patch_is_preserved(self):
        self.assertEqual(self.url("7.2.11-1-cachyos"),
            "https://cdn.kernel.org/pub/linux/kernel/v7.x/linux-7.2.11.tar.xz")

    def test_lts_zero_patch(self):
        self.assertEqual(self.url("6.18.0-2-cachyos-lts"),
            "https://cdn.kernel.org/pub/linux/kernel/v6.x/linux-6.18.tar.xz")

    def test_rejects_prerelease(self):
        with self.assertRaises(module.Stop):
            self.url("7.3.0-rc1-cachyos")

if __name__ == "__main__":
    unittest.main()
