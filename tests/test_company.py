#!/usr/bin/env python3
"""Unit tests for COMPANY_NAME detection & financial stopword protection."""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from pii_redactor import PIIDetector, DomainProfile

class TestCompanyDetection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.detector_hybrid = PIIDetector(method="hybrid", domain_profile=DomainProfile.get_rhp_default_profile())
        cls.detector_standalone = PIIDetector(method="hybrid", domain_profile=None)

    def test_positive_companies(self):
        positive_companies = [
            ("Filing by KSH International Limited today.", "KSH International Limited"),
            ("Lead manager ICICI Securities Limited appointed.", "ICICI Securities Limited"),
            ("Co-manager Nuvama Wealth Management Limited.", "Nuvama Wealth Management Limited"),
            ("Banker MUFG Bank Ltd signed credit.", "MUFG Bank Ltd"),
            ("Lender Federal Bank Limited approved loan.", "Federal Bank Limited"),
            ("Accounts audited by Kirtane & Pandit LLP.", "Kirtane & Pandit LLP"),
            ("Legal counsel Trilegal advised board.", "Trilegal"),
            ("State Bank of India sanctioned facility.", "State Bank of India"),
            ("HDFC Bank Limited issued guarantee.", "HDFC Bank Limited"),
            ("Registrar Link Intime India Private Limited.", "Link Intime India Private Limited")
        ]
        for text, expected in positive_companies:
            entities = self.detector_hybrid.detect_pii(text)
            detected = [e.text for e in entities if e.category == "COMPANY_NAME"]
            self.assertTrue(
                any(expected in d or d in expected for d in detected),
                f"Failed to detect company '{expected}' in '{text}'"
            )

    def test_negative_financial_phrases(self):
        negative_phrases = [
            "Review of Reference Rate for central bank.",
            "Offer for Sale by Selling Shareholder.",
            "Minimum Bid Amount required from bidders.",
            "Investment in Mutual Funds portfolios.",
            "Remuneration of Key Managerial Personnel.",
            "Statement of Capital Employed.",
            "Calculation of Net Asset Value per share.",
            "Transfer to Capital Reserve account.",
            "Verification of Cash and Bank Balances.",
            "Summary of Restated Financial Information."
        ]
        for text in negative_phrases:
            entities = self.detector_standalone.detect_pii(text)
            detected_comps = [e.text for e in entities if e.category == "COMPANY_NAME"]
            self.assertEqual(
                len(detected_comps), 0,
                f"False positive company detected in '{text}': {detected_comps}"
            )

if __name__ == "__main__":
    unittest.main()
