import sys
import unittest
from unittest.mock import patch, MagicMock


class TestRunFeature1(unittest.TestCase):

    def test_feature1_various_months(self):

        months_values = [-1, 0, 1, 6, 12, 16, 2000]

        for months_value in months_values:

            with self.subTest(months=months_value):

                test_args = [
                    "run.py",
                    "--feature", "1",
                    "-m", str(months_value)
                ]

                if "run" in sys.modules:
                    del sys.modules["run"]

                captured = {}

                def capture_args(args):
                    captured["feature"] = args.feature
                    captured["months"] = args.months

                with patch.object(sys, "argv", test_args):
                    with patch("config.overwrite_from_args", side_effect=capture_args):
                        with patch(
                            "feature1_analysis.analysis_time_commit_hist"
                        ) as mock_analysis_class:

                            mock_instance = MagicMock()
                            mock_analysis_class.return_value = mock_instance

                            import run  # ONLY import once

                            self.assertEqual(captured["feature"], 1)
                            self.assertEqual(captured["months"], months_value)

                            mock_analysis_class.assert_called_once()
                            mock_instance.run.assert_called_once()


if __name__ == "__main__":
    unittest.main()