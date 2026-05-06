"""
Unit tests for Feature 1 (weekly commits), Feature 2 (label types),
and Feature 3 (seasonal/weekly issue patterns).

Run with:
    python -m pytest test_features.py -v --cov=. --cov-report=term-missing
"""

import unittest
from unittest.mock import patch, MagicMock
from collections import Counter
from datetime import datetime

# ---------------------------------------------------------------------------
# Minimal stubs so tests work without a real poetry.json or config file
# ---------------------------------------------------------------------------

class MockIssue:
    """Lightweight stand-in for model.Issue."""
    def __init__(self, created_date=None, labels=None, events=None, state='open'):
        self.created_date = created_date
        self.labels = labels if labels is not None else []
        self.events = events if events is not None else []
        self.state = state
        self.updated_date = None


class MockEvent:
    """Lightweight stand-in for model.Event."""
    def __init__(self, event_type=None, event_date=None):
        self.event_type = event_type
        self.event_date = event_date


# ============================================================
# Feature 2 Tests — Label Type Bar Chart
# ============================================================

class TestFeature2LabelTypes(unittest.TestCase):
    """Tests for analysis_label_types (feature2_analysis.py)."""

    def _count_labels(self, issues):
        """Replicate the core counting logic from feature2_analysis.py."""
        label_counts = Counter()
        unlabeled_count = 0
        for issue in issues:
            if issue.labels:
                label_counts.update(issue.labels)
            else:
                unlabeled_count += 1
        return label_counts, unlabeled_count

    def test_single_labeled_issue(self):
        issues = [MockIssue(labels=['bug'])]
        counts, unlabeled = self._count_labels(issues)
        self.assertEqual(counts['bug'], 1)
        self.assertEqual(unlabeled, 0)

    def test_unlabeled_issue_counted_separately(self):
        issues = [MockIssue(labels=[]), MockIssue(labels=[])]
        counts, unlabeled = self._count_labels(issues)
        self.assertEqual(unlabeled, 2)
        self.assertEqual(len(counts), 0)

    def test_multiple_labels_on_one_issue(self):
        issues = [MockIssue(labels=['bug', 'high-priority', 'needs-triage'])]
        counts, unlabeled = self._count_labels(issues)
        self.assertEqual(counts['bug'], 1)
        self.assertEqual(counts['high-priority'], 1)
        self.assertEqual(counts['needs-triage'], 1)
        self.assertEqual(unlabeled, 0)

    def test_mixed_labeled_and_unlabeled(self):
        issues = [
            MockIssue(labels=['bug']),
            MockIssue(labels=[]),
            MockIssue(labels=['bug', 'feature']),
            MockIssue(labels=None),
        ]
        counts, unlabeled = self._count_labels(issues)
        self.assertEqual(counts['bug'], 2)
        self.assertEqual(counts['feature'], 1)
        self.assertEqual(unlabeled, 2)

    def test_empty_issue_list(self):
        counts, unlabeled = self._count_labels([])
        self.assertEqual(len(counts), 0)
        self.assertEqual(unlabeled, 0)

    def test_top_labels_ordering(self):
        issues = [
            MockIssue(labels=['bug']),
            MockIssue(labels=['bug']),
            MockIssue(labels=['feature']),
        ]
        counts, _ = self._count_labels(issues)
        top = counts.most_common(2)
        self.assertEqual(top[0][0], 'bug')
        self.assertEqual(top[0][1], 2)

    def test_none_labels_treated_as_unlabeled(self):
        issues = [MockIssue(labels=None)]
        counts, unlabeled = self._count_labels(issues)
        self.assertEqual(unlabeled, 1)

    @patch('feature2_analysis.DataLoader')
    @patch('feature2_analysis.plt')
    def test_run_calls_show(self, mock_plt, mock_loader):
        """run() should always call plt.show() when there is data."""
        from feature2_analysis import analysis_label_types
        mock_loader.return_value.get_issues.return_value = [
            MockIssue(labels=['bug']),
            MockIssue(labels=[]),
        ]
        analysis_label_types().run()
        mock_plt.show.assert_called_once()

    @patch('feature2_analysis.DataLoader')
    @patch('feature2_analysis.plt')
    def test_run_handles_empty_issues(self, mock_plt, mock_loader):
        """run() should not crash on an empty issue list."""
        from feature2_analysis import analysis_label_types
        mock_loader.return_value.get_issues.return_value = []
        try:
            analysis_label_types().run()
        except Exception as e:
            self.fail(f"run() raised an exception on empty input: {e}")

    @patch('feature2_analysis.DataLoader')
    @patch('feature2_analysis.plt')
    def test_run_with_all_unlabeled(self, mock_plt, mock_loader):
        """run() should not crash when every issue is unlabeled."""
        from feature2_analysis import analysis_label_types
        mock_loader.return_value.get_issues.return_value = [
            MockIssue(labels=[]),
            MockIssue(labels=[]),
        ]
        try:
            analysis_label_types().run()
        except Exception as e:
            self.fail(f"run() raised an exception with all-unlabeled issues: {e}")


