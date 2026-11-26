"""CLI contract: --demo reproduces the reference total; argument and path errors exit cleanly."""

import io
import os
import re
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

from ecostream.cli import main

ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def _run(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_demo_reproduces_reference_total(self):
        code, out, _ = self._run(["--demo", "--runs-dir", self.tmp.name])
        self.assertEqual(code, 0)
        self.assertIn("Tổng:    1594.699 tCO2e", out)

    def test_run_id_recalculates_existing_session(self):
        _, out, _ = self._run(["--demo", "--runs-dir", self.tmp.name])
        run_id = re.search(r"Mã phiên: (\S+)", out).group(1)
        code, out2, _ = self._run(["--run-id", run_id, "--runs-dir", self.tmp.name])
        self.assertEqual(code, 0)
        self.assertIn("Tổng:    1594.699 tCO2e", out2)

    def test_missing_input_path_returns_error_code(self):
        code, _, err = self._run(["--input", os.path.join(self.tmp.name, "khong_co.xlsx"), "--runs-dir", self.tmp.name])
        self.assertEqual(code, 2)
        self.assertIn("Không tìm thấy", err)

    def test_requires_exactly_one_mode(self):
        with self.assertRaises(SystemExit) as cm:
            self._run([])
        self.assertEqual(cm.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
