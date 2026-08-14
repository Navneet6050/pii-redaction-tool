#!/usr/bin/env python3
"""
===============================================================================
Regression Test Suite — Targeted Regression Protection
===============================================================================
Tests every specifically targeted fix:
- CREDIT_CARD: all major IIN families, Luhn gate, conflict resolution vs PHONE
- FULL_NAME: contextual scoring, URL/financial phrase exclusions
- COMPANY_NAME: legal suffix expansion, URL exclusion, financial phrase exclusion
- PHYSICAL_ADDRESS: structure keyword requirement, city-only exclusion
- DATE_OF_BIRTH: "Offer Date" FP fix, strong keyword requirement
- Entity conflict resolution: CREDIT_CARD beats PHONE for same span
===============================================================================
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from pii_redactor import PIIDetector, luhn_check


def get_detector():
    return PIIDetector(method="hybrid", domain_profile=None)


class TestCreditCardRecall(unittest.TestCase):
    """CREDIT_CARD should now detect all major IIN families."""

    def setUp(self):
        self.detector = get_detector()

    def _has_cc(self, text: str) -> bool:
        return any(e.category == "CREDIT_CARD" for e in self.detector.detect_pii(text))

    def test_visa_continuous(self):
        self.assertTrue(luhn_check("4111111111111111"))
        self.assertTrue(self._has_cc("4111111111111111"))

    def test_visa_spaces(self):
        self.assertTrue(self._has_cc("4111 1111 1111 1111"))

    def test_visa_hyphens(self):
        self.assertTrue(self._has_cc("4111-1111-1111-1111"))

    def test_mastercard_continuous(self):
        self.assertTrue(luhn_check("5500005555555559"))
        self.assertTrue(self._has_cc("5500005555555559"))

    def test_mastercard_spaces(self):
        self.assertTrue(self._has_cc("5500 0055 5555 5559"))

    def test_amex_continuous(self):
        self.assertTrue(luhn_check("378282246310005"))
        self.assertTrue(self._has_cc("378282246310005"))

    def test_amex_spaced(self):
        self.assertTrue(self._has_cc("3782 822463 10005"))

    def test_discover_continuous(self):
        self.assertTrue(luhn_check("6011111111111117"))
        self.assertTrue(self._has_cc("6011111111111117"))

    def test_discover_spaces(self):
        self.assertTrue(self._has_cc("6011 1111 1111 1117"))

    def test_visa_13_digit(self):
        self.assertTrue(luhn_check("4222222222222"))
        self.assertTrue(self._has_cc("4222222222222"))

    def test_invalid_luhn_rejected(self):
        # 4111111111111112 fails Luhn — should NOT be detected as CC
        self.assertFalse(luhn_check("4111111111111112"))
        self.assertFalse(self._has_cc("4111111111111112"))


class TestCreditCardConflictResolution(unittest.TestCase):
    """CREDIT_CARD must win over PHONE_NUMBER when both could match."""

    def setUp(self):
        self.detector = get_detector()

    def test_luhn_card_beats_phone(self):
        # 4111 1111 1111 1111 is a valid Visa — must be CREDIT_CARD, not PHONE
        ents = self.detector.detect_pii("Card: 4111 1111 1111 1111")
        cats = [e.category for e in ents]
        self.assertIn("CREDIT_CARD", cats)
        self.assertNotIn("PHONE_NUMBER", cats)


class TestFullNameContextual(unittest.TestCase):
    """FULL_NAME must detect contextual names without lowering global precision."""

    def setUp(self):
        self.detector = get_detector()

    def test_name_with_mr_prefix(self):
        ents = self.detector.detect_pii("Mr. Rohan Gupta submitted the form.")
        self.assertTrue(any(e.category == "FULL_NAME" for e in ents))

    def test_name_with_director_prefix(self):
        ents = self.detector.detect_pii("Director: Kavita Deshmukh")
        self.assertTrue(any(e.category == "FULL_NAME" for e in ents))

    def test_name_with_contact_prefix(self):
        ents = self.detector.detect_pii("Contact: Ananya Verma for details.")
        self.assertTrue(any(e.category == "FULL_NAME" for e in ents))

    def test_name_with_born_context(self):
        ents = self.detector.detect_pii("Neha Chaudhary, born 12 January 1985")
        cats = [e.category for e in ents]
        self.assertIn("FULL_NAME", cats)

    def test_financial_section_heading_not_name(self):
        # "Capital Structure" is a document section, not a person name
        ents = self.detector.detect_pii("Capital Structure")
        self.assertFalse(any(e.category == "FULL_NAME" for e in ents))

    def test_financial_phrase_not_name(self):
        ents = self.detector.detect_pii("Standalone Financial Results")
        self.assertFalse(any(e.category == "FULL_NAME" for e in ents))


class TestCompanyNameFixes(unittest.TestCase):
    """COMPANY_NAME must not fire on URLs or generic financial phrases."""

    def setUp(self):
        self.detector = get_detector()

    def test_company_with_ltd(self):
        ents = self.detector.detect_pii("Signed by Apex Global Logistics Limited")
        self.assertTrue(any(e.category == "COMPANY_NAME" for e in ents))

    def test_company_with_pvt_ltd(self):
        ents = self.detector.detect_pii("Genesis Biotech Solutions Pvt Ltd filed the return.")
        self.assertTrue(any(e.category == "COMPANY_NAME" for e in ents))

    def test_company_with_llp(self):
        ents = self.detector.detect_pii("Delta Capital Management LLP")
        self.assertTrue(any(e.category == "COMPANY_NAME" for e in ents))

    def test_url_not_company(self):
        # www.domain.com must NOT be detected as COMPANY_NAME
        ents = self.detector.detect_pii("Visit www.domain.com for details.")
        self.assertFalse(any(e.category == "COMPANY_NAME" and "www" in e.text for e in ents))

    def test_http_url_not_company(self):
        ents = self.detector.detect_pii("See http://company.org for information.")
        self.assertFalse(any(e.category == "COMPANY_NAME" for e in ents))

    def test_capital_employed_not_company(self):
        ents = self.detector.detect_pii("CAPITAL EMPLOYED increased by 12%.")
        self.assertFalse(any(e.category == "COMPANY_NAME" for e in ents))

    def test_cash_and_bank_not_company(self):
        ents = self.detector.detect_pii("CASH AND BANK BALANCES stood at Rs. 45 Cr.")
        self.assertFalse(any(e.category == "COMPANY_NAME" for e in ents))

    def test_credit_card_phrase_not_company(self):
        ents = self.detector.detect_pii("CREDIT CARD payments are not accepted.")
        self.assertFalse(any(e.category == "COMPANY_NAME" for e in ents))


class TestPhysicalAddressFixes(unittest.TestCase):
    """PHYSICAL_ADDRESS must require structural keywords; city-only must be excluded."""

    def setUp(self):
        self.detector = get_detector()

    def test_full_address_with_pincode_detected(self):
        ents = self.detector.detect_pii(
            "Flat 101, Building 4, Lotus Towers, MG Road, Mumbai - 400001, Maharashtra, India"
        )
        self.assertTrue(any(e.category == "PHYSICAL_ADDRESS" for e in ents))

    def test_city_only_not_address(self):
        # "Mumbai, India" alone must NOT be PHYSICAL_ADDRESS
        ents = self.detector.detect_pii("The company operates in Mumbai, India.")
        self.assertFalse(any(e.category == "PHYSICAL_ADDRESS" for e in ents))

    def test_state_only_not_address(self):
        ents = self.detector.detect_pii("Our markets include Maharashtra and Karnataka.")
        self.assertFalse(any(e.category == "PHYSICAL_ADDRESS" for e in ents))

    def test_company_operates_in_delhi_not_address(self):
        ents = self.detector.detect_pii("The company operates in Delhi.")
        self.assertFalse(any(e.category == "PHYSICAL_ADDRESS" for e in ents))


class TestDOBFixes(unittest.TestCase):
    """DATE_OF_BIRTH: strong keyword required; Offer Date must not fire."""

    def setUp(self):
        self.detector = get_detector()

    def test_dob_with_keyword_detected(self):
        self.assertTrue(any(
            e.category == "DATE_OF_BIRTH"
            for e in self.detector.detect_pii("DOB: 15 January 1985")
        ))

    def test_born_on_detected(self):
        self.assertTrue(any(
            e.category == "DATE_OF_BIRTH"
            for e in self.detector.detect_pii("Born on 04 July 1988")
        ))

    def test_date_of_birth_full_detected(self):
        self.assertTrue(any(
            e.category == "DATE_OF_BIRTH"
            for e in self.detector.detect_pii("Date of Birth: 12/01/1990")
        ))

    def test_offer_date_not_dob(self):
        # Regression: "Offer Date" must NOT trigger DOB
        ents = self.detector.detect_pii("Offer Date: November 05, 2024")
        self.assertFalse(any(e.category == "DATE_OF_BIRTH" for e in ents))

    def test_filing_date_not_dob(self):
        ents = self.detector.detect_pii("Filing Date: January 20, 2025")
        self.assertFalse(any(e.category == "DATE_OF_BIRTH" for e in ents))

    def test_financial_period_date_not_dob(self):
        ents = self.detector.detect_pii("For the period ending March 31, 2025")
        self.assertFalse(any(e.category == "DATE_OF_BIRTH" for e in ents))

    def test_board_resolution_date_not_dob(self):
        ents = self.detector.detect_pii("Board Resolution: May 02, 2024")
        self.assertFalse(any(e.category == "DATE_OF_BIRTH" for e in ents))

    def test_sebi_order_date_not_dob(self):
        ents = self.detector.detect_pii("SEBI Order dated August 12, 2024")
        self.assertFalse(any(e.category == "DATE_OF_BIRTH" for e in ents))


if __name__ == "__main__":
    unittest.main()
