"""Timeout settings change transport waiting, not grading or agent decisions."""
import os
import unittest
from unittest.mock import patch

from providers import post_json


class ProviderTimeoutTests(unittest.TestCase):
    @patch('providers.urllib.request.urlopen')
    def test_default_and_override(self, urlopen):
        urlopen.return_value.__enter__.return_value.read.return_value = b'{}'
        with patch.dict(os.environ, {}, clear=True):
            post_json('https://example.invalid', {}, {})
            self.assertEqual(urlopen.call_args.kwargs['timeout'], 60)
        with patch.dict(os.environ, {'PROVIDER_TIMEOUT_SECONDS': '180'}):
            post_json('https://example.invalid', {}, {})
            self.assertEqual(urlopen.call_args.kwargs['timeout'], 180)

    @patch('providers.urllib.request.urlopen')
    def test_invalid_timeout_does_not_call_network(self, urlopen):
        for value in ['0', '301', 'invalid']:
            with self.subTest(value=value), patch.dict(os.environ, {'PROVIDER_TIMEOUT_SECONDS': value}):
                with self.assertRaises(ValueError):
                    post_json('https://example.invalid', {}, {})
        urlopen.assert_not_called()
