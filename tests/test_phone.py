#!/usr/bin/env python3
"""Unit tests for PHONE_NUMBER detection (Positive, Negative, Edge Cases)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from pii_redactor import PIIDetector

class TestPhoneDetection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.detector = PIIDetector(method="hybrid", domain_profile=None)

    def test_positive_phone_numbers(self):
        positive_phones = [
            ("Call +91 9876543210 for help.", "+91 9876543210"),
            ("Mobile number +91-9876543210 registered.", "+91-9876543210"),
            ("Direct line 9876543210 active.", "9876543210"),
            ("Pune office landline 020-45053237.", "020-45053237"),
            ("Mumbai office landline +91 22 6807 7100.", "+91 22 6807 7100"),
            ("US Helpline: +1 212 555 0199.", "+1 212 555 0199"),
            ("STD format (020) 25501234.", "(020) 25501234"),
            ("Contact: 022-26598100.", "022-26598100"),
            ("Mobile +91 9123456789.", "+91 9123456789"),
            ("Phone 080-41123456.", "080-41123456")
        ]
        for text, expected in positive_phones:
            entities = self.detector.detect_pii(text)
            detected = [e.text for e in entities if e.category == "PHONE_NUMBER"]
            self.assertTrue(
                len(detected) >= 1,
                f"Failed to detect phone '{expected}' in '{text}'"
            )

    def test_negative_phone_numbers(self):
        negative_cases = [
            "Fiscal Year 2024-2025 financial reports.",
            "Comparison of Fiscal 2023-2024 results.",
            "Document ID number 000013004.",
            "Serial number 00000063.",
            "Year range 2022-2023.",
            "Section 135(5) of Companies Act.",
            "ISO standard 9001:2015.",
            "Page 123 of 456.",
            "Code 100000000000.",
            "Date 2025/03/31."
        ]
        for text in negative_cases:
            entities = self.detector.detect_pii(text)
            detected_phones = [e.text for e in entities if e.category == "PHONE_NUMBER"]
            self.assertEqual(
                len(detected_phones), 0,
                f"False positive phone detected in '{text}': {detected_phones}"
            )

if __name__ == "__main__":
    unittest.main()
