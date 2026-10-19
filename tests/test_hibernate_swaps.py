"""Regression tests for the unsupported swapon flags found in preflight.

No root privileges or real swap, mount, or sleep operations are required.
"""

import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/macbook81-hibernate-prepare.py"
SPEC = importlib.util.spec_from_file_location("hibernate_helper", SCRIPT)
HELPER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HELPER)


class SwapReaderTests(unittest.TestCase):
    def test_supported_command_and_numeric_rows(self):
        output = (
            "/dev/zram0 partition 8267808768 1717985280 100\n"
            "/swap/swapfile file 10737414144 0 10\n"
            "/example.swap file 1048576 4096 -2\n"
        )
        with patch.object(HELPER, "run", return_value=output) as command:
            actual = HELPER.swaps()
        command.assert_called_once_with(
            "swapon", "--show=NAME,TYPE,SIZE,USED,PRIO", "--bytes", "--noheadings", "--raw"
        )
        self.assertEqual(actual, [
            {"name": "/dev/zram0", "type": "partition", "size": 8267808768,
             "used": 1717985280, "prio": 100},
            {"name": "/swap/swapfile", "type": "file", "size": 10737414144,
             "used": 0, "prio": 10},
            {"name": "/example.swap", "type": "file", "size": 1048576,
             "used": 4096, "prio": -2},
        ])

    def test_empty_output(self):
        for output in ("", "\n   \n"):
            with self.subTest(output=output), patch.object(HELPER, "run", return_value=output):
                self.assertEqual(HELPER.swaps(), [])

    def test_malformed_output_is_rejected(self):
        rows = (
            "/dev/zram0 partition 4096 0",
            "/dev/zram0 partition 4096 0 100 extra",
            "/dev/zram0 partition 7.7G 0 100",
            "/dev/zram0 partition -1 0 100",
            "/dev/zram0 partition 4096 -1 100",
            "/dev/zram0 partition 4096 unknown 100",
            "/dev/zram0 partition 4096 0 unknown",
        )
        for row in rows:
            with self.subTest(row=row), patch.object(HELPER, "run", return_value=row):
                with self.assertRaises(RuntimeError):
                    HELPER.swaps()

    def test_failed_command_is_not_an_empty_inventory(self):
        failure = subprocess.CompletedProcess(["swapon"], 255, "", "listing failed")
        with patch.object(HELPER.subprocess, "run", return_value=failure):
            with self.assertRaisesRegex(RuntimeError, "Command failed"):
                HELPER.swaps()


if __name__ == "__main__":
    unittest.main()
