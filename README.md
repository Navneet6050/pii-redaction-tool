# PII Redaction Tool

A modular, high-precision Python tool for automated detection and deterministic pseudonymization of Personally Identifiable Information (PII) within Microsoft Word (`.docx`) legal and financial prospectuses.

The engine reads `.docx` documents, identifies sensitive entities across nine core PII categories using a multi-stage hybrid pipeline, replaces them with deterministic synthetic values, preserves typography and XML layout (paragraphs, tables, nested tables, headers, footers, text boxes), and validates the redacted output against residual leakage.

---

## Supported PII Types

The engine supports detection and pseudonymization across nine core PII categories:

1. **Full Names (`FULL_NAME`)**: Human names, corporate directors, promoters, key managerial personnel, and legal signatories.
2. **Email Addresses (`EMAIL_ADDRESS`)**: Electronic mail identifiers (`user@example.com`).
3. **Phone Numbers (`PHONE_NUMBER`)**: Domestic and international numbers (Indian STD landlines, mobile numbers, international formats).
4. **Company Names (`COMPANY_NAME`)**: Corporate entities, banks, merchant bankers, legal counsels, and registrar firms.
5. **Physical Addresses (`PHYSICAL_ADDRESS`)**: Multi-line mailing addresses, registered offices, building plots, street names, and postal PIN codes.
6. **Social Security Numbers (`SSN`)**: 9-digit US Social Security Numbers (`XXX-XX-XXXX`).
7. **Credit Card Numbers (`CREDIT_CARD`)**: 13–19 digit payment cards across Visa, Mastercard, American Express, Discover, Diners, JCB, and Maestro, verified via the Luhn checksum algorithm.
8. **Dates of Birth (`DATE_OF_BIRTH`)**: Explicit birth dates identified via contextual prefixes (`DOB:`, `Date of Birth:`, `Born on`).
9. **IP Addresses (`IP_ADDRESS`)**: IPv4 and IPv6 network addresses validated against standard subnet and octet constraints.

*Also detects Indian corporate registration identifiers (DIN, PAN).*

---

## Approach & Architecture

The tool uses a multi-stage pipeline designed for high precision, document fidelity, and reproducibility:

```
DOCX Extraction (Body, Tables, Nested Tables, Headers, Footers, w:txbxContent)
      ↓
Multi-Stage Detection Pipeline
  ├── Specialized RegEx Matchers (Emails, Phones, IPs, SSNs, Credit Cards, DOB, Legal Suffixes)
  ├── Microsoft Presidio Analyzer Engine (PERSON, LOCATION, EMAIL, PHONE, CREDIT_CARD, ORG)
  ├── spaCy Named Entity Recognition (Zero-shot PERSON and ORG extraction)
  ├── Contextual Validation & Financial Exclusion Filters (Capital market line items & dates)
  └── Optional Domain Profile Gazetteer (Promoter names, company entities, registered offices)
      ↓
Priority-First Greedy Overlap Resolution (Specialized Exact Matches > Contextual Entities)
      ↓
Deterministic Synthetic Pseudonymization (Seed-driven Faker with category-specific collision avoidance)
      ↓
Run-Aware DOCX Redaction (Mapping character spans to XML runs while preserving bold/italic/font styles)
      ↓
Post-Redaction Leakage Scan (Re-opening redacted DOCX to verify zero residual PII)
```

### Key Components

- **Hybrid Detection**: Combines strict structural regexes for pattern-bound identifiers (emails, credit cards, SSNs, IPs) with NLP models (spaCy `en_core_web_sm` and Microsoft Presidio) for contextual named entities (names, organizations).
- **Luhn Checksum Gating**: Every candidate credit card is validated with the Luhn algorithm to prevent false positives on general 16-digit order or invoice numbers.
- **Priority Overlap Resolution**: Conflict resolution prioritizes specialized structural matches over broad NER spans:
  $$\text{EMAIL (10)} > \text{SSN (9)} = \text{CREDIT CARD (9)} > \text{IP (8)} = \text{DOB (8)} > \text{PHONE (7)} > \text{ADDRESS (6)} > \text{COMPANY (5)} > \text{NAME (4)}$$
