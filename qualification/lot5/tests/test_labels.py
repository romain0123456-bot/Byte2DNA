import unittest

from qualification.lot5.labels import normalize_label


class NormalizeLabelTests(unittest.TestCase):
    def test_repeated_whitespace(self):
        self.assertEqual(normalize_label("  alpha \t \n beta  "), "alpha-beta")

    def test_mixed_case(self):
        self.assertEqual(normalize_label("MiXeD CaSe"), "mixed-case")

    def test_empty(self):
        self.assertEqual(normalize_label(""), "")
        self.assertEqual(normalize_label(" \t\n"), "")

    def test_invalid_type(self):
        for value in (None, 12, True, [], b"label"):
            with self.subTest(value=value), self.assertRaises(TypeError):
                normalize_label(value)

    def test_unicode_whitespace(self):
        self.assertEqual(normalize_label("Alpha\u2003Beta\u00a0Gamma"), "alpha-beta-gamma")

    def test_controlled_ci_failure(self):
        # Intentional first-HEAD qualification failure; retain until native review.
        self.assertEqual(normalize_label("Controlled CI"), "deliberately-wrong-oracle")
