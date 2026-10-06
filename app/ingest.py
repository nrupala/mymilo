# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Multi-format file ingestion: extract text, chunk it.

Adapted from nrupala/localragcoder ``engine/ingester.py`` (his repo, his
code — transfer, don't rebuild). Changes for MyMilo: AGPL headers,
``ingest_bytes`` entry point for HTTP uploads, and the same optional-
dependency discipline (missing parsers degrade with a clear error, never
silently).
"""

from __future__ import annotations

import csv
import io
import json
import logging
import re
import tempfile
import zipfile
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import fitz  # PyMuPDF

    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    import docx

    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

try:
    from bs4 import BeautifulSoup

    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

try:
    import markdown

    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False


class IngestionError(Exception):
    """Raised when a file cannot be ingested. Always explicit."""


EXTENSION_MAP = {
    ".pdf": "pdf",
    ".txt": "txt",
    ".md": "md",
    ".markdown": "md",
    ".html": "html",
    ".htm": "html",
    ".json": "json",
    ".csv": "csv",
    ".tsv": "csv",
    ".docx": "docx",
    ".doc": "doc",
    ".odt": "odt",
    ".rtf": "rtf",
    ".xml": "xml",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".log": "txt",
    ".cfg": "txt",
    ".ini": "txt",
    ".conf": "txt",
    ".py": "txt",
    ".js": "txt",
    ".ts": "txt",
    ".jsx": "txt",
    ".tsx": "txt",
    ".java": "txt",
    ".c": "txt",
    ".cpp": "txt",
    ".h": "txt",
    ".rs": "txt",
    ".go": "txt",
    ".rb": "txt",
    ".php": "txt",
    ".sql": "txt",
    ".sh": "txt",
    ".bat": "txt",
    ".ps1": "txt",
}


def detect_filetype(filename: str) -> str:
    """Detect file type by extension. Defaults to "txt"."""
    ext = Path(filename).suffix.lower()
    return EXTENSION_MAP.get(ext, "txt")


def _extract_txt_bytes(raw: bytes) -> str:
    return raw.decode("utf-8", errors="replace")


def _extract_md_bytes(raw: bytes) -> str:
    text = raw.decode("utf-8", errors="replace")
    if MARKDOWN_AVAILABLE and BS4_AVAILABLE:
        html = markdown.markdown(text)
        return BeautifulSoup(html, "html.parser").get_text()
    return text


def _extract_html_bytes(raw: bytes) -> str:
    text = raw.decode("utf-8", errors="replace")
    if BS4_AVAILABLE:
        soup = BeautifulSoup(text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        return soup.get_text(separator="\n", strip=True)
    return re.sub(r"<[^>]+>", " ", text)


def _extract_json_bytes(raw: bytes) -> str:
    data = json.loads(raw.decode("utf-8", errors="replace"))
    return json.dumps(data, indent=2, default=str)


def _extract_csv_bytes(raw: bytes) -> str:
    reader = csv.reader(io.StringIO(raw.decode("utf-8", errors="replace")))
    return "\n".join(" | ".join(row) for row in reader)


def _extract_docx_bytes(raw: bytes) -> str:
    if not DOCX_AVAILABLE:
        raise IngestionError(
            "python-docx is not installed — pip install -e '.[rag]' for "
            "DOCX support, or upload as plain text."
        )
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=True) as tmp:
        tmp.write(raw)
        tmp.flush()
        doc = docx.Document(tmp.name)
    paragraphs = [p.text for p in doc.paragraphs]
    for table in doc.tables:
        for row in table.rows:
            paragraphs.append(" | ".join(cell.text for cell in row.cells))
    return "\n".join(paragraphs)


def _extract_pdf_bytes(raw: bytes) -> str:
    if not PYMUPDF_AVAILABLE:
        raise IngestionError(
            "PyMuPDF is not installed — pip install -e '.[rag]' for PDF "
            "support, or upload as plain text."
        )
    doc = fitz.open(stream=raw, filetype="pdf")
    pages = [page.get_text() for page in doc]
    doc.close()
    return "\n".join(pages)


def _extract_odt_bytes(raw: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(raw), "r") as z:
            if "content.xml" not in z.namelist():
                raise IngestionError("Invalid ODT file: missing content.xml")
            xml_data = z.read("content.xml").decode("utf-8", errors="replace")
    except zipfile.BadZipFile:
        raise IngestionError("Invalid ODT file (not a zip archive)") from None
    if BS4_AVAILABLE:
        return BeautifulSoup(xml_data, "xml").get_text(separator="\n", strip=True)
    return re.sub(r"<[^>]+>", " ", xml_data)


def _extract_rtf_bytes(raw: bytes) -> str:
    text = raw.decode("utf-8", errors="replace")
    text = re.sub(r"\\([a-z]+)(-?\d+)?", " ", text)
    text = re.sub(r"[{}]", " ", text)
    text = re.sub(r"\\'[0-9a-f]{2}", " ", text)
    return re.sub(r"\s+", " ", text).strip()


EXTRACTORS = {
    "txt": _extract_txt_bytes,
    "md": _extract_md_bytes,
    "html": _extract_html_bytes,
    "htm": _extract_html_bytes,
    "json": _extract_json_bytes,
    "csv": _extract_csv_bytes,
    "tsv": _extract_csv_bytes,
    "docx": _extract_docx_bytes,
    "doc": _extract_docx_bytes,
    "pdf": _extract_pdf_bytes,
    "odt": _extract_odt_bytes,
    "rtf": _extract_rtf_bytes,
}


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 64) -> list[str]:
    """Split text into overlapping chunks by word count."""
    words = text.split()
    if len(words) <= chunk_size:
        return [text]
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start += chunk_size - overlap
    return chunks


def ingest_bytes(
    raw: bytes,
    filename: str,
    chunk_size: int = 512,
    overlap: int = 64,
    filetype: str | None = None,
) -> dict:
    """Ingest an in-memory file (e.g. from an HTTP upload).

    Returns dict with filename, filetype, size_bytes, text, chunks,
    chunk_count. Raises IngestionError on failure — never silently.
    """
    if not raw:
        raise IngestionError(f"Empty file: {filename}")
    ft = (filetype or detect_filetype(filename)).lower().lstrip(".")
    extractor = EXTRACTORS.get(ft)
    if extractor is None:
        raise IngestionError(f"Unsupported file type: {ft}")
    logger.info("Extracting text from %s (%s)", filename, ft)
    text = extractor(raw)
    if not text.strip():
        raise IngestionError(f"No extractable text in {filename}")
    chunks = chunk_text(text, chunk_size, overlap)
    return {
        "filename": filename,
        "filetype": ft,
        "size_bytes": len(raw),
        "text": text,
        "chunks": chunks,
        "chunk_count": len(chunks),
    }
