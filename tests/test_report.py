import contextlib
import io
import json
import sys
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ft_ps_tester import cli


class ReportTests(unittest.TestCase):
    def run_report(self, basic, performance_failures):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / 'result.json'
            stats = {'size': 100, 'mode': 'simple', 'max': 0, 'min': 0,
                     'avg': 0, 'fails': len(performance_failures), 'warnings': 0}
            with patch.object(sys, 'argv', ['tester', '--report', str(report), sys.executable]), \
                 patch.object(cli, 'run_basic_tests', return_value=basic), \
                 patch.object(cli, 'run_test_suite', return_value=(stats, performance_failures, [])), \
                 contextlib.redirect_stdout(io.StringIO()):
                cli.main()
            return json.loads(report.read_text())

    def test_pass_and_incomplete(self):
        report = self.run_report((0, 0, True), [])
        self.assertEqual((report['total'], report['passed'], report['failed']), (801, 801, 0))
        self.assertTrue(report['incomplete'])

    def test_basic_and_performance_failures_are_counted(self):
        failure = {'size': 100, 'mode': 'simple', 'disorder': 0, 'reason': 'bad', 'ops': 0, 'limit': 1}
        report = self.run_report((3, 0, False), [failure])
        self.assertEqual((report['passed'], report['failed']), (792, 9))
        self.assertFalse(report['incomplete'])

    def test_nonzero_exit_is_not_a_pass(self):
        process = subprocess.CompletedProcess([], 1, '', '')
        with patch.object(cli, '_run_ps', return_value=process):
            self.assertFalse(cli._exec_and_check(sys.executable, [1])['is_sorted'])

    def test_memory_timeout_is_incomplete(self):
        timeout = {'timeout': True, 'tool': 'valgrind'}
        with patch.object(cli.shutil, 'which', return_value='/valgrind'), \
             patch.object(cli, '_run_memcheck', return_value=timeout), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.test_memory(sys.executable), (0, True))

    def test_missing_memory_tool_is_incomplete(self):
        with patch.object(cli.shutil, 'which', return_value=None), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.test_memory(sys.executable), (0, True))


if __name__ == '__main__':
    unittest.main()
