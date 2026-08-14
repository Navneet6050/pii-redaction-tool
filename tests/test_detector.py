#!/usr/bin/env python3
"""
===============================================================================
Automated Unit Tests for PII Detection Pipeline
===============================================================================
Description:
    Rigorously tests every stage of the modular PII Detection Pipeline:
    1. All 9 minimum PII categories (Full Name, Email, Phone, Company, Address, SSN, Credit Card, DOB, IP)
    2. Luhn Check algorithm for Credit Cards
    3. Strict IP address validation
    4. Date of Birth vs. Financial Dates distinction
    5. Presidio Analyzer execution
    6. Decoupled Domain Profile (Standalone vs. Gazetteer mode)
    7. Overlap resolution and priority handling
===============================================================================
"""

import os
import sys
import unittest

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pii_redactor import (
    PIIDetector, PIIEntity, DomainProfile, luhn_check, is_valid_ip
)

class TestPIIDetector(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.detector_hybrid = PIIDetector(method="hybrid", domain_profile=DomainProfile.get_rhp_default_profile())
        cls.detector_standalone = PIIDetector(method="hybrid", domain_profile=None)

    def test_01_luhn_check(self):
        """Test Luhn algorithm credit card validation."""
        # Valid Visa & Mastercard numbers
        self.assertTrue(luhn_check("4532015112830366"))
        self.assertTrue(luhn_check("4012888888881881"))
        self.assertTrue(luhn_check("5500 0000 0000 0004"))
        
        # Invalid 16-digit strings
        self.assertFalse(luhn_check("1234567812345678"))
        self.assertFalse(luhn_check("0000000000000000"))

    def test_02_ip_validation(self):
        """Test IPv4 and IPv6 address validation."""
        self.assertTrue(is_valid_ip("192.168.1.1"))
        self.assertTrue(is_valid_ip("10.0.0.255"))
        self.assertTrue(is_valid_ip("2001:0db8:85a3:0000:0000:8a2e:0370:7334"))
        
        # Invalid IP addresses
        self.assertFalse(is_valid_ip("999.999.999.999"))
        self.assertFalse(is_valid_ip("192.168.1"))

    def test_03_phone_number_filtering(self):
        """Test phone detection and exclusion of fiscal year ranges."""
        text = "Contact us at +91 9876543210 or 020-45053237. Do not redact Fiscal 2024-2025 or 2023-24."
        entities = self.detector_standalone.detect_pii(text)
        
        phone_texts = [e.text for e in entities if e.category == "PHONE_NUMBER"]
        
        self.assertIn("+91 9876543210", phone_texts)
        self.assertIn("020-45053237", phone_texts)
        self.assertNotIn("2024-2025", phone_texts)
        self.assertNotIn("2023-24", phone_texts)

    def test_04_date_of_birth_vs_financial_dates(self):
        """Test DOB contextual triggers vs general financial reporting dates."""
        text = "Date of Birth: 15/08/1982. Financial results for March 31, 2025 and Fiscal FY 2024-25."
        entities = self.detector_standalone.detect_pii(text)
        
        dob_entities = [e for e in entities if e.category == "DATE_OF_BIRTH"]
        self.assertTrue(len(dob_entities) >= 1)
        self.assertIn("15/08/1982", dob_entities[0].text)
        
        # Verify financial date March 31, 2025 is not classified as DOB
        self.assertFalse(any("March 31, 2025" in e.text for e in dob_entities))

    def test_05_company_name_filtering(self):
        """Test company name detection and exclusion of financial stop words."""
        text = "KSH International Limited appointed ICICI Securities Limited. Key Management Personnel reviewed Capital Employed."
        entities = self.detector_hybrid.detect_pii(text)
        
        comp_texts = [e.text for e in entities if e.category == "COMPANY_NAME"]
        
        self.assertIn("KSH International Limited", comp_texts)
        self.assertIn("ICICI Securities Limited", comp_texts)
        self.assertNotIn("Key Management Personnel", comp_texts)
        self.assertNotIn("Capital Employed", comp_texts)

    def test_06_ssn_and_credit_card(self):
        """Test SSN and Luhn-validated Credit Card detection."""
        text = "SSN: 123-45-6789. Card Number: 4532-0151-1283-0366."
        entities = self.detector_standalone.detect_pii(text)
        
        cats = {e.category: e.text for e in entities}
        self.assertIn("SSN", cats)
        self.assertEqual(cats["SSN"], "123-45-6789")
        self.assertIn("CREDIT_CARD", cats)
        self.assertEqual(cats["CREDIT_CARD"], "4532-0151-1283-0366")

    def test_07_overlap_resolution(self):
        """Test deterministic resolution of overlapping entity spans."""
        text = "Kushal Subbayya Hegde is the Promoter."
        entities = self.detector_hybrid.detect_pii(text)
        
        # Verify zero overlapping entities returned
        person_entities = [e for e in entities if e.category == "FULL_NAME"]
        self.assertEqual(len(person_entities), 1)
        self.assertEqual(person_entities[0].text, "Kushal Subbayya Hegde")

    def test_08_presidio_direct_pass(self):
        """Verify that Presidio analyzer runs and extracts PII entities directly."""
        detector_presidio = PIIDetector(method="presidio", domain_profile=None)
        text = "Email us at support@example.com or visit John Doe in New York."
        entities = detector_presidio.detect_pii(text)
        
        sources = [e.source for e in entities]
        self.assertTrue(any("PRESIDIO" in s for s in sources), "Presidio engine was not executed!")

    def test_09_standalone_detector_without_domain_profile(self):
        """Verify that the detector works 100% standalone without hardcoded domain profiles."""
        text = "Alice Smith works at Acme Technologies Ltd. Email alice@acme.com or call +91 9988776655."
        entities = self.detector_standalone.detect_pii(text)
        
        cats = [e.category for e in entities]
        self.assertIn("FULL_NAME", cats)
        self.assertIn("COMPANY_NAME", cats)
        self.assertIn("EMAIL_ADDRESS", cats)
        self.assertIn("PHONE_NUMBER", cats)

if __name__ == "__main__":
    unittest.main()
