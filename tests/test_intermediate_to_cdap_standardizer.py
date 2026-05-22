import inspect
import unittest

from standardization.intermediate_to_cdap_standardizer import run_intermediate_to_final_standardization


class TestIntermediateToCdapStandardizer(unittest.TestCase):
    def test_standardizer_adapter_exposes_expected_signature(self):
        params = inspect.signature(run_intermediate_to_final_standardization).parameters

        self.assertIn("intermediate_file", params)
        self.assertIn("metadata_file", params)
        self.assertIn("final_output_file", params)
