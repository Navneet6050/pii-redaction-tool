#!/usr/bin/env python3
"""
===============================================================================
Automated Deterministic Pseudonymization Unit Tests
===============================================================================
Description:
    Validates Deterministic Pseudonymization Engine:
    1. Deterministic replacement consistency (same entity + seed -> same output)
    2. Seed variance (different seed -> different output)
    3. Collision avoidance (distinct entities receive distinct replacements)
    4. Entity-type specific replacement formatting (example.com, 192.0.2.x IPs, etc.)
    5. Zero raw PII text leakage into generated replacements
===============================================================================
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from pii_redactor import PIIAnonymizer

class TestDeterministicPseudonymization(unittest.TestCase):

    def test_01_deterministic_consistency(self):
        """Verify that identical original entities receive identical replacements across instances with same seed."""
        anon1 = PIIAnonymizer(strategy="synthetic", seed=42)
        anon2 = PIIAnonymizer(strategy="synthetic", seed=42)

        rep1_name = anon1.get_replacement("Kushal Hegde", "FULL_NAME")
        rep2_name = anon2.get_replacement("Kushal Hegde", "FULL_NAME")
        self.assertEqual(rep1_name, rep2_name)

        rep1_email = anon1.get_replacement("ksh@kshinternational.com", "EMAIL_ADDRESS")
        rep2_email = anon2.get_replacement("ksh@kshinternational.com", "EMAIL_ADDRESS")
        self.assertEqual(rep1_email, rep2_email)

    def test_02_seed_variance(self):
        """Verify that changing the random seed changes the generated replacement values."""
        anon_seed42 = PIIAnonymizer(strategy="synthetic", seed=42)
        anon_seed99 = PIIAnonymizer(strategy="synthetic", seed=99)

        rep_seed42 = anon_seed42.get_replacement("Kushal Hegde", "FULL_NAME")
        rep_seed99 = anon_seed99.get_replacement("Kushal Hegde", "FULL_NAME")
        self.assertNotEqual(rep_seed42, rep_seed99)

    def test_03_collision_avoidance(self):
        """Verify that 100 distinct entities of the same category map to 100 distinct replacements."""
        anon = PIIAnonymizer(strategy="synthetic", seed=42)
        replacements = set()

        for i in range(100):
            orig_name = f"Person Name {i}"
            rep = anon.get_replacement(orig_name, "FULL_NAME")
            replacements.add(rep)

        self.assertEqual(len(replacements), 100, "Collision detected among generated replacements!")

    def test_04_entity_type_formatting(self):
        """Verify that generated replacements conform to safe synthetic rules."""
        anon = PIIAnonymizer(strategy="synthetic", seed=42)

        # Email
        email_rep = anon.get_replacement("target@domain.com", "EMAIL_ADDRESS")
        self.assertTrue(email_rep.endswith("@example.com"), f"Email replacement '{email_rep}' does not use example.com domain!")

        # IP Address (RFC 5737 192.0.2.x)
        ip_rep = anon.get_replacement("10.0.0.1", "IP_ADDRESS")
        self.assertTrue(ip_rep.startswith("192.0.2."), f"IP replacement '{ip_rep}' is not an RFC 5737 documentation IP!")

        # SSN
        ssn_rep = anon.get_replacement("123-45-6789", "SSN")
        self.assertTrue(ssn_rep.startswith("000-00-"), f"SSN replacement '{ssn_rep}' is not synthetic 000-00-xxxx format!")

        # Credit Card
        cc_rep = anon.get_replacement("4532123456788890", "CREDIT_CARD")
        self.assertTrue(cc_rep.startswith("4532-0000-0000-"), f"Credit card replacement '{cc_rep}' is not synthetic!")

        # Company Name (Check clean single legal suffix)
        comp_rep = anon.get_replacement("Smith & Co Ltd.", "COMPANY_NAME")
        self.assertNotIn("Ltd. Inc.", comp_rep)
        self.assertNotIn("Limited Inc", comp_rep)

    def test_05_no_original_pii_leakage(self):
        """Verify that original PII text strings never leak into generated synthetic replacements."""
        anon = PIIAnonymizer(strategy="synthetic", seed=42)
        original_pii = "KushalSubbayyaHegde"
        
        rep = anon.get_replacement(original_pii, "FULL_NAME")
        self.assertNotIn(original_pii.lower(), rep.lower())

if __name__ == "__main__":
    unittest.main()
