import unittest
from unittest.mock import MagicMock, patch
import matplotlib
matplotlib.use("Agg")  # non-interactive backend, safe for tests


def _make_issue(labels):
    """Return a mock Issue with the given labels (list or None)."""
    issue = MagicMock()
    issue.labels = labels
    return issue


def _run(issues):
    """Run analysis_label_types.run() with issues patched, plot suppressed."""
    with patch("config.get_parameter", return_value=6), \
         patch("data_loader.DataLoader.get_issues", return_value=issues), \
         patch("matplotlib.pyplot.show"), \
         patch("matplotlib.pyplot.tight_layout"):
        from feature2_analysis import analysis_label_types
        analysis_label_types().run()


class TestAnalysisLabelTypes(unittest.TestCase):

    # ------------------------------------------------------------------
    # Constructor
    # ------------------------------------------------------------------

    def test_months_stored_from_config(self):
        with patch("config.get_parameter", return_value=3):
            from feature2_analysis import analysis_label_types
            a = analysis_label_types()
        self.assertEqual(a.months, 3)

    # ------------------------------------------------------------------
    # Happy path
    # ------------------------------------------------------------------

    def test_run_completes_with_labeled_issues(self):
        """run() finishes without error when all issues have labels."""
        issues = [
            _make_issue(["bug"]),
            _make_issue(["bug", "help wanted"]),
            _make_issue(["enhancement"]),
        ]
        _run(issues)  # no exception == pass

    def test_run_completes_with_all_unlabeled(self):
        """run() finishes without error when no issues have labels."""
        issues = [_make_issue([]), _make_issue(None), _make_issue([])]
        _run(issues)  # no exception == pass

    def test_run_completes_with_empty_issue_list(self):
        """run() must not raise when there are no issues at all."""
        _run([])

    # ------------------------------------------------------------------
    # Label counting
    # ------------------------------------------------------------------

    def test_single_label_counted_once(self):
        issues = [_make_issue(["bug"])]
        captured = self._capture_barh(issues)
        self.assertIn("bug", captured["labels"])
        idx = captured["labels"].index("bug")
        self.assertEqual(captured["counts"][idx], 1)

    def test_label_appearing_multiple_times_is_summed(self):
        issues = [_make_issue(["bug"]), _make_issue(["bug"]), _make_issue(["bug"])]
        captured = self._capture_barh(issues)
        idx = captured["labels"].index("bug")
        self.assertEqual(captured["counts"][idx], 3)

    def test_multiple_labels_on_one_issue_each_counted(self):
        issues = [_make_issue(["bug", "help wanted"])]
        captured = self._capture_barh(issues)
        self.assertIn("bug", captured["labels"])
        self.assertIn("help wanted", captured["labels"])

    # ------------------------------------------------------------------
    # Unlabeled bucket
    # ------------------------------------------------------------------

    def test_unlabeled_always_present(self):
        """'unlabeled' must appear even when every issue has labels."""
        issues = [_make_issue(["bug"]), _make_issue(["enhancement"])]
        captured = self._capture_barh(issues)
        self.assertIn("unlabeled", captured["labels"])

    def test_unlabeled_count_correct_for_empty_label_list(self):
        issues = [_make_issue([]), _make_issue([]), _make_issue(["bug"])]
        captured = self._capture_barh(issues)
        idx = captured["labels"].index("unlabeled")
        self.assertEqual(captured["counts"][idx], 2)

    def test_unlabeled_count_correct_for_none_labels(self):
        issues = [_make_issue(None), _make_issue(None)]
        captured = self._capture_barh(issues)
        idx = captured["labels"].index("unlabeled")
        self.assertEqual(captured["counts"][idx], 2)

    def test_unlabeled_count_zero_when_all_issues_labeled(self):
        issues = [_make_issue(["bug"]), _make_issue(["fix"])]
        captured = self._capture_barh(issues)
        idx = captured["labels"].index("unlabeled")
        self.assertEqual(captured["counts"][idx], 0)

    # ------------------------------------------------------------------
    # Top-15 cap
    # ------------------------------------------------------------------

    def test_at_most_16_bars_shown(self):
        """At most 15 labels + 1 unlabeled bucket = 16 bars total."""
        # Create 20 distinct labels
        issues = [_make_issue([f"label_{i}"]) for i in range(20)]
        captured = self._capture_barh(issues)
        # 15 top labels + "unlabeled"
        self.assertLessEqual(len(captured["labels"]), 16)

    def test_top_label_by_frequency_is_included(self):
        """The most frequent label must survive the top-15 cut."""
        issues = [_make_issue(["top"])] * 10 + [_make_issue([f"rare_{i}"]) for i in range(20)]
        captured = self._capture_barh(issues)
        self.assertIn("top", captured["labels"])

    def test_rare_labels_excluded_beyond_top_15(self):
        """Labels ranked 16th or lower must be dropped."""
        # 15 common labels (count=2 each) + 1 rare label (count=1)
        common = [_make_issue([f"label_{i}"]) for i in range(15)] * 2
        rare = [_make_issue(["rare_one"])]
        captured = self._capture_barh(common + rare)
        self.assertNotIn("rare_one", captured["labels"])

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------

    def _capture_barh(self, issues):
        """Run analysis and capture the labels/counts passed to plt.barh."""
        captured = {}

        def fake_barh(labels, counts, *args, **kwargs):
            captured["labels"] = list(labels)
            captured["counts"] = list(counts)

        with patch("config.get_parameter", return_value=6), \
             patch("data_loader.DataLoader.get_issues", return_value=issues), \
             patch("matplotlib.pyplot.barh", side_effect=fake_barh), \
             patch("matplotlib.pyplot.show"), \
             patch("matplotlib.pyplot.tight_layout"), \
             patch("matplotlib.pyplot.gca"):
            from feature2_analysis import analysis_label_types
            analysis_label_types().run()

        return captured


if __name__ == "__main__":
    unittest.main()