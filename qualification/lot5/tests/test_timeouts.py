import unittest

from qualification.lot5.timeouts import parse_timeout


class ParseTimeoutTests(unittest.TestCase):
    def test_valid_value(self):
        self.assertEqual(parse_timeout(30), 30)

    def test_inclusive_bounds(self):
        self.assertEqual(parse_timeout(1), 1)
        self.assertEqual(parse_timeout(300), 300)

    def test_out_of_range(self):
        for value in (0, -1, 301):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_timeout(value)

    def test_invalid_type(self):
        for value in (None, "5", 1.5, [], b"5"):
            with self.subTest(value=value), self.assertRaises(TypeError):
                parse_timeout(value)

    def test_bool_rejected(self):
        for value in (True, False):
            with self.subTest(value=value), self.assertRaises(TypeError):
                parse_timeout(value)

    def test_int_subclass_rejected(self):
        class MyInt(int):
            pass

        with self.assertRaises(TypeError):
            parse_timeout(MyInt(5))