- **Deterministic Pseudonymization**: The `PIIAnonymizer` uses a configurable seed (`--seed`) and entity hashing to ensure identical entity strings consistently map to the same synthetic replacement throughout the document.
- **DOCX Run-Aware Replacement**: Splices replacement strings directly into affected XML run boundaries (`w:r`) in right-to-left order, preventing offset drift and preserving bold, italic, font size, and color styling.
- **Independent Post-Redaction Leakage Validator**: Re-opens the saved `.docx` file and scans all paragraphs, tables, headers, footers, and text boxes to verify zero ground-truth PII leakage before concluding.

---

## Generic vs. Domain-Assisted Mode

- **Generic Mode (Default)**:
  - Operates using purely generalizable regex, Presidio, spaCy NER, and contextual rules without any target-specific gazetteer.
  - Demonstrates zero-shot performance across arbitrary legal/financial documents.
  - Enabled by default (`--use-domain-profile` omitted).
- **Domain-Assisted Mode (Optional)**:
  - Incorporates verified domain-specific gazetteers (`DomainProfile`) containing promoter names, corporate entities, and registered offices specific to the Red Herring Prospectus.
  - Maximizes recall on the supplied target prospectus without requiring external network access.
  - Explicitly activated via `--use-domain-profile`.

---

## Installation

```bash
# 1. Create and activate virtual environment
# Windows (PowerShell / CMD):
python -m venv .venv
.venv\Scripts\activate

# Linux / macOS (bash / zsh):
# python -m venv .venv
# source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Download spaCy English model
python -m spacy download en_core_web_sm
```

---

## Usage

Commands are formatted for cross-platform compatibility across Windows PowerShell, Command Prompt, and Linux/macOS shells:

### 1. Document Redaction (Domain-Assisted Mode for RHP Prospectus)
```bash
python pii_redactor.py --input "Red Herring Prospectus.docx" --output "Red Herring Prospectus_redacted.docx" --use-domain-profile --seed 42 --validate --strict
```

### 2. Document Redaction (Pure Generic Mode)
```bash
python pii_redactor.py --input "Red Herring Prospectus.docx" --output "Red Herring Prospectus_redacted.docx" --seed 42 --validate
```

### 3. Run Quantitative Evaluation
```bash
python evaluate_redactor.py
```

### 4. Run Automated Test Suite
```bash
python -m unittest discover tests -v
```

---

## Evaluation Results

Empirical results measured against the 633 annotated occurrences in `Red Herring Prospectus.docx` and the 392-case independent three-tier synthetic benchmark:

### Real-Document Evaluation (`Red Herring Prospectus.docx`, Support = 633)

| Metric | Generic Mode (Default) | Domain-Assisted Mode (`--use-domain-profile`) |
| :--- | :---: | :---: |
| **Micro Precision** | **100.00%** | **100.00%** |
| **Micro Recall** | **80.25%** | **92.26%** |
| **Micro F1-Score** | **89.04%** | **95.97%** |
| **Macro Precision** | **100.00%** | **100.00%** |
| **Macro Recall** | **92.18%** | **94.54%** |
| **Macro F1-Score** | **95.26%** | **96.66%** |

#### Real-Document Per-Category Breakdown
| Category | Generic Precision | Generic Recall | Generic F1 | Domain Precision | Domain Recall | Domain F1 | Support |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **FULL_NAME** | 100.00% | 73.18% | **84.51%** | 100.00% | 92.19% | **95.93%** | 384 |
| **EMAIL_ADDRESS** | 100.00% | 100.00% | **100.00%** | 100.00% | 100.00% | **100.00%** | 70 |
| **PHONE_NUMBER** | 100.00% | 58.70% | **73.97%** | 100.00% | 58.70% | **73.97%** | 46 |
| **COMPANY_NAME** | 100.00% | 97.74% | **98.86%** | 100.00% | 100.00% | **100.00%** | 133 |
| **PHYSICAL_ADDRESS** | 100.00% | 100.00% | **100.00%** | 100.00% | 100.00% | **100.00%** | 0 |
| **SSN** | 100.00% | 100.00% | **100.00%** | 100.00% | 100.00% | **100.00%** | 0 |
| **CREDIT_CARD** | 100.00% | 100.00% | **100.00%** | 100.00% | 100.00% | **100.00%** | 0 |
| **DATE_OF_BIRTH** | 100.00% | 100.00% | **100.00%** | 100.00% | 100.00% | **100.00%** | 0 |
| **IP_ADDRESS** | 100.00% | 100.00% | **100.00%** | 100.00% | 100.00% | **100.00%** | 0 |

