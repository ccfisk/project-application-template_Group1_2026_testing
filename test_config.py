import unittest
from unittest.mock import patch, mock_open
import os
import json

# ---------------------------------------------------------------------------
# Important: config uses a module-level singleton _config that persists
# between tests. Each test that touches get_parameter or _init_config must
# reset it first, otherwise earlier tests bleed into later ones.
# ---------------------------------------------------------------------------

import config


def _reset():
    """Reset the config singleton so _init_config() runs fresh each test."""
    config._config = None
    # Clean up any env vars set during the test
    for key in list(os.environ.keys()):
        if key.startswith("TEST_"):
            del os.environ[key]


# ===========================================================================
# convert_to_typed_value  (pure function, no singleton involved)
# ===========================================================================

class TestConvertToTypedValue(unittest.TestCase):

    def test_none_returns_none(self):
        self.assertIsNone(config.convert_to_typed_value(None))

    def test_integer_string_returns_int(self):
        self.assertEqual(config.convert_to_typed_value("42"), 42)

    def test_float_string_returns_float(self):
        self.assertAlmostEqual(config.convert_to_typed_value("3.14"), 3.14)

    def test_bool_true_string_returns_bool(self):
        self.assertIs(config.convert_to_typed_value("true"), True)

    def test_bool_false_string_returns_bool(self):
        self.assertIs(config.convert_to_typed_value("false"), False)

    def test_json_object_string_returns_dict(self):
        result = config.convert_to_typed_value('{"a": 1}')
        self.assertEqual(result, {"a": 1})

    def test_json_array_string_returns_list(self):
        result = config.convert_to_typed_value('[1, 2, 3]')
        self.assertEqual(result, [1, 2, 3])

    def test_plain_string_returns_string(self):
        self.assertEqual(config.convert_to_typed_value("hello"), "hello")

    def test_non_string_value_returned_as_is(self):
        self.assertEqual(config.convert_to_typed_value(99), 99)


# ===========================================================================
# get_parameter — env var priority
# ===========================================================================

class TestGetParameterEnvVar(unittest.TestCase):

    def setUp(self):
        _reset()

    def tearDown(self):
        _reset()

    def test_env_var_takes_priority_over_config_file(self):
        os.environ["TEST_KEY"] = "env_value"
        with patch("config._get_default_path", return_value=None):
            result = config.get_parameter("TEST_KEY")
        self.assertEqual(result, "env_value")

    def test_env_var_integer_is_converted(self):
        os.environ["TEST_INT"] = "7"
        with patch("config._get_default_path", return_value=None):
            result = config.get_parameter("TEST_INT")
        self.assertEqual(result, 7)

    def test_env_var_with_json_prefix_is_parsed(self):
        os.environ["TEST_JSON"] = "json:42"
        with patch("config._get_default_path", return_value=None):
            result = config.get_parameter("TEST_JSON")
        self.assertEqual(result, 42)

    def test_env_var_json_prefix_with_dict(self):
        os.environ["TEST_DICT"] = 'json:{"x": 10}'
        with patch("config._get_default_path", return_value=None):
            result = config.get_parameter("TEST_DICT")
        self.assertEqual(result, {"x": 10})


# ===========================================================================
# get_parameter — config file fallback
# ===========================================================================

class TestGetParameterConfigFile(unittest.TestCase):

    def setUp(self):
        _reset()

    def tearDown(self):
        _reset()

    def _run_with_config(self, cfg_dict, key, default=None):
        """Helper: run get_parameter as if config.json contained cfg_dict."""
        cfg_json = json.dumps(cfg_dict)
        with patch("config._get_default_path", return_value="/fake/config.json"), \
             patch("builtins.open", mock_open(read_data=cfg_json)):
            return config.get_parameter(key, default=default)

    def test_returns_value_from_config_file(self):
        result = self._run_with_config({"MY_KEY": "file_value"}, "MY_KEY")
        self.assertEqual(result, "file_value")

    def test_returns_default_when_key_missing(self):
        result = self._run_with_config({}, "MISSING", default="fallback")
        self.assertEqual(result, "fallback")

    def test_returns_none_when_key_missing_and_no_default(self):
        result = self._run_with_config({}, "MISSING")
        self.assertIsNone(result)

    def test_no_config_file_returns_default(self):
        with patch("config._get_default_path", return_value=None):
            result = config.get_parameter("ANYTHING", default="d")
        self.assertEqual(result, "d")

    def test_no_config_file_returns_none_with_no_default(self):
        with patch("config._get_default_path", return_value=None):
            result = config.get_parameter("ANYTHING")
        self.assertIsNone(result)


