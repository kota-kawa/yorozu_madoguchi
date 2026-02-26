#!/usr/bin/env python3
"""
EN: Provide the run unit tests module implementation.
JP: run_unit_tests モジュールの実装を定義する。
"""
import os
import pathlib
import sys
import unittest

ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent
TESTS_DIR = ROOT_DIR / "tests"
EXCLUDED_MODULES = {"test_api_e2e"}

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def _iter_test_cases(suite: unittest.TestSuite):
    """
    EN: Execute iter test cases processing.
    JP: _iter_test_cases の処理を実行する。
    """
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from _iter_test_cases(item)
        else:
            yield item


def _build_unit_suite() -> unittest.TestSuite:
    """
    EN: Execute build unit suite processing.
    JP: _build_unit_suite の処理を実行する。
    """
    loader = unittest.TestLoader()
    discovered = loader.discover(start_dir=str(TESTS_DIR), pattern="test_*.py")

    filtered_suite = unittest.TestSuite()
    for case in _iter_test_cases(discovered):
        module_name = case.__class__.__module__
        if module_name in EXCLUDED_MODULES:
            continue
        filtered_suite.addTest(case)
    return filtered_suite


def main() -> int:
    # Reservation-related unit tests import database.py.
    """
    EN: Run the main entrypoint flow.
    JP: メインの実行フローを開始する。
    """
    os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

    suite = _build_unit_suite()
    if suite.countTestCases() == 0:
        print("No unit tests were discovered.")
        return 1

    print("Excluded modules:", ", ".join(sorted(EXCLUDED_MODULES)))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
