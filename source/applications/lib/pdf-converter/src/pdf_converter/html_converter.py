"""
SimpleHTMLConverter
───────────────────
• No Marker imports – uses `markdownify` for HTML→Markdown.
• Assumes:  – HTML contains no embedded images
            – Entire document is treated as a single Page
• Produces: List[Page] where each page holds TextFragement and TableFragement
  objects (no ImageFragment because of the stated assumption).
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from core.string_handler import to_str

from markdownify import markdownify as md
from opentelemetry import trace

from core.result import Result
from domain.file_converter.interface import FileConverter
from domain.file_converter.model import (
    DocumentFragement,
    Page,
    TableFragement,
    TextFragement,
)

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
#  Converter
# --------------------------------------------------------------------------- #
class SimpleHTMLConverter(FileConverter):
    """
    Marker-free converter that turns an HTML file into Page/Fragment objects.
    """

    TABLE_RE = re.compile(r"^\s*\|")  # crude check for a GFM table

    def __init__(
        self,
    ) -> None:
        super().__init__()
        self.tracer: trace.Tracer = trace.get_tracer("SimpleHTMLConverter")

    # -------- File type check ------------------------------------------------
    def does_convert_filetype(self, filetype: str) -> bool:  # noqa: D401
        return filetype.lower() in {"html", "htm"}

    # -------- Public entry point --------------------------------------------
    def convert_file(self, file: str) -> Result[list[Page]]:
        try:
            pages = self._transform_file_to_markdown(file)
            return Result.Ok(pages)
        except Exception as exc:  # pylint: disable=broad-except
            # swallow stack trace – logging only the message like your PDF impl
            logger.error(exc.with_traceback(None))
            return Result.Err(exc)

    # -------- Private helpers -----------------------------------------------
    def _transform_file_to_markdown(self, file: str) -> list[Page]:
        """
        Steps
        -----
        1. Read HTML → Markdown via `markdownify`.
        2. Split Markdown blocks on blank lines.
        3. Detect simple tables (leading `|`) vs. normal text.
        4. Merge consecutive text fragments.
        5. Return **one** Page (no pagination for HTML).
        """
        with self.tracer.start_as_current_span("convert-html"):
            html_text = to_str(Path(file).read_bytes())
            md_text: str = md(html_text, strip=["img", "script", "style"])

            # break on blank lines, keep non-empty blocks only
            raw_blocks = [b.strip() for b in md_text.split("\n\n") if b.strip()]
            fragments: list[DocumentFragement] = []

            for block in raw_blocks:
                if self.TABLE_RE.match(block):
                    fragments.append(
                        TableFragement(full_tabel=block, header="", column=[])
                    )
                else:
                    fragments.append(TextFragement(text=block))

            # combine adjacent TextFragements into a single fragment each
            merged = self._merge_consecutive_text(fragments)
            pages = [Page(document_fragements=merged)]

        return pages

    @staticmethod
    def _merge_consecutive_text(
        fragments: list[DocumentFragement],
    ) -> list[DocumentFragement]:
        """
        Combine neighbouring TextFragements so consumers don’t have to handle
        artificial splits created by blank-line logic.
        """
        if not fragments:
            return []

        merged: list[DocumentFragement] = []
        buffer: TextFragement | None = None

        for frag in fragments:
            if isinstance(frag, TextFragement):
                if buffer is None:
                    buffer = TextFragement(text=frag.text)
                else:
                    buffer.text += "\n" + frag.text
            else:
                if buffer:
                    merged.append(buffer)
                    buffer = None
                merged.append(frag)

        if buffer:
            merged.append(buffer)

        return merged
