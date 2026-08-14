#!/usr/bin/env python3
"""Unit tests for EMAIL_ADDRESS detection (Positive, Negative, Edge Cases)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from pii_redactor import PIIDetector

class TestEmailDetection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.detector = PIIDetector(method="hybrid", domain_profile=None)

    def test_positive_emails(self):
        sample_emails = [
            ("Contact john.doe@example.com for details.", "john.doe@example.com"),
            ("Alias test user+alias@domain.co.uk registered.", "user+alias@domain.co.uk"),
            ("Subdomain address admin@sub.service.corp.org active.", "admin@sub.service.corp.org"),
            ("Uppercase EMAIL USER.NAME@COMPANY.COM valid.", "USER.NAME@COMPANY.COM"),
            ("Hyphenated domain info@my-company.io operational.", "info@my-company.io"),
            ("Numeric email 12345@domain.net.", "12345@domain.net"),
            ("Dot alias email jane.doe.work@enterprise.com.", "jane.doe.work@enterprise.com"),
            ("Customer care customercare@icicisecurities.com.", "customercare@icicisecurities.com"),
            ("Compliance cs.connect@kshinternational.com.", "cs.connect@kshinternational.com"),
            ("IPO desk ksh.ipo@nuvama.com.", "ksh.ipo@nuvama.com")
        ]
        for text, expected_email in sample_emails:
            entities = self.detector.detect_pii(text)
            detected = [e.text for e in entities if e.category == "EMAIL_ADDRESS"]
            self.assertTrue(
                any(expected_email.lower() == d.lower() for d in detected),
                f"Failed to detect positive email '{expected_email}' in '{text}'"
            )

    def test_negative_emails(self):
        non_emails = [
            "This is user@domain without tld.",
            "Double at symbol user@@domain.com invalid.",
            "Plain filename report.email.txt.",
            "Equation a@b is not email.",
            "Reference to @twitter handle.",
            "Domain URL https://kshinternational.com/investors.",
            "Mathematical expression x = y @ z.",
            "Spaces inside user @ domain.com.",
            "Missing username @domain.com."
        ]
        for text in non_emails:
            entities = self.detector.detect_pii(text)
            detected_emails = [e.text for e in entities if e.category == "EMAIL_ADDRESS"]
            self.assertEqual(len(detected_emails), 0, f"False positive email detected in '{text}': {detected_emails}")

if __name__ == "__main__":
    unittest.main()
