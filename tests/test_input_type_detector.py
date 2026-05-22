import tempfile
import unittest
from pathlib import Path

import pandas as pd

from validators.input_type_detector import INTERMEDIATE_FORMAT, detect_input_type
from validators.intermediate_validator import REQUIRED_INTERMEDIATE_COLUMNS


class TestInputTypeDetector(unittest.TestCase):
    def test_detects_intermediate_format_with_schema_aliases(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "intermediate.xlsx"
            df = pd.DataFrame([{col: "x" for col in REQUIRED_INTERMEDIATE_COLUMNS}])
            df = df.rename(columns={"Rural %": "rural_pct", "Urban %": "Urban Percentage"})
            df.to_excel(path, index=False)

            result = detect_input_type(path)

            self.assertEqual(result["input_type"], INTERMEDIATE_FORMAT)
