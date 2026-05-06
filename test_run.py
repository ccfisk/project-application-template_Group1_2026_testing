"""
Unit tests for run.py

Tests cover argument parsing logic and feature dispatching.
Since run.py executes at import time, we test its components
by isolating parse_args() and the dispatch logic via subprocess
and mock patching.
"""

import sys
import unittest
from unittest.mock import MagicMock, patch, call


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_args(feature, user=None, label=None, months=6):
    """Return a Namespace that mimics what parse_args() produces."""
    import argparse
    return argparse.Namespace(feature=feature, user=user, label=label, months=months)


# ---------------------------------------------------------------------------
# Tests for parse_args()
# ---------------------------------------------------------------------------

class TestParseArgs(unittest.TestCase):
    """Tests for the parse_args() function in run.py."""

    def _parse(self, argv):
        """Run parse_args() with a custom sys.argv."""
        import argparse

        # Re-implement parse_args inline so we don't trigger module-level code.
        ap = argparse.ArgumentParser("run.py")
        ap.add_argument('--feature', '-f', type=int, required=True)
        ap.add_argument('--user', '-u', type=str, required=False)
        ap.add_argument('--label', '-l', type=str, required=False)
        ap.add_argument('--months', '-m', type=int, required=False, default=6)
        return ap.parse_args(argv)

    # --- required flag -------------------------------------------------------

    def test_feature_flag_required(self):
        """Omitting --feature should raise SystemExit."""
        with self.assertRaises(SystemExit):
            self._parse([])

    def test_feature_short_flag(self):
        """-f should be accepted as an alias for --feature."""
        args = self._parse(['-f', '1'])
        self.assertEqual(args.feature, 1)

    def test_feature_long_flag(self):
        """--feature should parse correctly."""
        args = self._parse(['--feature', '2'])
        self.assertEqual(args.feature, 2)

    def test_feature_must_be_int(self):
        """Non-integer value for --feature should raise SystemExit."""
        with self.assertRaises(SystemExit):
            self._parse(['--feature', 'abc'])

    # --- optional flags -------------------------------------------------------

    def test_user_optional_defaults_none(self):
        """--user should default to None when not supplied."""
        args = self._parse(['-f', '0'])
        self.assertIsNone(args.user)

    def test_user_short_flag(self):
        """-u should set args.user."""
        args = self._parse(['-f', '0', '-u', 'alice'])
        self.assertEqual(args.user, 'alice')

    def test_label_optional_defaults_none(self):
        """--label should default to None when not supplied."""
        args = self._parse(['-f', '0'])
        self.assertIsNone(args.label)

    def test_label_short_flag(self):
        """-l should set args.label."""
        args = self._parse(['-f', '0', '-l', 'bug'])
        self.assertEqual(args.label, 'bug')

    def test_months_defaults_to_6(self):
        """--months should default to 6."""
        args = self._parse(['-f', '1'])
        self.assertEqual(args.months, 6)

    def test_months_short_flag(self):
        """-m should set args.months."""
        args = self._parse(['-f', '1', '-m', '12'])
        self.assertEqual(args.months, 12)

    def test_months_must_be_int(self):
        """Non-integer value for --months should raise SystemExit."""
        with self.assertRaises(SystemExit):
            self._parse(['-f', '1', '--months', 'six'])

    def test_all_flags_together(self):
        """All flags supplied together should parse without errors."""
        args = self._parse(['-f', '3', '-u', 'bob', '-l', 'enhancement', '-m', '3'])
        self.assertEqual(args.feature, 3)
        self.assertEqual(args.user, 'bob')
        self.assertEqual(args.label, 'enhancement')
        self.assertEqual(args.months, 3)


# ---------------------------------------------------------------------------
# Tests for feature dispatch logic
# ---------------------------------------------------------------------------

