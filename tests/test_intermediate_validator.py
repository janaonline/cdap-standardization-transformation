import unittest

import pandas as pd

from validators.intermediate_validator import REQUIRED_INTERMEDIATE_COLUMNS, validate_intermediate_dataframe


class TestIntermediateValidator(unittest.TestCase):
    def test_intermediate_validator_accepts_zero_values(self):
        row = {col: "x" for col in REQUIRED_INTERMEDIATE_COLUMNS}
        row.update({"Rural %": 0, "Urban %": "", "Total %": "", "Year": 2023, "Unit": "Percentage"})
        result = validate_intermediate_dataframe(pd.DataFrame([row]))

        self.assertTrue(result["success"])
        self.assertEqual(result["rows"], 1)
