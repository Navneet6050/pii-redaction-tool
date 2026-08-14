#!/usr/bin/env python3
"""
===============================================================================
PII Redaction Service — Cloud HTTP API (FastAPI)
===============================================================================
Production-grade HTTP API wrapper for the PII Redaction and Anonymization Engine.
Exposes:
  - GET  /       : Service landing page with interactive documentation guide
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
from fastapi.responses import FileResponse, HTMLResponse

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
    "/",
    response_class=HTMLResponse,
    summary="Landing Page",
    tags=["System"]
)
async def root_landing_page():
    """Serves a self-contained, professional landing page with usage instructions."""
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>PII Redaction Service</title>
  <style>
    :root {{
      --bg: #0f172a;
      --card-bg: #1e293b;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --primary: #38bdf8;
      --primary-hover: #0ea5e9;
      --success: #22c55e;
      --border: #334155;
      --code-bg: #090d16;
    }}
    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background-color: var(--bg);
      color: var(--text);
      line-height: 1.6;
      padding: 2rem 1rem;
      min-height: 100vh;
      display: flex;
      justify-content: center;
      align-items: center;
    }}
    .container {{
      max-width: 780px;
      width: 100%;
      background-color: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 2.5rem;
      box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.5);
    }}
    .header {{
      border-bottom: 1px solid var(--border);
      padding-bottom: 1.5rem;
      margin-bottom: 1.5rem;
    }}
    .title-row {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 0.75rem;
      margin-bottom: 0.5rem;
    }}
    h1 {{
      font-size: 1.875rem;
      font-weight: 700;
      color: var(--text);
      letter-spacing: -0.025em;
    }}
    .badges {{
      display: flex;
      gap: 0.5rem;
      align-items: center;
    }}
    .badge {{
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
      font-size: 0.75rem;
      font-weight: 600;
      padding: 0.25rem 0.65rem;
      border-radius: 9999px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}
    .badge-status {{
      background-color: rgba(34, 197, 94, 0.15);
      color: var(--success);
      border: 1px solid rgba(34, 197, 94, 0.3);
    }}
    .badge-status::before {{
      content: "";
      display: inline-block;
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background-color: var(--success);
    }}
    .badge-version {{
      background-color: rgba(56, 189, 248, 0.15);
      color: var(--primary);
      border: 1px solid rgba(56, 189, 248, 0.3);
    }}
    .subtitle {{
      color: var(--text-muted);
      font-size: 1rem;
      margin-top: 0.25rem;
    }}
    .section {{
      margin-bottom: 2rem;
    }}
    .section-title {{
      font-size: 1.125rem;
      font-weight: 600;
      margin-bottom: 0.75rem;
      color: var(--text);
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }}
    .endpoint-list {{
      list-style: none;
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
    }}
    .endpoint-item {{
      background-color: var(--code-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 0.75rem 1rem;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 0.5rem;
    }}
    .endpoint-route {{
      display: flex;
      align-items: center;
      gap: 0.6rem;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 0.875rem;
    }}
    .method {{
      font-weight: 700;
      font-size: 0.75rem;
      padding: 0.15rem 0.45rem;
      border-radius: 4px;
    }}
    .method-get {{
      background-color: #0284c7;
      color: #ffffff;
    }}
    .method-post {{
      background-color: #16a34a;
      color: #ffffff;
    }}
    .endpoint-desc {{
      color: var(--text-muted);
      font-size: 0.875rem;
    }}
    .steps-list {{
      padding-left: 1.25rem;
      color: var(--text-muted);
      font-size: 0.925rem;
    }}
    .steps-list li {{
      margin-bottom: 0.4rem;
    }}
    .steps-list strong {{
      color: var(--text);
    }}
    .cta-container {{
      margin: 1.5rem 0 2rem 0;
      display: flex;
      justify-content: center;
    }}
    .btn {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 0.5rem;
      background-color: var(--primary);
      color: #0f172a;
      font-weight: 700;
      font-size: 1rem;
      padding: 0.85rem 1.75rem;
      border-radius: 8px;
      text-decoration: none;
      transition: background-color 0.15s ease, transform 0.1s ease;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
    }}
    .btn:hover {{
      background-color: var(--primary-hover);
      transform: translateY(-1px);
    }}
    .note-box {{
      background-color: rgba(56, 189, 248, 0.08);
      border-left: 4px solid var(--primary);
      padding: 0.75rem 1rem;
      border-radius: 0 6px 6px 0;
      font-size: 0.875rem;
      color: var(--text-muted);
    }}
    .note-box strong {{
      color: var(--primary);
    }}
    .footer {{
      margin-top: 1.5rem;
      padding-top: 1rem;
      border-top: 1px solid var(--border);
      text-align: center;
      font-size: 0.8rem;
      color: var(--text-muted);
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="title-row">
        <h1>PII Redaction Service</h1>
        <div class="badges">
          <span class="badge badge-status">Service: Healthy</span>
          <span class="badge badge-version">v{__version__}</span>
        </div>
      </div>
      <p class="subtitle">
        High-precision Personally Identifiable Information (PII) detection and deterministic pseudonymization engine for Microsoft Word (<code>.docx</code>) documents.
      </p>
    </div>

    <div class="cta-container">
      <a href="/docs" class="btn" id="btn-docs">
        <span>Open Interactive API Docs</span>
        <span aria-hidden="true">&rarr;</span>
      </a>
    </div>

    <div class="section">
      <div class="section-title">Available Endpoints</div>
      <ul class="endpoint-list">
        <li class="endpoint-item">
          <div class="endpoint-route">
            <span class="method method-get">GET</span>
            <code>/health</code>
          </div>
          <span class="endpoint-desc">Service health check and operational status</span>
        </li>
        <li class="endpoint-item">
          <div class="endpoint-route">
            <span class="method method-post">POST</span>
            <code>/redact</code>
          </div>
          <span class="endpoint-desc">Upload a DOCX file and receive a redacted DOCX</span>
        </li>
        <li class="endpoint-item">
          <div class="endpoint-route">
            <span class="method method-get">GET</span>
            <code>/docs</code>
          </div>
          <span class="endpoint-desc">Interactive Swagger OpenAPI documentation & test console</span>
        </li>
      </ul>
    </div>

    <div class="section">
      <div class="section-title">How to Test via Web Console</div>
      <ol class="steps-list">
        <li>Click <strong>Open Interactive API Docs</strong> above (or navigate to <code>/docs</code>).</li>
        <li>Expand the <strong>POST /redact</strong> endpoint.</li>
        <li>Click the <strong>Try it out</strong> button in Swagger UI.</li>
        <li>Upload a <strong>.docx</strong> file using the file selector.</li>
        <li>Click <strong>Execute</strong> to process the document.</li>
        <li>Download the returned redacted Word document directly from the response.</li>
      </ol>
    </div>

    <div class="note-box">
      <strong>Supported Format:</strong> Only Microsoft Word (<code>.docx</code>) documents are supported. Non-DOCX files and empty payloads will be rejected safely with HTTP 400.
    </div>

    <div class="footer">
      PII Redaction Service &bull; Zero Raw PII Retention &bull; In-Memory & Temp-Stream Safe
    </div>
  </div>
</body>
</html>"""
    return HTMLResponse(content=html_content, status_code=status.HTTP_200_OK)


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
