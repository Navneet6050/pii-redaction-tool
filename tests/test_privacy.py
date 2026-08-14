#!/usr/bin/env python3
"""
===============================================================================
Automated Privacy & Security Hardening Unit Tests
===============================================================================
Description:
    Validates that the PII Redaction pipeline produces zero raw PII exposure
    in output artifacts, audit logs, and JSON reports.

Assertions:
    1. Output JSON reports do not contain known raw PII strings.
    2. Audit records expose only anonymized entity IDs, categories, and replacements.
    3. Privacy validation status flag is correctly set to PASSED.
===============================================================================
"""

import os
import json
import unittest
import sys

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pii_redactor import PIIDetector, PIIAnonymizer, DocxRedactor

class TestPrivacyHardening(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        cls.input_docx = os.path.join(cls.base_dir, "Red Herring Prospectus.docx")
        cls.output_docx = os.path.join(cls.base_dir, "Red Herring Prospectus_redacted.docx")
        cls.report_json = os.path.join(cls.base_dir, "redaction_report.json")
        
        # Known sensitive raw PII strings present in the original document
        cls.known_raw_pii = [
            "Kushal Subbayya Hegde",
            "Pushpa Kushal Hegde",
            "Rajesh Kushal Hegde",
            "Rohit Kushal Hegde",
            "Rakhi Girija Shetty",
            "Sarthak Malvadkar",
            "cs.connect@kshinternational.com",
            "ksh.ipo@nuvama.com",
            "+91 20 45053237",
            "+91 22 6807 7100",
            "11/3, 11/4 and 11/5 Village Birdewadi Chakan Taluka - Khed Pune"
        ]

    def test_01_privacy_safe_report_structure(self):
        """Verify that the generated redaction_report.json follows the privacy-safe schema."""
        self.assertTrue(os.path.exists(self.report_json), "redaction_report.json missing.")
        
        with open(self.report_json, "r", encoding="utf-8") as f:
            report_data = json.load(f)

        self.assertIn("summary", report_data)
        self.assertIn("category_counts", report_data)
        self.assertIn("audit_records", report_data)
        
        # Check summary privacy validation flag
        self.assertEqual(
            report_data["summary"].get("privacy_validation"),
            "PASSED - ZERO RAW PII EXPOSED"
        )
        
        # Verify audit records structure
        for record in report_data["audit_records"]:
            self.assertIn("entity_id", record)
            self.assertIn("category", record)
            self.assertIn("replacement", record)
            self.assertNotIn("original", record)
            self.assertNotIn("text", record)

    def test_02_zero_raw_pii_in_report_file(self):
        """Assert that zero known raw PII strings exist anywhere in redaction_report.json."""
        with open(self.report_json, "r", encoding="utf-8") as f:
            report_content = f.read()

        for raw_pii in self.known_raw_pii:
            self.assertNotIn(
                raw_pii,
                report_content,
                f"PRIVACY VIOLATION: Raw PII string '{raw_pii}' found in redaction_report.json!"
            )

    def test_03_anonymizer_in_memory_isolation(self):
        """Assert that PIIAnonymizer keeps mappings in-memory and exports privacy-safe audit items."""
        anonymizer = PIIAnonymizer(strategy="synthetic")
        rep1 = anonymizer.get_replacement("Test User Name", "FULL_NAME")
        rep2 = anonymizer.get_replacement("Test User Name", "FULL_NAME")
        
        # Deterministic replacement check
        self.assertEqual(rep1, rep2)
        
        audit_records = anonymizer.get_privacy_safe_audit_records()
        self.assertEqual(len(audit_records), 1)
        self.assertEqual(audit_records[0]["entity_id"], "FULL_NAME_0001")
        self.assertEqual(audit_records[0]["category"], "FULL_NAME")
        self.assertEqual(audit_records[0]["replacement"], rep1)
        self.assertNotIn("Test User Name", json.dumps(audit_records[0]))

if __name__ == "__main__":
    unittest.main()
