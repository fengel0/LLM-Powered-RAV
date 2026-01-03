from __future__ import annotations
import logging

logger = logging.getLogger(__name__)

# core/string_handler.py

_BOMS: list[tuple[bytes, str]] = [
    (b"\xef\xbb\xbf", "utf-8-sig"),
    (b"\xff\xfe\x00\x00", "utf-32-le"),
    (b"\x00\x00\xfe\xff", "utf-32-be"),
    (b"\xff\xfe", "utf-16-le"),
    (b"\xfe\xff", "utf-16-be"),
]


def to_str(
    data: bytes | bytearray | str,
    encoding: str | None = None,
    *,
    try_detector: bool = True,
) -> str:
    """
    bytes/bytearray/str -> str

    Priority:
      - str passthrough
      - explicit encoding (errors='replace')
      - BOM sniff
      - utf-8 strict
      - cp1252, latin-1
      - detector (optional, AFTER deterministic fallbacks)
      - utf-8 with surrogateescape
    """
    if isinstance(data, str):
        return data

    raw = bytes(data)
    if not raw:
        return ""

    if encoding is not None:
        return raw.decode(encoding, errors="replace")

    for bom, enc in _BOMS:
        if raw.startswith(bom):
            return raw.decode(enc)

    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        pass

    for enc in ("cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue

    if try_detector:
        try:
            from charset_normalizer import from_bytes  # type: ignore

            best = from_bytes(raw).best()
            if best and best.encoding:
                return str(best)
        except Exception:
            pass

    return raw.decode("utf-8", errors="surrogateescape")


def str_to_bytes(text: str, encoding: str = "utf-8", errors: str = "replace") -> bytes:
    """
    str -> bytes

    If you want U+FFFD (�) for lone surrogates when encoding to UTF-8,
    normalize them to U+FFFD first; otherwise Python uses '?' for encode-replace.
    """
    if not isinstance(text, str):
        raise TypeError(f"Expected str, got {type(text).__name__}")

    if encoding.lower() == "utf-8" and errors == "replace":
        normalized = text.encode("utf-8", "surrogatepass").decode("utf-8", "replace")
        return normalized.encode("utf-8")

    return text.encode(encoding, errors=errors)