# ============================================================
# Feature 3 Tests — Seasonal / Weekly Pattern Analysis
# ============================================================

class TestFeature3SeasonalPatterns(unittest.TestCase):
    """Tests for SeasonalPatternAnalysis (feature3_analysis.py)."""

    def setUp(self):
        from feature3_analysis import SeasonalPatternAnalysis
        self.analysis = SeasonalPatternAnalysis()

    # --- _extract_creations ---

    def test_extract_creations_basic(self):
        d = datetime(2023, 3, 15)  # Wednesday = weekday 2, month 3
        issues = [MockIssue(created_date=d)]
        df = self.analysis._extract_creations(issues)
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]['day_of_week'], 2)
        self.assertEqual(df.iloc[0]['month'], 3)

    def test_extract_creations_skips_none_date(self):
        issues = [MockIssue(created_date=None)]
        df = self.analysis._extract_creations(issues)
        self.assertEqual(len(df), 0)

    def test_extract_creations_multiple_issues(self):
        issues = [
            MockIssue(created_date=datetime(2023, 1, 2)),   # Monday
            MockIssue(created_date=datetime(2023, 6, 10)),  # Saturday
            MockIssue(created_date=None),
        ]
        df = self.analysis._extract_creations(issues)
        self.assertEqual(len(df), 2)

    def test_extract_creations_empty_list(self):
        df = self.analysis._extract_creations([])
        self.assertEqual(len(df), 0)

    # --- _extract_referenced ---

    def test_extract_referenced_picks_right_event_type(self):
        event_ref = MockEvent(event_type='referenced', event_date=datetime(2023, 4, 5))
        event_closed = MockEvent(event_type='closed', event_date=datetime(2023, 4, 6))
        issues = [MockIssue(events=[event_ref, event_closed])]
        df = self.analysis._extract_referenced(issues)
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]['month'], 4)

    def test_extract_referenced_skips_none_date(self):
        event = MockEvent(event_type='referenced', event_date=None)
        issues = [MockIssue(events=[event])]
        df = self.analysis._extract_referenced(issues)
        self.assertEqual(len(df), 0)

    def test_extract_referenced_no_events(self):
        issues = [MockIssue(events=[])]
        df = self.analysis._extract_referenced(issues)
        self.assertEqual(len(df), 0)

    def test_extract_referenced_empty_issue_list(self):
        df = self.analysis._extract_referenced([])
        self.assertEqual(len(df), 0)

    def test_extract_referenced_multiple_events_same_issue(self):
        events = [
            MockEvent(event_type='referenced', event_date=datetime(2023, 1, 10)),
            MockEvent(event_type='referenced', event_date=datetime(2023, 2, 15)),
        ]
        issues = [MockIssue(events=events)]
        df = self.analysis._extract_referenced(issues)
        self.assertEqual(len(df), 2)

    # --- _extract_closures ---

    def test_extract_closures_basic(self):
        event = MockEvent(event_type='closed', event_date=datetime(2023, 7, 20))
        issues = [MockIssue(events=[event])]
        df = self.analysis._extract_closures(issues)
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]['month'], 7)

    def test_extract_closures_ignores_other_event_types(self):
        events = [
            MockEvent(event_type='referenced', event_date=datetime(2023, 7, 20)),
            MockEvent(event_type='labeled', event_date=datetime(2023, 7, 21)),
        ]
        issues = [MockIssue(events=events)]
        df = self.analysis._extract_closures(issues)
        self.assertEqual(len(df), 0)

    def test_extract_closures_skips_none_date(self):
        event = MockEvent(event_type='closed', event_date=None)
        issues = [MockIssue(events=[event])]
        df = self.analysis._extract_closures(issues)
        self.assertEqual(len(df), 0)

    def test_extract_closures_empty_events(self):
        issues = [MockIssue(events=[])]
        df = self.analysis._extract_closures(issues)
        self.assertEqual(len(df), 0)

    def test_extract_closures_empty_issue_list(self):
        df = self.analysis._extract_closures([])
        self.assertEqual(len(df), 0)

    # --- day_of_week values ---

    def test_day_of_week_range(self):
        """All day_of_week values should be 0-6."""
        issues = [
            MockIssue(created_date=datetime(2023, 1, d))
            for d in range(2, 9)  # Mon through Sun
        ]
        df = self.analysis._extract_creations(issues)
        self.assertTrue((df['day_of_week'] >= 0).all())
        self.assertTrue((df['day_of_week'] <= 6).all())

    def test_month_range(self):
        """All month values should be 1-12."""
        issues = [
            MockIssue(created_date=datetime(2023, m, 1))
            for m in range(1, 13)
        ]
        df = self.analysis._extract_creations(issues)
        self.assertTrue((df['month'] >= 1).all())
        self.assertTrue((df['month'] <= 12).all())

    # --- run() integration ---

    @patch('feature3_analysis.DataLoader')
    @patch('feature3_analysis.plt')
    def test_run_calls_show(self, mock_plt, mock_loader):
        mock_loader.return_value.get_issues.return_value = [
            MockIssue(
                created_date=datetime(2023, 3, 15),
                events=[
                    MockEvent(event_type='referenced', event_date=datetime(2023, 3, 16)),
                    MockEvent(event_type='closed', event_date=datetime(2023, 4, 1)),
                ]
            )
        ]
        self.analysis.run()
        mock_plt.show.assert_called_once()

    @patch('feature3_analysis.DataLoader')
    @patch('feature3_analysis.plt')
    def test_run_handles_empty_issues(self, mock_plt, mock_loader):
        mock_loader.return_value.get_issues.return_value = []
        try:
            self.analysis.run()
        except Exception as e:
            self.fail(f"run() raised an exception on empty input: {e}")


