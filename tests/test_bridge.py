import unittest

from lessweb.bridge import cast_http_method


class TestCastHttpMethod(unittest.TestCase):
    def test_valid_http_method(self):
        method = 'GET'
        result = cast_http_method(method)
        self.assertEqual(result, 'GET')

    def test_invalid_http_method(self):
        method = 'INVALID'
        with self.assertRaises(AssertionError):
            cast_http_method(method)


if __name__ == '__main__':
    unittest.main()
