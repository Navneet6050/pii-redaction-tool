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

import logging
import os
import shutil
import sys
import tempfile
import zipfile
from contextlib import asynccontextmanager
from typing import Optional

from docx.opc.exceptions import PackageNotFoundError
from fastapi import FastAPI, File, UploadFile, Query, HTTPException, BackgroundTasks, status
from fastapi.responses import FileResponse

from pii_redactor import (
    PIIDetector,
    PIIAnonymizer,
    DocxRedactor,
    DomainProfile,
    __version__
)

# Configure sanitized logging (zero raw PII logged)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("PIIRedactionAPI")

# Global detector singletons (generic pre-warmed, domain lazily instantiated)
_generic_detector: Optional[PIIDetector] = None
_domain_detector: Optional[PIIDetector] = None


def cleanup_temp_files(*file_paths: str):
    """Safely removes temporary files from disk post-response."""
    for path in file_paths:
        try:
            if path and os.path.exists(path):
                os.remove(path)
        except Exception as e:
            logger.warning(f"Failed to remove temporary file {path}: {type(e).__name__}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Pre-warm generic NLP model at application startup to minimize memory and latency."""
    global _generic_detector, _domain_detector
    logger.info("Pre-warming generic PII Detector model...")
    _generic_detector = PIIDetector(method="hybrid", domain_profile=None)
    _domain_detector = None
    logger.info("Generic PII Detector model ready.")
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
    background_tasks: BackgroundTasks,
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
    and streams the redacted DOCX file back via disk-backed temporary storage.
    """
    # 1. Validate filename and extension
    filename = file.filename or ""
    if not filename.lower().endswith(".docx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only Microsoft Word (.docx) documents are supported."
        )

    # 2. Stream uploaded file directly to a temporary input file on disk
    temp_in = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
    temp_in_path = temp_in.name
    temp_out = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
    temp_out_path = temp_out.name

    try:
        try:
            # Stream in 64KB chunks to prevent holding complete file bytes in memory
            while chunk := await file.read(1024 * 64):
                temp_in.write(chunk)
        finally:
            temp_in.close()
            temp_out.close()

        # Check for empty file upload
        if os.path.getsize(temp_in_path) == 0:
            cleanup_temp_files(temp_in_path, temp_out_path)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The uploaded file is empty."
            )

        # 3. Select detector (generic pre-warmed, domain lazily instantiated)
        global _generic_detector, _domain_detector
        if use_domain_profile:
            if _domain_detector is None:
                logger.info("Lazily instantiating domain-assisted PII Detector...")
                _domain_detector = PIIDetector(
                    method="hybrid",
                    domain_profile=DomainProfile.get_rhp_default_profile()
                )
            detector = _domain_detector
        else:
            if _generic_detector is None:
                _generic_detector = PIIDetector(method="hybrid", domain_profile=None)
            detector = _generic_detector

        anonymizer = PIIAnonymizer(strategy="synthetic", seed=seed)
        redactor = DocxRedactor(detector=detector, anonymizer=anonymizer)

        # 4. Redact document directly from temporary input path to temporary output path
        try:
            redactor.redact_document(temp_in_path, temp_out_path)
        except (PackageNotFoundError, zipfile.BadZipFile, KeyError, ValueError) as e:
            logger.warning(f"Malformed DOCX package rejected: {type(e).__name__}")
            cleanup_temp_files(temp_in_path, temp_out_path)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The uploaded file is not a valid or readable .docx package."
            )
        except Exception as e:
            logger.error(f"Document redaction error: {type(e).__name__}")
            cleanup_temp_files(temp_in_path, temp_out_path)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred while processing the document."
            )

    except HTTPException:
        raise
    except Exception as e:
        cleanup_temp_files(temp_in_path, temp_out_path)
        logger.error(f"Unexpected API error: {type(e).__name__}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the document."
        )

    # 5. Schedule cleanup of temporary input and output files after response finishes
    background_tasks.add_task(cleanup_temp_files, temp_in_path, temp_out_path)

    # 6. Return the redacted document via FileResponse
    out_filename = f"redacted_{filename}" if filename else "redacted_document.docx"
    return FileResponse(
        path=temp_out_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=out_filename,
        background=background_tasks
    )