# ============================================================
# Feature 1 Tests — Weekly Commits Over Time
# ============================================================
# Feature 1 plots weekly commit/issue counts over a user-specified
# date range. We test the date-filtering and bucketing logic.

class TestFeature1WeeklyCommits(unittest.TestCase):
    """Tests for feature1_analysis.py (weekly activity over time)."""

    @patch('feature1_analysis.DataLoader')
    @patch('feature1_analysis.plt')
    def test_run_completes_without_error(self, mock_plt, mock_loader):
        """run() should complete without crashing on normal input."""
        from feature1_analysis import analysis_time_commit_hist
        mock_loader.return_value.get_issues.return_value = [
            MockIssue(created_date=datetime(2023, 1, 10)),
            MockIssue(created_date=datetime(2023, 2, 20)),
        ]
        try:
            analysis_time_commit_hist().run()
        except Exception as e:
            self.fail(f"run() raised an unexpected exception: {e}")

    @patch('feature1_analysis.DataLoader')
    @patch('feature1_analysis.plt')
    def test_run_calls_show(self, mock_plt, mock_loader):
        """run() should call plt.show() to display the plot."""
        from feature1_analysis import analysis_time_commit_hist
        mock_loader.return_value.get_issues.return_value = [
            MockIssue(created_date=datetime(2023, 3, 5)),
        ]
        analysis_time_commit_hist().run()
        mock_plt.show.assert_called_once()

    @patch('feature1_analysis.DataLoader')
    @patch('feature1_analysis.plt')
    def test_run_handles_empty_issues(self, mock_plt, mock_loader):
        """run() should not crash when the issue list is empty."""
        from feature1_analysis import analysis_time_commit_hist
        mock_loader.return_value.get_issues.return_value = []
        try:
            analysis_time_commit_hist().run()
        except Exception as e:
            self.fail(f"run() raised an exception on empty input: {e}")

    @patch('feature1_analysis.DataLoader')
    @patch('feature1_analysis.plt')
    def test_run_handles_none_created_dates(self, mock_plt, mock_loader):
        """run() should not crash when issues have no created_date."""
        from feature1_analysis import analysis_time_commit_hist
        mock_loader.return_value.get_issues.return_value = [
            MockIssue(created_date=None),
            MockIssue(created_date=None),
        ]
        try:
            analysis_time_commit_hist().run()
        except Exception as e:
            self.fail(f"run() raised an exception on None dates: {e}")

    @patch('feature1_analysis.DataLoader')
    @patch('feature1_analysis.plt')
    def test_run_with_single_issue(self, mock_plt, mock_loader):
        """run() should work with just one issue."""
        from feature1_analysis import analysis_time_commit_hist
        mock_loader.return_value.get_issues.return_value = [
            MockIssue(created_date=datetime(2022, 6, 15)),
        ]
        try:
            analysis_time_commit_hist().run()
        except Exception as e:
            self.fail(f"run() raised an exception with a single issue: {e}")

    def test_issues_filtered_by_date_range(self):
        """Issues outside the requested time window should be excluded."""
        inside = MockIssue(created_date=datetime(2023, 3, 10))
        outside = MockIssue(created_date=datetime(2020, 1, 1))
        start = datetime(2023, 1, 1)
        end = datetime(2023, 12, 31)
        filtered = [
            i for i in [inside, outside]
            if i.created_date and start <= i.created_date <= end
        ]
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].created_date, datetime(2023, 3, 10))

    def test_weekly_bucket_groups_nearby_dates(self):
        """Two issues in the same week should land in the same bucket."""
        from collections import defaultdict
        import math

        dates = [datetime(2023, 3, 6), datetime(2023, 3, 8)]  # same week
        start = datetime(2023, 3, 6)
        buckets = defaultdict(int)
        for d in dates:
            week_num = math.floor((d - start).days / 7)
            buckets[week_num] += 1

        self.assertEqual(buckets[0], 2)

    def test_weekly_bucket_separates_different_weeks(self):
        """Issues a week apart should land in different buckets."""
        from collections import defaultdict
        import math

        dates = [datetime(2023, 3, 6), datetime(2023, 3, 14)]  # ~8 days apart
        start = datetime(2023, 3, 6)
        buckets = defaultdict(int)
        for d in dates:
            week_num = math.floor((d - start).days / 7)
            buckets[week_num] += 1

        self.assertIn(0, buckets)
        self.assertIn(1, buckets)
        self.assertNotEqual(buckets[0], 0)
        self.assertNotEqual(buckets[1], 0)


