#!/usr/bin/env python3
"""
===============================================================================
PII Redaction Service — Cloud HTTP API (FastAPI)
===============================================================================
Production-grade HTTP API wrapper for the PII Redaction and Anonymization Engine.
Exposes:
  - GET  /health : Service health check and version info
  - POST /redact : Multipart/form-data DOCX file upload returning redacted DOCX
===============================================================================
"""

import io
import logging
import sys
from contextlib import asynccontextmanager
from typing import Optional

import docx
from docx.opc.exceptions import PackageNotFoundError
from fastapi import FastAPI, File, UploadFile, Query, HTTPException, status
from fastapi.responses import StreamingResponse

from pii_redactor import (
    PIIDetector,
    PIIAnonymizer,
    DocxRedactor,
    DomainProfile,
    __version__
)

# Configure sanitized logging (no PII logged)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("PIIRedactionAPI")

# Global pre-warmed detector singletons
_generic_detector: Optional[PIIDetector] = None
_domain_detector: Optional[PIIDetector] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Pre-warm NLP models at application startup to minimize per-request latency."""
    global _generic_detector, _domain_detector
    logger.info("Initializing pre-warmed PII Detector models...")
    _generic_detector = PIIDetector(method="hybrid", domain_profile=None)
    _domain_detector = PIIDetector(
        method="hybrid",
        domain_profile=DomainProfile.get_rhp_default_profile()
    )
    logger.info("PII Detector models ready.")
    yield
    logger.info("Shutting down PII Redaction API.")


app = FastAPI(
    title="PII Redaction Service",
    description="High-precision PII detection and deterministic pseudonymization for DOCX files.",
    version=__version__,
    lifespan=lifespan
)


@app.get(
    "/health",
    summary="Health Check",
    tags=["System"]
)
async def health_check():
    """Returns the operational health and version metadata of the service."""
    return {
        "status": "healthy",
        "service": "pii-redaction-service",
        "version": __version__
    }


@app.post(
    "/redact",
    summary="Redact DOCX Document",
    tags=["Redaction"],
    responses={
        200: {
            "description": "Redacted Microsoft Word document (.docx)",
            "content": {
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {}
            }
        },
        400: {"description": "Invalid file upload or corrupted document"},
        415: {"description": "Unsupported media type"},
        500: {"description": "Internal document processing error"}
    }
)
async def redact_docx(
    file: UploadFile = File(..., description="Microsoft Word document (.docx) to redact"),
    use_domain_profile: bool = Query(
        False,
        description="Enable domain-specific gazetteer knowledge (default: False for generic detection)"
    ),
    seed: int = Query(
        42,
        description="Random seed for deterministic pseudonymization"
    )
):
    """
    Accepts a DOCX file upload, processes it using the PII Redactor engine,
    and streams the redacted DOCX file back in-memory.
    """
    # 1. Validate filename and extension
    filename = file.filename or ""
    if not filename.lower().endswith(".docx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only Microsoft Word (.docx) documents are supported."
        )

    # 2. Read file bytes into memory
    try:
        file_bytes = await file.read()
    except Exception as e:
        logger.error(f"Failed to read uploaded file: {type(e).__name__}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to read the uploaded file stream."
        )

    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty."
        )

    # 3. Validate DOCX XML package integrity
    in_stream = io.BytesIO(file_bytes)
    try:
        _ = docx.Document(in_stream)
        in_stream.seek(0)
    except (PackageNotFoundError, Exception) as e:
        logger.warning(f"Malformed DOCX package rejected: {type(e).__name__}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is not a valid or readable .docx package."
        )

    # 4. Select pre-warmed detector and initialize redactor
    try:
        global _generic_detector, _domain_detector
        if use_domain_profile:
            detector = _domain_detector or PIIDetector(
                method="hybrid",
                domain_profile=DomainProfile.get_rhp_default_profile()
            )
        else:
            detector = _generic_detector or PIIDetector(method="hybrid", domain_profile=None)

        anonymizer = PIIAnonymizer(strategy="synthetic", seed=seed)
        redactor = DocxRedactor(detector=detector, anonymizer=anonymizer)

        # 5. Process redaction directly to in-memory output stream
        out_stream = io.BytesIO()
        redactor.redact_document(in_stream, out_stream)
        out_stream.seek(0)

    except Exception as e:
        logger.error(f"Document redaction error: {type(e).__name__}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the document."
        )

    # 6. Stream back the redacted document
    out_filename = f"redacted_{filename}" if filename else "redacted_document.docx"
    return StreamingResponse(
        out_stream,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f'attachment; filename="{out_filename}"'
        }
    )
