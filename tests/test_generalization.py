#!/usr/bin/env python3
"""
===============================================================================
Generalization Test Suite (Requirement 11)
===============================================================================
Description:
    Tests PIIDetector in pure GENERIC mode (use_domain_profile=False / domain_profile=None)
    against unseen synthetic entities that do NOT exist in the RHP DomainProfile gazetteer.
    Proves zero-shot detection capability without overfitting.
===============================================================================
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from pii_redactor import PIIDetector, luhn_check

class TestGeneralizationZeroShot(unittest.TestCase):

    def setUp(self):
        # Explicitly initialize detector in pure GENERIC mode (no domain profile)
        self.detector = PIIDetector(method="hybrid", domain_profile=None)

    def test_01_unseen_full_names(self):
        text = "Meeting attended by Alexander Hamilton and Benjamin Franklin."
        entities = self.detector.detect_pii(text)
        cats = [e.category for e in entities]
        texts = [e.text for e in entities]
        
        self.assertIn("FULL_NAME", cats)
        self.assertTrue(any("Alexander Hamilton" in t or "Benjamin Franklin" in t for t in texts))

    def test_02_unseen_company_names(self):
        text = "Audit performed by Quantum Leap Technologies Inc. and Horizon Financial Holdings Limited."
        entities = self.detector.detect_pii(text)
        cats = [e.category for e in entities]
        
        self.assertIn("COMPANY_NAME", cats)

    def test_03_unseen_emails_phones_ips(self):
        text = "Contact founder at dev.lead@nexus-cyber.io or +1 415 555 0199. Server IP: 198.51.100.45."
        entities = self.detector.detect_pii(text)
        cats = [e.category for e in entities]
        
        self.assertIn("EMAIL_ADDRESS", cats)
        self.assertIn("PHONE_NUMBER", cats)
        self.assertIn("IP_ADDRESS", cats)

    def test_04_unseen_ssn_credit_card_dob(self):
        # 4111-1111-1111-1111 passes Luhn check
        text = "Employee SSN: 987-65-4321. Credit Card: 4111-1111-1111-1111. Date of Birth: 14 August 1988."
        entities = self.detector.detect_pii(text)
        cats = [e.category for e in entities]
        
        self.assertIn("SSN", cats)
        self.assertIn("CREDIT_CARD", cats)
        self.assertIn("DATE_OF_BIRTH", cats)

    def test_05_unseen_generic_address(self):
        text = "Headquarters located at Plot 45, Cyber City Phase 2, Gurgaon – 122002, Maharashtra, India."
        entities = self.detector.detect_pii(text)
        cats = [e.category for e in entities]
        
        self.assertIn("PHYSICAL_ADDRESS", cats)

if __name__ == "__main__":
    unittest.main()
