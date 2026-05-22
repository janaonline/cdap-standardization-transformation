import unittest

from utils.year_utils import extract_years_from_text, normalize_year_token


class TestYearUtils(unittest.TestCase):
    def test_year_labels_are_normalized(self):
        self.assertEqual(normalize_year_token("Financial Year 2019"), "2019")
        self.assertEqual(normalize_year_token("Till March '22"), "2022")
        self.assertEqual(normalize_year_token("2017-18"), "2018")

    def test_nic_classification_year_is_ignored(self):
        self.assertEqual(extract_years_from_text("National Industrial Classification NIC 2008"), [])
