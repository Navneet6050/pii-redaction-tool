#!/usr/bin/env python3
"""Unit tests for DATE_OF_BIRTH detection (Contextual DOB vs. Financial Dates)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from pii_redactor import PIIDetector

class TestDOBDetection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.detector = PIIDetector(method="hybrid", domain_profile=None)

    def test_positive_dob(self):
        positive_dobs = [
            "Executive Date of Birth: 15/08/1982.",
            "Promoter DOB: 12-01-1990.",
            "Director Born on: January 15, 1985.",
            "Birth Date: 20 July 1978."
        ]
        for text in positive_dobs:
            entities = self.detector.detect_pii(text)
            detected = [e.text for e in entities if e.category == "DATE_OF_BIRTH"]
            self.assertTrue(len(detected) >= 1, f"Failed to detect DOB in '{text}'")

    def test_negative_financial_reporting_dates(self):
        financial_dates = [
            "Financial results for the year ended March 31, 2025.",
            "Restated financial information as of June 30, 2024.",
            "Audited balance sheet dated December 31, 2023.",
            "Board meeting conducted on October 15, 2024.",
            "Fiscal FY 2024-25 reporting period."
        ]
        for text in financial_dates:
            entities = self.detector.detect_pii(text)
            detected_dobs = [e.text for e in entities if e.category == "DATE_OF_BIRTH"]
            self.assertEqual(len(detected_dobs), 0, f"False positive DOB detected in '{text}': {detected_dobs}")

if __name__ == "__main__":
    unittest.main()
