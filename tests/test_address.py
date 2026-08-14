#!/usr/bin/env python3
"""Unit tests for PHYSICAL_ADDRESS detection (Indian street, village, office, multi-line)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from pii_redactor import PIIDetector, DomainProfile

class TestAddressDetection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.detector_hybrid = PIIDetector(method="hybrid", domain_profile=DomainProfile.get_rhp_default_profile())
        cls.detector_standalone = PIIDetector(method="hybrid", domain_profile=None)

    def test_positive_addresses(self):
        positive_addresses = [
            "Registered Office: Flat 101, Business Park, Baner Road, Pune - 411045, Maharashtra, India.",
            "Office No. 201, Montreal Business Centre, Off Pallod Farms, Baner Pune 411045.",
            "11/3, 11/4 and 11/5 Village Birdewadi Chakan Taluka - Khed Pune – 410 501 Maharashtra, India.",
            "Plot 12, Industrial Estate, Sector 5, Navi Mumbai - 400703.",
            "Address: 123 Main Street, New Delhi",
            "Mailing Address: 45 MG Road, Bengaluru",
            "Registered Address: 221B Baker Street, London",
            "12 Park Avenue, Mumbai"
        ]
        for text in positive_addresses:
            entities = self.detector_hybrid.detect_pii(text)
            detected = [e.text for e in entities if e.category == "PHYSICAL_ADDRESS"]
            self.assertTrue(
                len(detected) >= 1,
                f"Failed to detect physical address in '{text}'"
            )

    def test_street_style_addresses_detected(self):
        street_addresses = [
            "Address: 123 Main Street, New Delhi",
            "Mailing Address: 45 MG Road, Bengaluru",
            "Registered Address: 221B Baker Street, London",
            "12 Park Avenue, Mumbai"
        ]
        for text in street_addresses:
            entities = self.detector_standalone.detect_pii(text)
            detected = [e.text for e in entities if e.category == "PHYSICAL_ADDRESS"]
            self.assertTrue(
                len(detected) >= 1,
                f"Failed to detect physical address in '{text}' (standalone detector)"
            )

    def test_negative_prose_city_mentions(self):
        prose_mentions = [
            "The company has operations in Pune and Mumbai.",
            "Growth in Maharashtra and Gujarat markets.",
            "Meetings held in New Delhi.",
            "Exporting to United States and Europe.",
            "Expansion plans in India."
        ]
        for text in prose_mentions:
            entities = self.detector_standalone.detect_pii(text)
            detected_addrs = [e.text for e in entities if e.category == "PHYSICAL_ADDRESS"]
            self.assertEqual(
                len(detected_addrs), 0,
                f"False positive address detected in '{text}': {detected_addrs}"
            )

if __name__ == "__main__":
    unittest.main()