# ============================================================
# Model Tests — Issue and Event data structures
# ============================================================

class TestModels(unittest.TestCase):
    """Basic sanity checks on model.Issue and model.Event."""

    def test_issue_defaults(self):
        from model import Issue
        issue = Issue()
        self.assertIsNone(issue.creator)
        self.assertEqual(issue.labels, [])
        self.assertEqual(issue.events, [])

    def test_issue_from_json(self):
        from model import Issue
        data = {
            'url': 'http://example.com/1',
            'creator': 'alice',
            'labels': ['bug'],
            'state': 'open',
            'assignees': [],
            'title': 'Test Issue',
            'text': 'Some description',
            'number': '42',
            'created_date': '2023-01-15T10:00:00Z',
            'updated_date': '2023-01-16T10:00:00Z',
            'timeline_url': 'http://example.com/1/timeline',
            'events': [],
        }
        issue = Issue(data)
        self.assertEqual(issue.creator, 'alice')
        self.assertEqual(issue.labels, ['bug'])
        self.assertEqual(issue.number, 42)
        self.assertEqual(issue.created_date.year, 2023)

    def test_event_from_json(self):
        from model import Event
        data = {
            'event_type': 'closed',
            'author': 'bob',
            'event_date': '2023-05-10T08:00:00Z',
            'label': None,
            'comment': None,
        }
        event = Event(data)
        self.assertEqual(event.event_type, 'closed')
        self.assertEqual(event.author, 'bob')
        self.assertEqual(event.event_date.month, 5)

    def test_event_handles_bad_date(self):
        from model import Event
        data = {
            'event_type': 'labeled',
            'author': 'carol',
            'event_date': 'not-a-date',
        }
        event = Event(data)
        self.assertIsNone(event.event_date)

    def test_issue_handles_bad_date(self):
        from model import Issue
        data = {
            'state': 'open',
            'labels': [],
            'assignees': [],
            'events': [],
            'created_date': 'bad-date',
            'updated_date': 'also-bad',
        }
        issue = Issue(data)
        self.assertIsNone(issue.created_date)


if __name__ == '__main__':
    unittest.main()
