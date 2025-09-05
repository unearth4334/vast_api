import unittest
import sys
import os

# Add the parent directory to the path so we can import from app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.utils.match_filter import match_filter

class TestMatchFilter(unittest.TestCase):

    def test_suffix_match(self):
        self.assertTrue(match_filter("Quebec, CA", "*, CA", column="geolocation"))
        self.assertTrue(match_filter("British Columbia, CA", "*, CA", column="geolocation"))
        self.assertFalse(match_filter("Trinidad and Tobago, TT", "*, CA", column="geolocation"))

    def test_exact_match(self):
        self.assertTrue(match_filter("France, FR", "France, FR", column="geolocation"))
        self.assertFalse(match_filter("France, FR", "France, CA", column="geolocation"))


    def test_numeric_filters(self):
        self.assertTrue(match_filter(24576, ">= 24576", column="gpu_ram"))
        self.assertFalse(match_filter(24000, ">= 24576", column="gpu_ram"))
        self.assertTrue(match_filter(5.1, "> 5", column="score"))
        self.assertFalse(match_filter(1.0, "== 2", column="score"))

if __name__ == "__main__":
    unittest.main()
