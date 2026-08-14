#!/usr/bin/env python3
"""Unit tests for Overlap and Entity Resolution Engine."""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from pii_redactor import PIIDetector, PIIEntity, DomainProfile

class TestEntityResolution(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.detector = PIIDetector(method="hybrid", domain_profile=DomainProfile.get_rhp_default_profile())

    def test_overlap_resolution_priority(self):
        candidates = [
            PIIEntity(category="FULL_NAME", start=0, end=12, text="Kushal Hegde", confidence=0.9, source="NER"),
            PIIEntity(category="FULL_NAME", start=0, end=21, text="Kushal Subbayya Hegde", confidence=1.0, source="GAZETTEER")
        ]
        resolved = self.detector.resolve_overlaps(candidates)
        
        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0].text, "Kushal Subbayya Hegde")
        self.assertEqual(resolved[0].confidence, 1.0)

    def test_non_overlapping_spans_preserved(self):
        candidates = [
            PIIEntity(category="FULL_NAME", start=0, end=12, text="Kushal Hegde", confidence=1.0, source="GAZETTEER"),
            PIIEntity(category="EMAIL_ADDRESS", start=25, end=45, text="user@example.com", confidence=1.0, source="REGEX")
        ]
        resolved = self.detector.resolve_overlaps(candidates)
        self.assertEqual(len(resolved), 2)

if __name__ == "__main__":
    unittest.main()
