from dataclasses import field
import re
from enum import Enum
from pydantic import BaseModel


class DocumentFragement(BaseModel): ...


class FragementTypes(Enum):
    TEXT = "TEXT"
    TABEL = "TABEL"
    IMAGE = "IMAGE"


class ImageFragment(DocumentFragement):
    filename: str
    data: bytes

    def get_image_description_filename(self) -> str:
        return f"{self.filename}.md"


class TextFragement(DocumentFragement):
    text: str


class TableFragement(DocumentFragement):
    full_tabel: str
    header: str = field(init=False, default="")
    column: list[str] = field(init=False, default=[])

    # ------------------------------------------------------------------
    # Lifecycle helpers
    # ------------------------------------------------------------------
    def __post_init__(self) -> None:  # noqa: D401 – simple post‑init hook
        """Immediately parse *full_tabel* and populate *header*/*column*."""
        self.split_header_and_columns()

    # ------------------------------------------------------------------
    # Core logic
    # ------------------------------------------------------------------
    def split_header_and_columns(self) -> None:
        """Split *full_tabel* into *header* and *column* strings.

        The first non‑empty line becomes the header. If the second line is a
        standard markdown delimiter row (e.g. ``| --- | :---: | ---: |``), it
        is skipped. Everything after that is joined by new‑lines and stored in
        *column*.
        """

        # Normalise whitespace and drop blank lines
        lines: list[str] = [
            ln.strip() for ln in self.full_tabel.strip().splitlines() if ln.strip()
        ]

        if not lines:
            self.header, self.column = "", []
            return

        # First row is always the header
        self.header = lines[0]

        # Detect alignment row (contains only pipes, colons, dashes, spaces)
        align_pattern = re.compile(r"^\|?[ \t:.-]+(?:\|[ \t:.-]+)*\|?$")
        body_start_idx = (
            2 if len(lines) > 1 and align_pattern.fullmatch(lines[1]) else 1
        )

        # Remainder becomes the column/body string
        self.column = lines[body_start_idx:]


class Page(BaseModel):
    document_fragements: list[DocumentFragement]


class FragementLite(BaseModel):
    filename: str
    fragement_number: int
    fragement_type: FragementTypes

    def get_image_description_filename(self) -> str:
        return f"{self.filename}.md"


class PageLite(BaseModel):
    page_number: int
    fragments: list[FragementLite]
