import unittest
from unittest.mock import MagicMock, patch
import pandas as pd


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_issue(created_date):
    """Return a mock Issue with the given created_date."""
    issue = MagicMock()
    issue.created_date = created_date
    return issue


def _now():
    """
    Return the current time as a tz-naive Timestamp.

    The production code converts dates with pd.to_datetime(utc=True) then
    immediately strips tz with .dt.tz_localize(None), and builds the cutoff
    with .replace(tzinfo=None). Both sides of the comparison are tz-naive, so
    mock dates must be tz-naive too.
    """
    return pd.Timestamp.now()  # no tz


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestAnalysisTimeCommitHist(unittest.TestCase):

    def _make_analysis(self, months=6):
        with patch("config.get_parameter", return_value=months):
            from feature1_analysis import analysis_time_commit_hist
            return analysis_time_commit_hist()

    def _run_with_issues(self, issues, months=6, capture=False):
        """
        Run analysis with issues and months patched.
        If capture=True, patches pd.Series.plot to capture weekly_counts.
        Returns list of captured Series.
        """
        captured = []

        def capture_plot(self, *args, **kwargs):
            captured.append(self.copy())
            return MagicMock()

        patches = [
            patch("config.get_parameter", return_value=months),
            patch("data_loader.DataLoader.get_issues", return_value=issues),
            patch("matplotlib.pyplot.show"),
            patch("matplotlib.pyplot.tight_layout"),
        ]
        if capture:
            patches.append(patch.object(pd.Series, "plot", capture_plot))

        with patches[0], patches[1], patches[2], patches[3]:
            if capture:
                with patches[4]:
                    from feature1_analysis import analysis_time_commit_hist
                    analysis_time_commit_hist().run()
            else:
                from feature1_analysis import analysis_time_commit_hist
                analysis_time_commit_hist().run()

        return captured

    # ------------------------------------------------------------------
    # __init__ / config
    # ------------------------------------------------------------------

    def test_default_months_is_6(self):
        """Constructor stores 6 when config returns the default."""
        self.assertEqual(self._make_analysis(months=6).months, 6)

    def test_custom_months_stored(self):
        """Constructor stores whatever value config returns."""
        self.assertEqual(self._make_analysis(months=3).months, 3)

    # ------------------------------------------------------------------
    # Happy path
    # ------------------------------------------------------------------

    def test_run_happy_path(self):
        """run() completes without error for a normal set of recent issues."""
        now = _now()
        issues = [
            _make_issue(now - pd.DateOffset(weeks=1)),
            _make_issue(now - pd.DateOffset(weeks=2)),
            _make_issue(now - pd.DateOffset(weeks=3)),
        ]
        self._run_with_issues(issues, months=6)  # no exception == pass

    # ------------------------------------------------------------------
    # Edge cases – date filtering
    # ------------------------------------------------------------------

    def test_issues_outside_window_are_excluded(self):
        """Issues older than `months` must not appear in the plot data."""
        now = _now()
        issues = [
            _make_issue(now - pd.DateOffset(weeks=1)),    # inside window
            _make_issue(now - pd.DateOffset(months=12)),  # outside window
        ]
        captured = self._run_with_issues(issues, months=6, capture=True)
        self.assertTrue(len(captured) > 0)
        self.assertEqual(captured[0].sum(), 1)

    def test_no_issues_runs_without_error(self):
        """run() prints a message and returns cleanly when there are no issues."""
        self._run_with_issues([], months=6)  # no exception == pass

    def test_issues_with_none_date_are_skipped(self):
        """Issues with created_date=None must be silently ignored."""
        now = _now()
        issues = [
            _make_issue(None),
            _make_issue(now - pd.DateOffset(weeks=1)),
        ]
        self._run_with_issues(issues, months=6)  # no exception == pass

    def test_all_issues_outside_window_no_plot(self):
        """If every issue is too old, run() returns early with no plot."""
        now = _now()
        issues = [_make_issue(now - pd.DateOffset(years=2))]
        captured = self._run_with_issues(issues, months=6, capture=True)
        self.assertEqual(len(captured), 0)

    # ------------------------------------------------------------------
    # Edge cases – months parameter
    # ------------------------------------------------------------------

    def test_months_1_only_shows_last_month(self):
        """With months=1, only issues from the last ~30 days are included."""
        now = _now()
        issues = [
            _make_issue(now - pd.DateOffset(weeks=2)),   # inside window
            _make_issue(now - pd.DateOffset(months=3)),  # outside window
        ]
        captured = self._run_with_issues(issues, months=1, capture=True)
        self.assertEqual(captured[0].sum(), 1)

    def test_large_months_value_includes_older_issues(self):
        """With months=24, issues up to 2 years old are included."""
        now = _now()
        issues = [
            _make_issue(now - pd.DateOffset(months=18)),
            _make_issue(now - pd.DateOffset(months=1)),
        ]
        captured = self._run_with_issues(issues, months=24, capture=True)
        self.assertEqual(captured[0].sum(), 2)


if __name__ == "__main__":
    unittest.main()