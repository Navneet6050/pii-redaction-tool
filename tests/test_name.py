#!/usr/bin/env python3
"""Unit tests for FULL_NAME detection (Indian, Western, Middle, Hyphenated)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from pii_redactor import PIIDetector, DomainProfile

class TestNameDetection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.detector_hybrid = PIIDetector(method="hybrid", domain_profile=DomainProfile.get_rhp_default_profile())
        cls.detector_standalone = PIIDetector(method="hybrid", domain_profile=None)

    def test_indian_and_western_names(self):
        positive_names = [
            ("Promoter Kushal Subbayya Hegde filed document.", "Kushal Subbayya Hegde"),
            ("Director Pushpa Kushal Hegde attended meeting.", "Pushpa Kushal Hegde"),
            ("Secretary Sarthak Malvadkar confirmed minutes.", "Sarthak Malvadkar"),
            ("Chairman Jonathan Miller presented report.", "Jonathan Miller"),
            ("Vice President Ashley Williams approved budget.", "Ashley Williams"),
            ("CFO Robert Chen signed statements.", "Robert Chen"),
            ("Officer Katyayani Balasubramanian authorized release.", "Katyayani Balasubramanian"),
            ("Auditor Gopalakrishnan V reviewed books.", "Gopalakrishnan V"),
            ("Consultant Anne-Marie Smith verified accounts.", "Anne-Marie Smith"),
            ("Manager Rajesh Kushal Hegde led discussion.", "Rajesh Kushal Hegde")
        ]
        for text, expected in positive_names:
            entities = self.detector_hybrid.detect_pii(text)
            detected = [e.text for e in entities if e.category == "FULL_NAME"]
            self.assertTrue(
                any(expected in d or d in expected for d in detected),
                f"Failed to detect name '{expected}' in '{text}'"
            )

    def test_negative_capitalized_phrases(self):
        negative_phrases = [
            "The Board of Directors approved the resolution.",
            "Report by the Audit Committee.",
            "Review by Nomination and Remuneration Committee.",
            "Submitted to Stakeholders Relationship Committee.",
            "Approved by Risk Management Committee.",
            "According to the Companies Act.",
            "As stated in Table of Contents.",
            "In compliance with SEBI Regulations.",
            "Details in Restated Financial Information.",
            "Outlined in Risk Factors."
        ]
        for text in negative_phrases:
            entities = self.detector_standalone.detect_pii(text)
            detected_names = [e.text for e in entities if e.category == "FULL_NAME"]
            self.assertEqual(
                len(detected_names), 0,
                f"False positive name detected in '{text}': {detected_names}"
            )

if __name__ == "__main__":
    unittest.main()
