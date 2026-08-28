"""OCR Provider Abstraction and Implementations for MediGen AI.

Phase 8.8: Pluggable OCR Subsystem for Scanned/Image Medical Documents.

Architecture:
    BaseOCRProvider        (abstract interface)
    ├── MockOCRProvider    (deterministic, offline, test-friendly)
    └── TextractOCRProvider (AWS Textract cloud OCR adapter)

Design principles:
- Scanned/image-only PDFs are routed to OCR when OCR is enabled (OCR_ENABLED=True).
- Preserves multi-page boundaries, page numbers, and clinical metadata.
- Zero PHI leaking into operational logs.
- Extracted text continues seamlessly into the standard cleaning, chunking, and embedding pipeline.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import logging
from typing import Any, Callable, Optional

from pypdf import PdfReader

from app.ai.extractors import ExtractedDocument

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Abstract Base
# ---------------------------------------------------------------------------


class BaseOCRProvider(ABC):
    """Abstract interface for Optical Character Recognition providers."""

    @abstractmethod
    def extract_text(
        self,
        file_path: str,
        file_extension: str,
    ) -> ExtractedDocument:
        """Perform OCR on a physical document file.

        Args:
            file_path: Absolute path to the document on disk.
            file_extension: Normalized file extension (e.g. '.pdf', '.png', '.jpg').

        Returns:
            ExtractedDocument containing ordered, page-indexed contents.
        """


# ---------------------------------------------------------------------------
# Mock OCR Provider (Deterministic & Offline)
# ---------------------------------------------------------------------------


class MockOCRProvider(BaseOCRProvider):
    """Deterministic Mock OCR provider for unit testing and offline development.

    Behavior:
    1. For PDFs: Inspects embedded metadata and pages for simulated scanned text.
    2. If text was embedded in metadata (e.g. /Subject or /Title), extracts and attributes to pages.
    3. If custom_handler is provided, delegates to custom_handler for targeted test assertions.
    4. Otherwise, generates deterministic page-indexed clinical text based on document properties.
    """

    def __init__(
        self,
        custom_handler: Optional[Callable[[str, str], ExtractedDocument]] = None,
    ) -> None:
        self._custom_handler = custom_handler

    def extract_text(
        self,
        file_path: str,
        file_extension: str,
    ) -> ExtractedDocument:
        """Extract text deterministically from simulated scanned documents."""
        if self._custom_handler is not None:
            return self._custom_handler(file_path, file_extension)

        ext = file_extension.lower().strip()
        pages: list[tuple[int, str]] = []
        full_text_parts: list[str] = []

        if ext == ".pdf":
            try:
                reader = PdfReader(file_path)
                page_count = max(1, len(reader.pages))

                # Check if PDF metadata has simulated text
                metadata_text = ""
                if reader.metadata:
                    metadata_text = str(
                        reader.metadata.get("/Subject") or reader.metadata.get("/Title") or ""
                    ).strip()

                for page_idx in range(page_count):
                    page_num = page_idx + 1
                    p_text = reader.pages[page_idx].extract_text() or ""
                    if not p_text.strip() and metadata_text:
                        p_text = f"SCANNED PAGE {page_num} OCR EXTRACT:\n{metadata_text}"
                    elif not p_text.strip():
                        p_text = f"SCANNED CLINICAL RECORD [PAGE {page_num}]: Patient medical history and vital signs recorded via OCR scan."

                    pages.append((page_num, p_text.strip()))
                    full_text_parts.append(p_text.strip())
            except Exception as exc:
                logger.error("MockOCRProvider failed to read PDF: %s", type(exc).__name__)
                raise ValueError(f"Mock OCR extraction failed for PDF: {exc}") from exc
        else:
            p_text = "SCANNED DOCUMENT OCR EXTRACT: Clinical findings and diagnostic report."
            pages.append((1, p_text))
            full_text_parts.append(p_text)

        full_text = "\n\n".join(full_text_parts).strip()
        return ExtractedDocument(
            text=full_text,
            page_count=len(pages),
            pages=pages,
            metadata={"format": ext, "ocr": True, "ocr_provider": "mock"},
        )


# ---------------------------------------------------------------------------
# AWS Textract OCR Provider (Cloud-Safe Adapter)
# ---------------------------------------------------------------------------


class TextractOCRProvider(BaseOCRProvider):
    """Production cloud OCR adapter utilizing AWS Textract."""

    def __init__(
        self,
        region_name: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
    ) -> None:
        from app.core.config import settings

        self.region_name = region_name or settings.AWS_REGION
        self.aws_access_key_id = aws_access_key_id or settings.AWS_ACCESS_KEY_ID
        self.aws_secret_access_key = aws_secret_access_key or settings.AWS_SECRET_ACCESS_KEY
        self._client = None

    def _get_client(self) -> Any:
        """Instantiate boto3 Textract client."""
        if self._client is not None:
            return self._client

        import boto3

        client_kwargs: dict[str, Any] = {"region_name": self.region_name}
        if self.aws_access_key_id and self.aws_secret_access_key:
            client_kwargs["aws_access_key_id"] = self.aws_access_key_id
            client_kwargs["aws_secret_access_key"] = self.aws_secret_access_key

        self._client = boto3.client("textract", **client_kwargs)
        return self._client

    def extract_text(
        self,
        file_path: str,
        file_extension: str,
    ) -> ExtractedDocument:
        """Execute OCR extraction via AWS Textract API."""
        try:
            with open(file_path, "rb") as f:
                file_bytes = f.read()

            client = self._get_client()
            response = client.detect_document_text(Document={"Bytes": file_bytes})

            # Parse lines from Textract response
            lines = [
                item["Text"]
                for item in response.get("Blocks", [])
                if item.get("BlockType") == "LINE" and "Text" in item
            ]
            full_text = "\n".join(lines).strip()

            if not full_text:
                raise ValueError("AWS Textract detected no text in document.")

            return ExtractedDocument(
                text=full_text,
                page_count=1,
                pages=[(1, full_text)],
                metadata={"format": file_extension, "ocr": True, "ocr_provider": "textract"},
            )
        except Exception as exc:
            logger.error("AWS Textract OCR failed: %s", type(exc).__name__)
            raise RuntimeError(f"AWS Textract OCR extraction failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Factory Function
# ---------------------------------------------------------------------------


def get_ocr_provider(provider: Optional[str] = None) -> BaseOCRProvider:
    """Instantiate the configured OCR provider.

    Args:
        provider: Provider name (defaults to settings.OCR_PROVIDER or 'mock').

    Returns:
        Instance of BaseOCRProvider.
    """
    from app.core.config import settings

    prov = (provider or settings.OCR_PROVIDER).strip().lower()

    if prov == "mock":
        return MockOCRProvider()

    if prov in ("textract", "aws_textract", "aws"):
        return TextractOCRProvider()

    raise ValueError(
        f"Unsupported OCR provider '{provider}'. Supported providers: 'mock', 'textract'."
    )
