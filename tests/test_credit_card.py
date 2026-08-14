#!/usr/bin/env python3
"""Unit tests for CREDIT_CARD detection & Luhn validation."""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from pii_redactor import PIIDetector, luhn_check

class TestCreditCardDetection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.detector = PIIDetector(method="hybrid", domain_profile=None)

    def test_luhn_algorithm(self):
        self.assertTrue(luhn_check("4532015112830366"))
        self.assertTrue(luhn_check("4532-0151-1283-0366"))
        self.assertFalse(luhn_check("1234567812345678"))
        self.assertFalse(luhn_check("0000000000000000"))

    def test_positive_credit_cards(self):
        positive_cards = [
            ("Visa card 4532-0151-1283-0366 processed.", "4532-0151-1283-0366"),
            ("Primary card 4532015112830366 charged.", "4532015112830366")
        ]
        for text, expected in positive_cards:
            entities = self.detector.detect_pii(text)
            detected = [e.text for e in entities if e.category == "CREDIT_CARD"]
            self.assertIn(expected, detected, f"Failed to detect valid credit card '{expected}' in '{text}'")

    def test_negative_invalid_luhn_cards(self):
        invalid_cards = [
            "Random 16 digits 1234567812345678.",
            "All zero digits 0000000000000000.",
            "Fiscal year range 2024-2025.",
            "Order ID 123456789012."
        ]
        for text in invalid_cards:
            entities = self.detector.detect_pii(text)
            detected_cards = [e.text for e in entities if e.category == "CREDIT_CARD"]
            self.assertEqual(len(detected_cards), 0, f"False positive credit card in '{text}': {detected_cards}")

if __name__ == "__main__":
    unittest.main()
