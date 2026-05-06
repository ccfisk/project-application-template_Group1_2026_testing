"""
Unit tests for data_loader.py — targeting 95% coverage.
"""

import importlib
import json
import sys
import unittest
from unittest.mock import MagicMock, mock_open, patch

DATA_PATH = '/fake/path/issues.json'


def build_mocks(data_path=DATA_PATH):
    mock_config = MagicMock()
    mock_config.get_parameter.return_value = data_path
    mock_model = MagicMock()
    mock_model.Issue = MagicMock(side_effect=lambda d: MagicMock(_data=d))
    return {'config': mock_config, 'model': mock_model}


def import_data_loader(mocks):
    sys.modules['config'] = mocks['config']
    sys.modules['model'] = mocks['model']
    sys.modules.pop('data_loader', None)
    return importlib.import_module('data_loader')


def cleanup():
    for key in ('config', 'model', 'data_loader'):
        sys.modules.pop(key, None)


class TestDataLoader(unittest.TestCase):

    def tearDown(self):
        cleanup()

    # --- __init__ ---

    def test_data_path_read_from_config(self):
        mocks = build_mocks()
        mod = import_data_loader(mocks)
        loader = mod.DataLoader()
        mocks['config'].get_parameter.assert_called_with('ENPM611_PROJECT_DATA_PATH')
        self.assertEqual(loader.data_path, DATA_PATH)

    # --- get_issues / singleton ---

    def test_get_issues_returns_loaded_issues(self):
        mocks = build_mocks()
        mod = import_data_loader(mocks)
        loader = mod.DataLoader()
        fake = [MagicMock(), MagicMock()]
        loader._load = MagicMock(return_value=fake)
        self.assertEqual(loader.get_issues(), fake)

    def test_singleton_loads_once_and_caches(self):
        mocks = build_mocks()
        mod = import_data_loader(mocks)
        loader = mod.DataLoader()
        loader._load = MagicMock(return_value=[MagicMock()])
        loader.get_issues()
        loader.get_issues()
        loader._load.assert_called_once()

    def test_get_issues_prints_on_load(self):
        mocks = build_mocks()
        mod = import_data_loader(mocks)
        loader = mod.DataLoader()
        loader._load = MagicMock(return_value=[MagicMock(), MagicMock()])
        with patch('builtins.print') as mock_print:
            loader.get_issues()
        mock_print.assert_called_once()

    # --- _load ---

    def test_load_parses_json_and_wraps_in_issue(self):
        mocks = build_mocks()
        mod = import_data_loader(mocks)
        loader = mod.DataLoader()
        raw = [{'id': 1}, {'id': 2}]
        with patch('builtins.open', mock_open(read_data=json.dumps(raw))):
            result = loader._load()
        self.assertEqual(len(result), 2)
        self.assertEqual(mocks['model'].Issue.call_count, 2)

    def test_load_file_not_found_raises(self):
        mocks = build_mocks()
        mod = import_data_loader(mocks)
        loader = mod.DataLoader()
        with patch('builtins.open', side_effect=FileNotFoundError):
            with self.assertRaises(FileNotFoundError):
                loader._load()


if __name__ == '__main__':
    unittest.main()