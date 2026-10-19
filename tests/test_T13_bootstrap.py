import json, os, unittest
from common import *
import bootstrap_ci as BC


class T13(unittest.TestCase):
    def test_shipped_receipt_is_reproduced_and_documented(self):
        self.assertEqual(BC.main(["--root", W, "--check"]), 0)

    def test_intervals_contain_the_point_estimate_and_are_ordered(self):
        r = json.load(open(os.path.join(W, BC.SHIPPED)))
        for s in r["systems"].values():
            for c in s.values():
                self.assertLessEqual(c["lo"], c["point"] + 1e-9)
                self.assertLessEqual(c["point"], c["hi"] + 1e-9)

    def test_exact_scaling(self):
        from fractions import Fraction
        vals, den = BC.scaled([Fraction(1, 3), Fraction(1, 4), Fraction(0)])
        self.assertEqual((vals, den), ([4, 3, 0], 12))


if __name__ == "__main__":
    unittest.main()