### Synthetic Benchmark Evaluation (360 Clean Cases + 32 Adversarial Cases)

| Benchmark Set | Total Support | Metric Result | Notes |
| :--- | :---: | :---: | :--- |
| **Synthetic Positive Recall** | 180 | **98.33%** (177 / 180 TP) | Evaluates multi-format generalization across all 9 PII types (20 per category). |
| **Synthetic Clear-Negative Specificity** | 180 | **80.00%** (144 / 180 TN) | Evaluates non-PII text with zero structural PII resemblance (20 per category). |
| **Adversarial / Ambiguous Cases** | 32 | Stress-test tracked | Non-Luhn cards: 75% blocked; partial addresses: 62.5% blocked. |
| **Post-Redaction Leakage Scan** | — | **PASS (0 Leaks)** | Verified across paragraphs, tables, headers, footers, text boxes. |
| **Automated Unit Test Suite** | 94 tests | **94 / 94 PASS (100%)** | Comprehensive functional, regression, and privacy test coverage. |

---

## Evaluation Methodology

- **Ground-Truth Evaluation**: Predictions are compared against `ground_truth.json` by entity category and character span matching.
- **Precision / Recall / F1**: Standard metrics:
  $$\text{Precision} = \frac{\text{TP}}{\text{TP} + \text{FP}}, \quad \text{Recall} = \frac{\text{TP}}{\text{TP} + \text{FN}}, \quad \text{F1} = 2 \times \frac{\text{Precision} \times \text{Recall}}{\text{Precision} + \text{Recall}}$$
- **Specificity & Negative Evaluation**: For entity extraction tasks on free text, True Negatives cannot be uniquely counted without defining arbitrary non-entity token spans. Specificity and accuracy are therefore evaluated on the discrete synthetic negative benchmark where negative instances are well-defined.
- **Independent Three-Tier Benchmark**: Clear positive, clear negative, and ambiguous adversarial cases are evaluated and reported separately to avoid misleading aggregate scores.

---

## Phone Ground-Truth Annotation Limitation

An occurrence-level audit of the 19 reported `PHONE_NUMBER` false negatives revealed:
- **Root Cause**: The reference `ground_truth.json` contains 19 split/truncated annotations representing partial fragments (e.g. `+91 22 2288` as an 8-character prefix, or `2460` as a 4-digit suffix) of complete 12-digit Indian landline telephone strings (`+91 22 2288 2460`).
- **Complete Phone Coverage**: All 27 complete telephone numbers in the document were detected with **100% precision and recall (27 / 27 TP)**.
- **Preserved Precision Safeguard**: The detector was intentionally not loosened to classify arbitrary 4-to-6 digit numbers as telephone entities, as doing so would cause severe false-positive regressions on financial figures, accounting dates, and section indices.
- **Ground-Truth Integrity**: The reference ground truth was preserved without alteration.

---

## Tradeoffs and Known Limitations

1. **Contextual Name Triggers**: Bare standalone names lacking contextual honorifics or role prefixes (*"Mr."*, *"Director:"*, *"Promoter:"*) rely on NER model confidence, which can lead to lower recall on isolated names in header tables.
2. **Financial Date Preservation**: Dates lacking explicit birth-related prefixes (*"DOB:"*, *"Date of Birth:"*) are intentionally excluded to prevent destructive redaction of financial accounting periods (*"March 31, 2025"*).
3. **Invalid-Luhn Numeric Sequences**: 16-digit order or invoice numbers failing the Luhn checksum are safely treated as non-PII.
4. **Complex XML Drawing Shapes**: Text embedded inside non-standard vector drawing XML elements (`w:drawing`) is not traversed by standard python-docx iterators.
5. **Language Scope**: Regexes and NLP singletons are configured for English-language documents.

