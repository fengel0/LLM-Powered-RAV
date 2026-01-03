import math
from core.logger import init_logging
import unittest

# Adjust this import to match your file/module name (e.g., `import mymodule as m`)
from graph_view.ratings.calc_ratings import (
    calc_miss_match,
    calc_f1,
    calc_recall,
    calc_precision,
    calc_complettnes,
    calc_complettnes_strict,
    prf_counts,
    bootstrap_mean_ci,
    wilson_interval,
    z_mean_interval,
)

init_logging("debug")


class TestCalcMissMatch(unittest.TestCase):
    def test_basic_and_behavior(self):
        self.assertEqual(
            calc_miss_match(
                answer_facts=[True, True, False, False],
                context_facts=[True, False, True, False],
            ),
            [True, False, False, False],
        )

    def test_all_false(self):
        self.assertEqual(
            calc_miss_match(answer_facts=[False, False], context_facts=[True, True]),
            [False, False],
        )

    def test_all_true(self):
        self.assertEqual(
            calc_miss_match(
                answer_facts=[True, True, True], context_facts=[True, True, True]
            ),
            [True, True, True],
        )

    def test_length_mismatch_assertion(self):
        with self.assertRaises(AssertionError):
            calc_miss_match([True], [True, False])


class TestPRFCounts(unittest.TestCase):
    def test_prf_counts_typical(self):
        # gold = [True, True, True, True]
        pred = [True, False, True, False]
        tp, fp, fn = prf_counts(pred=pred, number_of_facts=5, id="q1")
        # tp is number of True in pred (since gold is all True)
        self.assertEqual(tp, 2)
        # fp = number_of_facts - tp
        self.assertEqual(fp, 3)
        # fn = number of False in pred (since gold is all True)
        self.assertEqual(fn, 2)

    def test_prf_counts_fp_capped_and_logger_used(self):
        # When number_of_facts < tp, fp would be negative and should be set to 0.
        # The function references `logger` only when fp < 0; provide a dummy to avoid NameError.

        pred = [True, True, True]  # tp = 3
        tp, fp, fn = prf_counts(pred=pred, number_of_facts=1, id="q2")
        self.assertEqual(tp, 3)
        self.assertEqual(fp, 0)  # capped at 0
        self.assertEqual(fn, 0)


class TestPrecisionRecallF1(unittest.TestCase):
    def test_recall(self):
        self.assertEqual(calc_recall(tp=0, fn=0), 0.0)  # defined 0/0 -> 0
        self.assertAlmostEqual(calc_recall(tp=3, fn=1), 3 / 4)

    def test_precision(self):
        self.assertEqual(calc_precision(tp=0, fp=0), 0.0)  # defined 0/0 -> 0
        self.assertAlmostEqual(calc_precision(tp=3, fp=1), 3 / 4)

    def test_f1(self):
        # With precision=0 and recall=0, F1 defined as 0
        self.assertEqual(calc_f1(0.0, 0.0), 0.0)
        # Symmetric harmonic mean
        self.assertAlmostEqual(calc_f1(1.0, 1.0), 1.0)
        self.assertAlmostEqual(calc_f1(0.5, 1.0), 2 * (0.5 * 1.0) / (1.5))


class TestCompleteness(unittest.TestCase):
    def test_complettnes_empty(self):
        self.assertEqual(calc_complettnes([]), 0.0)

    def test_complettnes_mixed(self):
        self.assertAlmostEqual(calc_complettnes([True, False, True, False]), 0.5)

    def test_complettnes_all_true(self):
        self.assertAlmostEqual(calc_complettnes([True, True, True]), 1.0)

    def test_complettnes_strict(self):
        self.assertEqual(calc_complettnes_strict([True, True]), 1.0)
        self.assertEqual(calc_complettnes_strict([True, False]), 0.0)
        self.assertEqual(calc_complettnes_strict([]), 0.0)  # underlying mean is 0.0


class TestZMeanInterval(unittest.TestCase):
    def test_empty_returns_nan_tuple(self):
        lo, hi = z_mean_interval([])
        self.assertTrue(math.isnan(lo))
        self.assertTrue(math.isnan(hi))

    def test_all_zeros(self):
        lo, hi = z_mean_interval([0.0, 0.0, 0.0, 0.0])
        self.assertGreaterEqual(lo, 0.0)
        self.assertLessEqual(hi, 1.0)
        # mean=0 so interval should start at 0
        self.assertAlmostEqual(lo, 0.0, places=7)

    def test_all_ones(self):
        lo, hi = z_mean_interval([1.0, 1.0, 1.0, 1.0])
        self.assertGreaterEqual(lo, 0.0)
        self.assertLessEqual(hi, 1.0)
        # mean=1 so interval should end at 1
        self.assertAlmostEqual(hi, 1.0, places=7)

    def test_mixed_contains_mean(self):
        vals = [0, 1, 1, 0, 1, 1, 0, 1]
        lo, hi = z_mean_interval(vals)
        mean = sum(vals) / len(vals)
        self.assertLessEqual(lo, mean)
        self.assertGreaterEqual(hi, mean)


class TestWilsonInterval(unittest.TestCase):
    def test_empty_returns_nan_tuple(self):
        lo, hi = wilson_interval([])
        self.assertTrue(math.isnan(lo))
        self.assertTrue(math.isnan(hi))

    def test_bounds_and_monotonic(self):
        vals = [0, 1, 1, 0, 1]
        lo, hi = wilson_interval(vals)
        self.assertGreaterEqual(lo, 0.0)
        self.assertLessEqual(hi, 1.0)
        self.assertLessEqual(lo, hi)

    def test_degenerate_all_zero_or_one(self):
        lo0, hi0 = wilson_interval([0, 0, 0, 0, 0])
        self.assertGreaterEqual(lo0, 0.0)
        self.assertLessEqual(hi0, 1.0)
        lo1, hi1 = wilson_interval([1, 1, 1, 1, 1])
        self.assertGreaterEqual(lo1, 0.0)
        self.assertLessEqual(hi1, 1.0)
        self.assertLessEqual(lo0, hi0)
        self.assertLessEqual(lo1, hi1)


class TestBootstrapMeanCI(unittest.TestCase):
    def test_empty_returns_nan_tuple(self):
        lo, hi = bootstrap_mean_ci([])
        self.assertTrue(math.isnan(lo))
        self.assertTrue(math.isnan(hi))

    def test_contains_sample_mean_and_bounds(self):
        vals = [0, 1, 1, 0, 1, 0, 1, 1]
        lo, hi = bootstrap_mean_ci(vals, alpha=0.1, B=5000, seed=42)
        mean = sum(vals) / len(vals)
        self.assertLessEqual(lo, mean)
        self.assertGreaterEqual(hi, mean)
        self.assertGreaterEqual(lo, 0.0)
        self.assertLessEqual(hi, 1.0)
        self.assertLessEqual(lo, hi)

    def test_deterministic_with_seed(self):
        vals = [0, 0, 1, 1, 1, 0, 1]
        lo1, hi1 = bootstrap_mean_ci(vals, alpha=0.05, B=4000, seed=123)
        lo2, hi2 = bootstrap_mean_ci(vals, alpha=0.05, B=4000, seed=123)
        self.assertAlmostEqual(lo1, lo2, places=10)
        self.assertAlmostEqual(hi1, hi2, places=10)


if __name__ == "__main__":
    unittest.main()
