"""Mocked regression tests for the read-only MacBook8,1 kernel preflight."""
import contextlib
import importlib.util
import io
import pathlib
import unittest
from unittest import mock

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts/check-kernel-update.py"
spec = importlib.util.spec_from_file_location("macbook81_kernel_check", SCRIPT)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)

OLD = "__initstub__kmod_dw_dmac_pci__437_139_dw_pci_driver_init6"
NEW = "__initstub__kmod_dw_dmac_pci__442_139_dw_pci_driver_init6"
MODULES = checker.MODULES


class KernelRegressionTests(unittest.TestCase):
    def run_case(self, *, versions=("7.2.11-1-cachyos", "7.3.0-2-cachyos"),
                 running="7.2.11-1-cachyos", symbols=None,
                 config=None, cmdline=None, missing_modules=(), model="MacBook8,1"):
        symbols = symbols if symbols is not None else {
            "7.2.11-1-cachyos": OLD, "7.3.0-2-cachyos": NEW
        }
        config = OLD if config is None else config
        cmdline = OLD if cmdline is None else cmdline
        folders = [pathlib.Path("/usr/lib/modules") / version for version in versions]
        exists = set()
        source = {
            "/sys/class/dmi/id/product_name": model,
            "/etc/default/limine": config,
            "/proc/cmdline": cmdline,
            "/proc/kallsyms": symbols.get(running, ""),
        }
        for folder in folders:
            exists.update((str(folder / "vmlinuz"), str(folder / "pkgbase")))
            source[str(folder / "pkgbase")] = "linux-cachyos"
            if folder.name != running and folder.name in symbols:
                path = str(folder / "build/System.map")
                exists.add(path)
                source[path] = symbols[folder.name]
            for module in MODULES:
                if (folder.name, module) not in missing_modules:
                    exists.add(str(folder / "updates/dkms" / (module + ".ko.zst")))

        real_glob = pathlib.Path.glob
        real_is_file = pathlib.Path.is_file
        def glob(path, pattern):
            if str(path) == "/usr/lib/modules" and pattern == "*":
                return folders
            return real_glob(path, pattern)
        def is_file(path):
            if str(path).startswith("/usr/lib/modules/") or str(path).startswith("/boot/System.map-"):
                return str(path) in exists
            return real_is_file(path)
        def read(path):
            return source.get(str(path), "")
        def command(*args):
            if args[:1] == ("uname",):
                return running
            if len(args) == 5 and args[:1] == ("modinfo",):
                version, module = args[2], args[4]
                return str(pathlib.Path("/usr/lib/modules") / version / "updates/dkms" /
                           (module + ".ko.zst"))
            return "disabled" if "is-enabled" in args else "inactive"

        capture = io.StringIO()
        with mock.patch.object(checker, "read", side_effect=read), \
             mock.patch.object(checker, "command", side_effect=command), \
             mock.patch.object(pathlib.Path, "glob", autospec=True, side_effect=glob), \
             mock.patch.object(pathlib.Path, "is_file", autospec=True, side_effect=is_file), \
             mock.patch.dict("os.environ", {}, clear=True), \
             contextlib.redirect_stdout(capture):
            status = checker.main()
        return status, capture.getvalue()

    def test_changed_symbol_blocks_new_kernel(self):
        status, report = self.run_case()
        self.assertEqual(status, 2)
        self.assertIn("SPI NOT READY", report)
        self.assertIn(NEW, report)
        self.assertIn("REVIEW REQUIRED", report)

    def test_both_verified_symbols_does_not_claim_hardware_proof(self):
        status, report = self.run_case(config=OLD + "," + NEW)
        self.assertEqual(status, 0)
        self.assertEqual(report.count("SPI CONFIGURED"), 2)
        self.assertIn("does not prove hardware", report)

    def test_missing_future_kernel_symbol_is_unverified(self):
        status, report = self.run_case(symbols={"7.2.11-1-cachyos": OLD},
                                       config=OLD + "," + NEW)
        self.assertEqual(status, 2)
        self.assertIn("SPI UNVERIFIED", report)

    def test_running_cmdline_missing_active_symbol(self):
        status, report = self.run_case(
            versions=("7.2.11-1-cachyos",), config=OLD, cmdline="quiet splash")
        self.assertEqual(status, 2)
        self.assertIn("SPI NOT ACTIVE", report)

    def test_missing_audio_module_blocks_even_if_spi_configured(self):
        status, report = self.run_case(
            versions=("7.2.11-1-cachyos",),
            missing_modules={("7.2.11-1-cachyos", MODULES[0])})
        self.assertEqual(status, 2)
        self.assertIn("AUDIO NOT READY", report)

    def test_wrong_model_stops_before_kernel_scan(self):
        status, report = self.run_case(model="MacBook9,1")
        self.assertEqual(status, 2)
        self.assertIn("only for MacBook8,1", report)

    def test_no_kernels_stops(self):
        status, report = self.run_case(versions=())
        self.assertEqual(status, 2)
        self.assertIn("No installed CachyOS kernel", report)


if __name__ == "__main__":
    unittest.main()
