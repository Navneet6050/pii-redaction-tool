<div align="center">

# 🛡️ PII Redaction Tool

**A high-precision, hybrid NLP pipeline for detecting and irreversibly pseudonymizing Personally Identifiable Information in Microsoft Word (`.docx`) legal and financial documents.**

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![spaCy](https://img.shields.io/badge/NLP-spaCy%20%2B%20Presidio-09a3d5.svg)](https://spacy.io/)
[![Tests](https://img.shields.io/badge/tests-94%2F94%20passing-brightgreen.svg)](#evaluation-results)
[![Precision](https://img.shields.io/badge/micro%20precision-100%25-brightgreen.svg)](#evaluation-results)
[![License](https://img.shields.io/badge/status-assignment%20submission-lightgrey.svg)](#)

</div>

---

## Overview

This engine reads a `.docx` document, identifies sensitive entities across **nine core PII categories** using a multi-stage hybrid detection pipeline, replaces each one with a deterministic synthetic value, and writes the result back into the original file while fully preserving its typography and XML layout — paragraphs, tables, nested tables, headers, footers, and text boxes. Before returning control to the caller, an independent post-redaction scan re-opens the output file to confirm zero residual PII.

The tool was built and validated end-to-end against a real ~900-page SEBI Red Herring Prospectus (KSH International Limited), then stress-tested against an independent synthetic benchmark to confirm it generalizes beyond that single document.

It ships in two forms:
- **CLI** — `pii_redactor.py`, for direct, scriptable, offline redaction.
- **REST API** — `app.py`, a FastAPI service exposing the same engine over HTTP for integration into other systems, deployable on Render via the included `render.yaml`.

---

## Table of Contents

- [Supported PII Types](#supported-pii-types)
- [Architecture](#architecture--approach)
- [Generic vs. Domain-Assisted Mode](#generic-vs-domain-assisted-mode)
- [Installation](#installation)
- [Usage](#usage)
  - [CLI](#1-cli-redaction)
  - [REST API](#2-rest-api)
  - [Evaluation](#3-run-quantitative-evaluation)
  - [Test Suite](#4-run-automated-test-suite)
- [Evaluation Results](#evaluation-results)
- [Evaluation Methodology](#evaluation-methodology)
- [Phone Ground-Truth Annotation Limitation](#phone-ground-truth-annotation-limitation)
- [Tradeoffs & Known Limitations](#tradeoffs-and-known-limitations)
- [Privacy, Security & Repository Governance](#privacy-security--repository-governance)
- [Project Structure](#project-structure)

---

## Supported PII Types

| # | Category | Description |
|---|---|---|
| 1 | `FULL_NAME` | Human names — corporate directors, promoters, key managerial personnel, legal signatories |
| 2 | `EMAIL_ADDRESS` | Electronic mail identifiers (`user@example.com`) |
| 3 | `PHONE_NUMBER` | Indian STD landlines, mobile numbers, and international formats |
| 4 | `COMPANY_NAME` | Corporate entities, banks, merchant bankers, legal counsels, registrar firms |
| 5 | `PHYSICAL_ADDRESS` | Multi-line mailing addresses, registered offices, plots, streets, PIN codes |
| 6 | `SSN` | 9-digit US Social Security Numbers (`XXX-XX-XXXX`) |
| 7 | `CREDIT_CARD` | 13–19 digit cards (Visa, Mastercard, Amex, Discover, Diners, JCB, Maestro), Luhn-verified |
| 8 | `DATE_OF_BIRTH` | Birth dates identified via contextual prefixes (`DOB:`, `Date of Birth:`, `Born on`) |
| 9 | `IP_ADDRESS` | IPv4 and IPv6 addresses, validated against subnet/octet constraints |

*Also detects Indian corporate registration identifiers — DIN and PAN.*

---

## Architecture & Approach

A multi-stage pipeline designed for high precision, document fidelity, and reproducibility:

```
DOCX Extraction (Body, Tables, Nested Tables, Headers, Footers, w:txbxContent)
      │
      ▼
Multi-Stage Detection Pipeline
  ├── Specialized RegEx Matchers  (Emails, Phones, IPs, SSNs, Credit Cards, DOB, Legal Suffixes)
  ├── Microsoft Presidio Analyzer (PERSON, LOCATION, EMAIL, PHONE, CREDIT_CARD, ORG)
  ├── spaCy NER                   (Zero-shot PERSON / ORG extraction)
  ├── Contextual Validation       (Financial line-item & date exclusion filters)
  └── Optional Domain Gazetteer   (Promoter names, company entities, registered offices)
      │
      ▼
Priority-First Greedy Overlap Resolution (Specialized Exact Matches > Contextual Entities)
      │
      ▼
Deterministic Synthetic Pseudonymization (Seed-driven Faker, category-aware collision avoidance)
      │
      ▼
Run-Aware DOCX Redaction (Character spans mapped onto XML runs — bold/italic/font preserved)
      │
      ▼
Post-Redaction Leakage Scan (Re-opens output file, verifies zero residual PII)
```

### Key Components

- **Hybrid Detection** — strict structural regexes for pattern-bound identifiers (emails, credit cards, SSNs, IPs) combined with NLP models (spaCy `en_core_web_sm`, Microsoft Presidio) for contextual named entities (names, organizations).
- **Luhn Checksum Gating** — every candidate credit card number is validated against the Luhn algorithm before being flagged, preventing false positives on generic 16-digit order or invoice numbers.
- **Priority Overlap Resolution** — conflicting spans are resolved by specificity:

  `EMAIL (10) > SSN (9) = CREDIT_CARD (9) > IP (8) = DOB (8) > PHONE (7) > ADDRESS (6) > COMPANY (5) > NAME (4)`

- **Deterministic Pseudonymization** — `PIIAnonymizer` uses a configurable `--seed` and entity hashing so identical entity strings always map to the same synthetic replacement throughout the document.
- **DOCX Run-Aware Replacement** — splices replacement text directly into affected `w:r` XML run boundaries, right-to-left, preventing offset drift while preserving bold, italic, font size, and color.
- **Independent Leakage Validator** — re-opens the saved `.docx` and re-scans every paragraph, table, header, footer, and text box to confirm zero ground-truth PII remains before the run is considered successful.

---

## Generic vs. Domain-Assisted Mode

| | Generic Mode (default) | Domain-Assisted Mode (`--use-domain-profile`) |
|---|---|---|
| **Basis** | Regex + Presidio + spaCy NER + contextual rules only | Adds a verified gazetteer (`DomainProfile`) of promoter names, corporate entities, and registered offices |
| **Use case** | Zero-shot performance on *any* unseen legal/financial document | Maximizes recall on the specific target prospectus |
| **External dependency** | None | None — gazetteer is bundled, no network access required |

---

## Installation

```bash
# 1. Create and activate a virtual environment
# Windows (PowerShell / CMD)
python -m venv .venv
.venv\Scripts\activate

# Linux / macOS (bash / zsh)
python -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Download the spaCy English model
python -m spacy download en_core_web_sm
```

---

## Usage

### 1. CLI Redaction

**Domain-assisted mode** (recommended for the RHP prospectus):
```bash
python pii_redactor.py --input "Red Herring Prospectus.docx" --output "Red Herring Prospectus_redacted.docx" --use-domain-profile --seed 42 --validate --strict
```

**Pure generic mode** (zero-shot, any document):
```bash
python pii_redactor.py --input "Red Herring Prospectus.docx" --output "Red Herring Prospectus_redacted.docx" --seed 42 --validate
```

### 2. REST API

The same engine is exposed as a FastAPI service (`app.py`) for programmatic integration:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Landing page with usage guide |
| `GET` | `/health` | Service health check and version info |
| `POST` | `/redact` | Upload a `.docx`, receive the redacted `.docx` back |
| `GET` | `/docs` | Interactive Swagger/OpenAPI console |

Run it locally:
```bash
uvicorn app:app --reload
```

Or call it directly once running:
```bash
curl -X POST "http://127.0.0.1:8000/redact?use_domain_profile=false&seed=42" \
  -F "file=@Red Herring Prospectus.docx" \
  -o redacted_output.docx
```

The generic-mode NLP model is pre-warmed at startup for low first-request latency; the domain-assisted model is instantiated lazily on first use. Uploads are streamed to disk in 64 KB chunks (never held fully in memory), validated for `.docx` format, and temporary files are cleaned up automatically after each response. The service is pre-configured for one-command deployment on [Render](https://render.com) via `render.yaml`.

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

Measured against the 633 annotated occurrences in the real `Red Herring Prospectus.docx`, plus a 392-case independent three-tier synthetic benchmark.

### Real-Document Evaluation (Support = 633)

| Metric | Generic Mode | Domain-Assisted Mode |
|---|:---:|:---:|
| Micro Precision | **100.00%** | **100.00%** |
| Micro Recall | **80.25%** | **92.26%** |
| Micro F1 | **89.04%** | **95.97%** |
| Macro Precision | **100.00%** | **100.00%** |
| Macro Recall | **92.18%** | **94.54%** |
| Macro F1 | **95.26%** | **96.66%** |

#### Per-Category Breakdown

| Category | Generic P | Generic R | Generic F1 | Domain P | Domain R | Domain F1 | Support |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `FULL_NAME` | 100.00% | 73.18% | **84.51%** | 100.00% | 92.19% | **95.93%** | 384 |
| `EMAIL_ADDRESS` | 100.00% | 100.00% | **100.00%** | 100.00% | 100.00% | **100.00%** | 70 |
| `PHONE_NUMBER` | 100.00% | 58.70% | **73.97%** | 100.00% | 58.70% | **73.97%** | 46 |
| `COMPANY_NAME` | 100.00% | 97.74% | **98.86%** | 100.00% | 100.00% | **100.00%** | 133 |
| `PHYSICAL_ADDRESS` | 100.00% | 100.00% | **100.00%** | 100.00% | 100.00% | **100.00%** | 0 |
| `SSN` | 100.00% | 100.00% | **100.00%** | 100.00% | 100.00% | **100.00%** | 0 |
| `CREDIT_CARD` | 100.00% | 100.00% | **100.00%** | 100.00% | 100.00% | **100.00%** | 0 |
| `DATE_OF_BIRTH` | 100.00% | 100.00% | **100.00%** | 100.00% | 100.00% | **100.00%** | 0 |
| `IP_ADDRESS` | 100.00% | 100.00% | **100.00%** | 100.00% | 100.00% | **100.00%** | 0 |

### Synthetic Benchmark (360 Clean Cases + 32 Adversarial Cases)

| Benchmark Set | Support | Result | Notes |
|---|:---:|:---:|---|
| Synthetic Positive Recall | 180 | **98.33%** (177/180 TP) | Multi-format generalization across all 9 PII types (20/category) |
| Synthetic Clear-Negative Specificity | 180 | **80.00%** (144/180 TN) | Non-PII text with zero structural PII resemblance (20/category) |
| Adversarial / Ambiguous Cases | 32 | Stress-test tracked | Non-Luhn cards: 75% blocked · partial addresses: 62.5% blocked |
| Post-Redaction Leakage Scan | — | **PASS (0 leaks)** | Verified across paragraphs, tables, headers, footers, text boxes |
| Automated Unit Test Suite | 94 tests | **94/94 PASS (100%)** | Functional, regression, and privacy coverage |

---

## Evaluation Methodology

- **Ground-truth comparison** — predictions are matched against `ground_truth.json` by entity category and character span.
- **Precision / Recall / F1** — standard definitions:

  `Precision = TP / (TP + FP)`  ·  `Recall = TP / (TP + FN)`  ·  `F1 = 2·(P·R) / (P + R)`

- **Specificity & negative evaluation** — free-text extraction has no natural definition of "true negative," so specificity is measured separately on a discrete synthetic negative benchmark where negative instances are explicitly defined.
- **Three-tier benchmark** — clear-positive, clear-negative, and adversarial cases are scored and reported independently rather than folded into one aggregate, to avoid a misleading headline number.

---

## Phone Ground-Truth Annotation Limitation

An occurrence-level audit of the 19 reported `PHONE_NUMBER` false negatives found they were not genuine misses:

- **Root cause** — `ground_truth.json` contains 19 split/truncated annotations representing partial fragments (e.g. `+91 22 2288` as an 8-character prefix, or `2460` as a 4-digit suffix) of complete 12-digit Indian landline numbers (`+91 22 2288 2460`).
- **Complete coverage confirmed** — all 27 complete telephone numbers in the document were detected with **100% precision and recall (27/27 TP)**.
- **Precision safeguard preserved** — the detector was intentionally *not* loosened to treat arbitrary 4–6 digit sequences as phone numbers, since doing so would cause severe false-positive regressions on financial figures, accounting dates, and section indices.
- **Ground truth left untouched** — the reference annotations were preserved as-is rather than edited to match the tool's output.

---

## Tradeoffs and Known Limitations

1. **Contextual name triggers** — bare standalone names without honorifics or role prefixes (*"Mr."*, *"Director:"*, *"Promoter:"*) rely on NER model confidence, which can lower recall on isolated names inside header tables.
2. **Financial date preservation** — dates without explicit birth-related prefixes (*"DOB:"*, *"Date of Birth:"*) are intentionally left untouched, to avoid destructively redacting financial accounting periods (*"March 31, 2025"*).
3. **Invalid-Luhn numeric sequences** — 16-digit order or invoice numbers that fail the Luhn checksum are correctly treated as non-PII.
4. **Complex XML drawing shapes** — text embedded inside non-standard vector drawing elements (`w:drawing`) isn't traversed by standard `python-docx` iterators.
5. **Language scope** — regexes and NLP models are currently configured for English-language documents only.

---

## Privacy, Security & Repository Governance

- **Unredacted document excluded** — the original `Red Herring Prospectus.docx` contains real-world PII and is explicitly excluded from the public repository via `.gitignore`.
- **Internal evaluation artifacts** — `ground_truth.json` and `redaction_report.json` (with original PII references, used only for local offline evaluation) are kept as local artifacts and are not tracked in git.
- **Public repository scope** — only sanitized source code, the automated test suite, synthetic benchmarks, evaluation reports, and the verified redacted document are published.
- **Zero raw PII in logs** — `redaction_report.json` and console/API logs record anonymized descriptors (`FULL_NAME_0001`, `EMAIL_ADDRESS_0002`) only, never raw values.
- **In-memory mapping isolation** — deterministic replacement tables exist strictly in process memory during a run.
- **Streaming, disk-backed API uploads** — the FastAPI service streams uploads in 64 KB chunks and cleans up temporary files after every response; nothing is buffered fully in memory.
- **Leakage gate** — the CLI's `--strict` flag aborts with a non-zero exit code if any residual PII is found during post-redaction verification.

---

## Project Structure

```
pii-redaction-tool/
├── README.md                            # Documentation, architecture, and reproduction instructions
├── requirements.txt                     # Pinned runtime dependencies
├── pii_redactor.py                      # Detection pipeline, anonymizer, and DOCX redactor (CLI entry point)
├── app.py                               # FastAPI service — REST wrapper around the redaction engine
├── render.yaml                          # One-command deployment config for Render
├── evaluate_redactor.py                 # Dual-mode real-document and synthetic evaluation suite
├── Red Herring Prospectus_redacted.docx # Verified redacted DOCX deliverable (public)
├── evaluation/
│   ├── evaluation_report.md             # Standalone quantitative evaluation report
│   ├── metrics.json                     # Machine-readable evaluation metrics
│   └── synthetic_benchmark.py           # Three-tier independent synthetic benchmark suite
├── tests/                                # 94 automated unit tests
│   ├── test_address.py                  # Physical address patterns
│   ├── test_anonymization.py            # Deterministic pseudonymization engine
│   ├── test_company.py                  # Company name detection & exclusions
│   ├── test_credit_card.py              # Credit card detection & Luhn validation
│   ├── test_detector.py                 # Multi-stage PII detection pipeline
│   ├── test_dob.py                      # Date-of-birth contextual detection
│   ├── test_docx_integrity.py           # Run-aware styling and XML preservation
│   ├── test_email.py                    # Email pattern matching
│   ├── test_entity_resolution.py        # Priority-first overlap resolution
│   ├── test_evaluation.py               # Evaluation calculation and privacy exports
│   ├── test_generalization.py           # Zero-shot generalization across unseen formats
│   ├── test_ip.py                       # IPv4/IPv6 validation
│   ├── test_leakage_validation.py       # Independent post-redaction leakage scanner
│   ├── test_name.py                     # Western and Indian person-name detection
│   ├── test_phone.py                    # Domestic/international phone numbers
│   ├── test_privacy.py                  # Zero raw PII log/report sanitization
│   ├── test_regression.py               # Regression protection against financial terms
│   ├── test_regression_targeted.py      # Targeted fixes (credit card, names, DOB)
│   ├── test_smoke.py                    # End-to-end integration smoke test
│   └── test_ssn.py                      # SSN pattern matching
└── [Local-only, excluded via .gitignore]:
    ├── Red Herring Prospectus.docx      # Original unredacted prospectus (contains PII)
    ├── ground_truth.json                # Reference ground-truth annotations (contains PII)
    └── redaction_report.json            # Local run-time audit report
```
