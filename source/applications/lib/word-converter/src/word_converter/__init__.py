"""
office_to_pdf.py
Convert DOC/DOCX and PPT/PPTX files to PDF, then hand the PDF off to an
existing PDF-aware FileConverter.
"""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile
from typing import Final

from opentelemetry import trace

from core.result import Result
from domain.file_converter.interface import FileConverter
from domain.file_converter.model import Page

logger = logging.getLogger(__name__)


class OfficeToPDFConverter(FileConverter):
    """
    Converts modern/legacy Word and PowerPoint to PDF, then forwards the
    resulting PDF to *pdf_converter*.

    Supported extensions:
        * .doc  • .docx
        * .ppt  • .pptx
    """

    _pdf_converter: FileConverter
    tracer: trace.Tracer

    _SUPPORTED_EXTS: Final[set[str]] = {"doc", "docx", "ppt", "pptx"}

    def __init__(self, pdf_converter: FileConverter) -> None:
        # Make sure the delegate understands PDF
        assert pdf_converter.does_convert_filetype("pdf")

        self._pdf_converter = pdf_converter
        self.tracer = trace.get_tracer(__name__)
        super().__init__()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def does_convert_filetype(self, filetype: str) -> bool:  # noqa: D401
        """Return True iff *filetype* is doc/docx/ppt/pptx (case-insensitive)."""
        return filetype.lower() in self._SUPPORTED_EXTS

    def convert_file(self, file: str) -> Result[list[Page]]:
        """
        Convert *file* (must be one of the supported Office types) to PDF and
        then delegate to the injected PDF converter.
        """
        with self.tracer.start_as_current_span("office-to-pdf"):
            try:
                pdf_path = self._convert_to_pdf(file)
                return self._pdf_converter.convert_file(pdf_path)
            except Exception as exc:  # noqa: BLE001
                logger.error(exc.with_traceback(None))
                return Result.Err(exc)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _convert_to_pdf(self, file: str) -> str:
        """
        Use LibreOffice to turn *file* into a PDF:

            soffice --headless --convert-to pdf --outdir <tmp> <file>

        Returns the path to the generated PDF (lives in a temp dir that is
        cleaned up when the program exits). Any error is raised so the caller
        can wrap it in a Result.
        """
        if not os.path.exists(file):
            raise FileNotFoundError(f"File not found: {file}")

        ext = os.path.splitext(file)[1].lstrip(".").lower()
        if ext not in self._SUPPORTED_EXTS:
            raise ValueError(f"Unsupported file type: {ext}")

        tmp_dir = tempfile.mkdtemp()
        output_dir = os.path.join(tmp_dir, "loo_output")
        os.makedirs(output_dir, exist_ok=True)

        logger.debug("LibreOffice: %s ➜ pdf", ext)
        subprocess.run(
            [
                "soffice",
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                output_dir,
                file,
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Expect exactly one PDF with the same base name
        base = os.path.splitext(os.path.basename(file))[0]
        pdf_candidates = [
            f
            for f in os.listdir(output_dir)
            if f.startswith(base) and f.lower().endswith(".pdf")
        ]
        if not pdf_candidates:
            raise RuntimeError(f"LibreOffice failed to create a PDF for {file}")

        pdf_path = os.path.join(output_dir, pdf_candidates[0])
        logger.debug("Generated PDF at %s", pdf_path)
        return pdf_path
