import tempfile
import unittest
from pathlib import Path

import pandas as pd

from converters.format_detector import detect_source_format


class TestFormatDetector(unittest.TestCase):
    def test_detects_plfs_industry_text(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "source.xlsx"
            df = pd.DataFrame([
                ["Table 1"],
                ["Percentage distribution of usually working persons by industry of work"],
                ["Rural", "Urban", "Male", "Female"],
            ])
            df.to_excel(path, index=False, header=False)

            result = detect_source_format(path)

            self.assertEqual(result["detected_format"], "plfs_industry")
            self.assertGreaterEqual(result["confidence"], 0.7)
