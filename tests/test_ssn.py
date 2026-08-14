#!/usr/bin/env python3
"""Unit tests for SSN detection."""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from pii_redactor import PIIDetector

class TestSSNDetection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.detector = PIIDetector(method="hybrid", domain_profile=None)

    def test_positive_ssn(self):
        positive_ssns = [
            ("Employee SSN: 123-45-6789.", "123-45-6789"),
            ("Tax record 987-65-4321.", "987-65-4321"),
            ("US Social Security Number 456-78-9012.", "456-78-9012")
        ]
        for text, expected in positive_ssns:
            entities = self.detector.detect_pii(text)
            detected = [e.text for e in entities if e.category == "SSN"]
            self.assertIn(expected, detected, f"Failed to detect SSN '{expected}' in '{text}'")

    def test_negative_ssn(self):
        negative_ssns = [
            "Year range 2024-2025.",
            "Phone number +91 9876543210.",
            "Arbitrary 9 digits 123456789 without hyphens.",
            "PAN Number ABCDE1234F."
        ]
        for text in negative_ssns:
            entities = self.detector.detect_pii(text)
            detected_ssns = [e.text for e in entities if e.category == "SSN"]
            self.assertEqual(len(detected_ssns), 0, f"False positive SSN in '{text}': {detected_ssns}")

if __name__ == "__main__":
    unittest.main()
