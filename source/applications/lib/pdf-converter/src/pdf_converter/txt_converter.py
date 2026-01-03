"""
SimpleTXTConverter
──────────────────
• No Marker imports – reads plain-text as-is.
• Assumes: entire TXT file fits into memory; no pagination.
• Produces: List[Page] containing **one** TextFragement (no tables or images).
"""

from __future__ import annotations

import logging
from pathlib import Path

from core.string_handler import to_str
from opentelemetry import trace

from core.result import Result
from domain.file_converter.interface import FileConverter
from domain.file_converter.model import Page, TextFragement

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
#  Converter
# --------------------------------------------------------------------------- #
class SimpleTXTConverter(FileConverter):
    """
    Minimal converter that wraps a .txt file into a single Page/TextFragement.
    """

    def __init__(self) -> None:
        super().__init__()
        self.tracer: trace.Tracer = trace.get_tracer("SimpleTXTConverter")

    # -------- File-type check -------------------------------------------------
    def does_convert_filetype(self, filetype: str) -> bool:  # noqa: D401
        return filetype.lower() in ["txt", "text"]

    # -------- Public entry point --------------------------------------------
    def convert_file(self, file: str) -> Result[list[Page]]:
        try:
            pages = self._wrap_file_as_fragment(file)
            return Result.Ok(pages)
        except Exception as exc:
            logger.error(exc, exc_info=True)
            return Result.Err(exc)

    # -------- Internal helper -----------------------------------------------
    def _wrap_file_as_fragment(self, file: str) -> list[Page]:
        """
        Read entire TXT → single TextFragement → single Page.
        """
        with self.tracer.start_as_current_span("convert-txt"):
            fragment = TextFragement(text=to_str(Path(file).read_bytes()))
            pages = [Page(document_fragements=[fragment])]

        return pages