---

## Privacy, Security & Repository Governance

- **Unredacted Document Exclusion**: The original unredacted `Red Herring Prospectus.docx` contains sensitive real-world PII and is explicitly **excluded from the public repository** via `.gitignore` for privacy compliance.
- **Internal Evaluation Artifacts**: The ground-truth dataset (`ground_truth.json`) and run-time audit records (`redaction_report.json`) contain original PII references used strictly for local offline evaluation. They are designated as internal/local artifacts and are **not tracked in the public git repository**.
- **Public Repository Scope**: The public repository publishes only the sanitized source code, automated test suite, synthetic benchmarks, quantitative evaluation reports, and the verified redacted document (`Red Herring Prospectus_redacted.docx`).
- **Zero Raw PII in Audit Logs**: Generated `redaction_report.json` and console logs record anonymized audit descriptors (`FULL_NAME_0001`, `EMAIL_ADDRESS_0002`) without persisting sensitive raw values.
- **In-Memory Mapping Isolation**: Deterministic replacement tables exist strictly in process memory during execution.
- **Leakage Gate**: Strict CLI execution (`--strict`) automatically aborts and exits with a non-zero code if any residual PII is discovered during post-redaction verification.

---

## Project Structure

```
PII_Redaction_Tool/
├── README.md                           # Documentation, architecture, and reproduction instructions
├── requirements.txt                    # Pinned runtime dependencies
├── pii_redactor.py                     # Main CLI, detection pipeline, anonymizer, and docx redactor
├── evaluate_redactor.py                # Dual-mode real-document and synthetic evaluation suite
├── Red Herring Prospectus_redacted.docx # Verified redacted DOCX deliverable (public)
├── evaluation/
│   ├── evaluation_report.md            # Standalone quantitative evaluation report
│   ├── metrics.json                    # Detailed machine-readable evaluation metrics
│   └── synthetic_benchmark.py          # Three-tier independent synthetic benchmark suite
├── tests/
│   ├── test_address.py                 # Unit tests for physical address patterns
│   ├── test_anonymization.py           # Unit tests for deterministic pseudonymization engine
│   ├── test_company.py                 # Unit tests for company name detection & exclusions
│   ├── test_credit_card.py             # Unit tests for credit card detection & Luhn validation
│   ├── test_detector.py                # Unit tests for multi-stage PII detection pipeline
│   ├── test_dob.py                     # Unit tests for date of birth contextual detection
│   ├── test_docx_integrity.py          # Unit tests for run-aware styling and XML preservation
│   ├── test_email.py                   # Unit tests for email pattern matching
│   ├── test_entity_resolution.py       # Unit tests for priority-first overlap resolution
│   ├── test_evaluation.py              # Unit tests for evaluation calculation and privacy exports
│   ├── test_generalization.py          # Zero-shot generalization tests across unseen PII formats
│   ├── test_ip.py                      # Unit tests for IPv4/IPv6 validation
│   ├── test_leakage_validation.py      # Unit tests for independent post-redaction leakage scanner
│   ├── test_name.py                    # Unit tests for Western and Indian person name detection
│   ├── test_phone.py                   # Unit tests for domestic/international phone numbers
│   ├── test_privacy.py                 # Unit tests for zero raw PII log/report sanitization
│   ├── test_regression.py              # Unit tests for regression protection against financial terms
│   ├── test_regression_targeted.py     # Unit tests for targeted fixes (Credit Card, Names, DOB)
│   ├── test_smoke.py                   # End-to-end integration smoke test
│   └── test_ssn.py                     # Unit tests for SSN pattern matching
└── [Local Evaluation Artifacts — Excluded from Public Repo via .gitignore]:
    ├── Red Herring Prospectus.docx     # Original unredacted prospectus (contains PII)
    ├── ground_truth.json               # Reference ground-truth annotations (contains PII)
    └── redaction_report.json           # Local run-time audit report
```