# ===========================================================================
# set_parameter
# ===========================================================================

class TestSetParameter(unittest.TestCase):

    def setUp(self):
        _reset()

    def tearDown(self):
        _reset()

    def test_string_value_stored_as_is_in_env(self):
        with patch("config._get_default_path", return_value=None):
            config.set_parameter("TEST_STR", "hello")
        self.assertEqual(os.environ["TEST_STR"], "hello")

    def test_int_value_stored_with_json_prefix(self):
        with patch("config._get_default_path", return_value=None):
            config.set_parameter("TEST_NUM", 5)
        self.assertEqual(os.environ["TEST_NUM"], "json:5")

    def test_dict_value_stored_with_json_prefix(self):
        with patch("config._get_default_path", return_value=None):
            config.set_parameter("TEST_OBJ", {"a": 1})
        self.assertEqual(os.environ["TEST_OBJ"], 'json:{"a": 1}')

    def test_set_then_get_roundtrip_string(self):
        with patch("config._get_default_path", return_value=None):
            config.set_parameter("TEST_RT", "world")
            result = config.get_parameter("TEST_RT")
        self.assertEqual(result, "world")

    def test_set_then_get_roundtrip_int(self):
        with patch("config._get_default_path", return_value=None):
            config.set_parameter("TEST_RT_INT", 99)
            result = config.get_parameter("TEST_RT_INT")
        self.assertEqual(result, 99)


# ===========================================================================
# overwrite_from_args
# ===========================================================================

class TestOverwriteFromArgs(unittest.TestCase):

    def setUp(self):
        _reset()

    def tearDown(self):
        _reset()

    def _make_args(self, **kwargs):
        """Return a simple namespace object like argparse produces."""
        from argparse import Namespace
        return Namespace(**kwargs)

    def test_string_arg_written_to_env(self):
        args = self._make_args(TEST_LABEL="bug")
        with patch("config._get_default_path", return_value=None):
            config.overwrite_from_args(args)
            result = config.get_parameter("TEST_LABEL")
        self.assertEqual(result, "bug")

    def test_none_args_are_skipped(self):
        args = self._make_args(TEST_SKIP=None, TEST_KEEP="yes")
        with patch("config._get_default_path", return_value=None):
            config.overwrite_from_args(args)
        self.assertNotIn("TEST_SKIP", os.environ)
        self.assertIn("TEST_KEEP", os.environ)

    def test_int_arg_roundtrips_correctly(self):
        args = self._make_args(TEST_MONTHS=3)
        with patch("config._get_default_path", return_value=None):
            config.overwrite_from_args(args)
            result = config.get_parameter("TEST_MONTHS")
        self.assertEqual(result, 3)


# ===========================================================================
# _get_default_path
# ===========================================================================

class TestGetDefaultPath(unittest.TestCase):

    def test_returns_none_when_config_json_not_found(self):
        # Patch isfile to always return False so traversal hits the root
        with patch("os.path.isfile", return_value=False):
            result = config._get_default_path()
        self.assertIsNone(result)

    def test_returns_path_when_config_json_found(self):
        with patch("os.path.isfile", return_value=True):
            result = config._get_default_path()
        self.assertIsNotNone(result)
        self.assertTrue(result.endswith("config.json"))


if __name__ == "__main__":
    unittest.main()