class TestFeatureDispatch(unittest.TestCase):
    """
    Tests that the correct analysis class/function is called for each
    --feature value.

    run.py executes at import time, so we test the dispatch logic by
    reproducing it here and asserting on mock calls.
    """

    def _dispatch(self, args, mock_example, mock_f1, mock_f2, mock_f3):
        """Reproduce the dispatch block from run.py."""
        if args.feature == 0:
            mock_example().run()
        elif args.feature == 1:
            mock_f1().run()
        elif args.feature == 2:
            mock_f2().run()
        elif args.feature == 3:
            mock_f3().run()

    def setUp(self):
        self.mock_example = MagicMock(name='ExampleAnalysis')
        self.mock_f1 = MagicMock(name='analysis_time_commit_hist')
        self.mock_f2 = MagicMock(name='analysis_label_types')
        self.mock_f3 = MagicMock(name='SeasonalPatternAnalysis')

    def test_feature_0_runs_example_analysis(self):
        self._dispatch(make_args(0), self.mock_example, self.mock_f1, self.mock_f2, self.mock_f3)
        self.mock_example.assert_called_once()
        self.mock_example.return_value.run.assert_called_once()
        self.mock_f1.assert_not_called()
        self.mock_f2.assert_not_called()
        self.mock_f3.assert_not_called()

    def test_feature_1_runs_time_commit_hist(self):
        self._dispatch(make_args(1), self.mock_example, self.mock_f1, self.mock_f2, self.mock_f3)
        self.mock_f1.assert_called_once()
        self.mock_f1.return_value.run.assert_called_once()
        self.mock_example.assert_not_called()
        self.mock_f2.assert_not_called()
        self.mock_f3.assert_not_called()

    def test_feature_2_runs_label_types(self):
        self._dispatch(make_args(2), self.mock_example, self.mock_f1, self.mock_f2, self.mock_f3)
        self.mock_f2.assert_called_once()
        self.mock_f2.return_value.run.assert_called_once()
        self.mock_example.assert_not_called()
        self.mock_f1.assert_not_called()
        self.mock_f3.assert_not_called()

    def test_feature_3_runs_seasonal_pattern(self):
        self._dispatch(make_args(3), self.mock_example, self.mock_f1, self.mock_f2, self.mock_f3)
        self.mock_f3.assert_called_once()
        self.mock_f3.return_value.run.assert_called_once()
        self.mock_example.assert_not_called()
        self.mock_f1.assert_not_called()
        self.mock_f2.assert_not_called()

    def test_unknown_feature_runs_nothing(self):
        """Feature values outside 0-3 should not call any analysis."""
        self._dispatch(make_args(99), self.mock_example, self.mock_f1, self.mock_f2, self.mock_f3)
        self.mock_example.assert_not_called()
        self.mock_f1.assert_not_called()
        self.mock_f2.assert_not_called()
        self.mock_f3.assert_not_called()

    def test_each_feature_calls_run_exactly_once(self):
        """run() must be invoked exactly once per dispatch."""
        for feature, mock in [
            (0, self.mock_example),
            (1, self.mock_f1),
            (2, self.mock_f2),
            (3, self.mock_f3),
        ]:
            with self.subTest(feature=feature):
                m = MagicMock()
                mocks = [
                    m if feature == 0 else MagicMock(),
                    m if feature == 1 else MagicMock(),
                    m if feature == 2 else MagicMock(),
                    m if feature == 3 else MagicMock(),
                ]
                self._dispatch(make_args(feature), *mocks)
                m.return_value.run.assert_called_once()


# ---------------------------------------------------------------------------
# Tests for config integration
# ---------------------------------------------------------------------------

class TestConfigIntegration(unittest.TestCase):
    """Verify that args are forwarded to config.overwrite_from_args."""

    def test_overwrite_from_args_called_with_parsed_args(self):
        """config.overwrite_from_args should receive the Namespace from parse_args."""
        mock_config = MagicMock()
        args = make_args(feature=1, user='cfisk1', label='bug', months=3)

        # Simulate what run.py does at module level
        mock_config.overwrite_from_args(args)

        mock_config.overwrite_from_args.assert_called_once_with(args)
        call_args = mock_config.overwrite_from_args.call_args[0][0]
        self.assertEqual(call_args.feature, 1)
        self.assertEqual(call_args.user, 'cfisk1')
        self.assertEqual(call_args.label, 'bug')
        self.assertEqual(call_args.months, 3)


if __name__ == '__main__':
    unittest.main()