#!/usr/bin/env python3
"""Unit tests for IP_ADDRESS detection (IPv4, IPv6, version string filtering)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from pii_redactor import PIIDetector, is_valid_ip

class TestIPDetection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.detector = PIIDetector(method="hybrid", domain_profile=None)

    def test_ip_validation_function(self):
        self.assertTrue(is_valid_ip("192.168.1.1"))
        self.assertTrue(is_valid_ip("10.0.0.255"))
        self.assertTrue(is_valid_ip("2001:0db8:85a3:0000:0000:8a2e:0370:7334"))
        self.assertFalse(is_valid_ip("999.999.999.999"))
        self.assertFalse(is_valid_ip("192.168.1"))

    def test_positive_ip(self):
        positive_ips = [
            ("Server IP: 192.168.1.1 connected.", "192.168.1.1"),
            ("Gateway IP: 10.0.0.255 active.", "10.0.0.255")
        ]
        for text, expected in positive_ips:
            entities = self.detector.detect_pii(text)
            detected = [e.text for e in entities if e.category == "IP_ADDRESS"]
            self.assertIn(expected, detected, f"Failed to detect IP '{expected}' in '{text}'")

    def test_negative_version_numbers(self):
        negative_ips = [
            "Software version 1.2.3.4 released.",
            "Invalid IP 999.999.999.999.",
            "Section 1.2.3 reference.",
            "ISO standard 9001.2015."
        ]
        for text in negative_ips:
            entities = self.detector.detect_pii(text)
            detected_ips = [e.text for e in entities if e.category == "IP_ADDRESS"]
            self.assertEqual(len(detected_ips), 0, f"False positive IP detected in '{text}': {detected_ips}")

if __name__ == "__main__":
    unittest.main()
