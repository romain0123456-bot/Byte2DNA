import unittest
from qualification.lot2.app import add, multiply


class ApplicationContract(unittest.TestCase):
    def test_add_handles_positive_negative_and_zero(self):
        for a, b in ((2, 3), (-4, 3), (0, 7), (0, 0)):
            with self.subTest(a=a, b=b):
                self.assertEqual(add(a, b), a + b)

    def test_multiply_handles_sign_and_zero(self):
        for a, b in ((2, 3), (-4, 3), (0, 7), (-4, -3)):
            with self.subTest(a=a, b=b):
                self.assertEqual(multiply(a, b), a * b)
