#!/usr/bin/env python3
"""
===============================================================================
Regression Protection Unit Tests
===============================================================================
Description:
    Tests explicit regression targets discovered during earlier evaluations:
    - Fiscal year ranges: "2022-2023", "2023-2024", "2024-2025"
    - Capital market stop words: "Reference Rate", "Selling Shareholder", "Bid Amount",
      "Mutual Funds", "Key Managerial Personnel", "Key Management Personnel",
      "Capital Reserve", "Capital Employed", "March 31, 2025"
===============================================================================
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from pii_redactor import PIIDetector

class TestRegressionProtection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.detector = PIIDetector(method="hybrid", domain_profile=None)

    def test_regression_year_ranges_not_phones(self):
        regression_years = [
            "Financial results for 2022-2023.",
            "Comparison with 2023-2024.",
            "Fiscal 2024-2025 targets.",
            "FY 2024-25 report.",
            "Document ID 000013004."
        ]
        for text in regression_years:
            entities = self.detector.detect_pii(text)
            detected_phones = [e.text for e in entities if e.category == "PHONE_NUMBER"]
            self.assertEqual(
                len(detected_phones), 0,
                f"REGRESSION DETECTED: Year range in '{text}' falsely flagged as phone: {detected_phones}"
            )

    def test_regression_financial_terms_not_companies(self):
        regression_terms = [
            "Review of central bank Reference Rate.",
            "Offer for Sale by Selling Shareholder.",
            "Minimum Bid Amount allocation.",
            "Investment in Mutual Funds portfolios.",
            "Remuneration of Key Managerial Personnel.",
            "Compensation of Key Management Personnel.",
            "Calculation of Capital Employed.",
            "Transfer to Capital Reserve.",
            "Financial statements as of March 31, 2025."
        ]
        for text in regression_terms:
            entities = self.detector.detect_pii(text)
            detected_comps = [e.text for e in entities if e.category == "COMPANY_NAME"]
            detected_dobs = [e.text for e in entities if e.category == "DATE_OF_BIRTH"]
            
            self.assertEqual(
                len(detected_comps), 0,
                f"REGRESSION DETECTED: Financial term in '{text}' falsely flagged as company: {detected_comps}"
            )
            self.assertEqual(
                len(detected_dobs), 0,
                f"REGRESSION DETECTED: Financial date in '{text}' falsely flagged as DOB: {detected_dobs}"
            )

if __name__ == "__main__":
    unittest.main()
