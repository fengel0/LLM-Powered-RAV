# tests/test_string_handler_pytest_class.py
from __future__ import annotations

import logging
import pytest

from core.string_handler import to_str, str_to_bytes
from core.logger import init_logging

init_logging("debug")
logger = logging.getLogger(__name__)


class TestStrToBytes:
    @pytest.fixture(autouse=True)
    def _newline_log(self):
        logger.debug("\n")

    def test_empty_string(self):
        assert str_to_bytes("") == b""

    def test_ascii(self):
        assert str_to_bytes("hello") == b"hello"

    def test_unicode_bmp(self):
        # Japanese "日本語"
        s = "日本語"
        b = str_to_bytes(s)
        logger.debug(s)
        logger.debug(b)
        assert isinstance(b, bytes)
        assert b.decode("utf-8") == s

    def test_emoji(self):
        s = "hello 👋🌍"
        b = str_to_bytes(s)
        assert b.decode("utf-8") == s

    def test_latin1_encoding(self):
        # 'é' is 0xE9 in latin-1
        s = "café"
        b_latin1 = str_to_bytes(s, encoding="latin-1")
        logger.debug(s)
        logger.debug(b_latin1)
        assert b_latin1 == b"caf\xe9"
        assert b_latin1.decode("latin-1") == s

    def test_replacement_behavior_is_not_explosive(self):
        # since source is str, errors="replace" only hits for odd cases like lone surrogate
        s = "good \udcff luck"  # include a lone surrogate to be annoying
        b = str_to_bytes(s, encoding="utf-8")
        logger.debug(s)
        logger.debug(b)
        # lone surrogate should be replaced with U+FFFD (UTF-8: EF BF BD)
        assert b"\xef\xbf\xbd" in b

    def test_large_string(self):
        s = "日本語とemoji🙂"
        b = str_to_bytes(s)
        assert len(b) > len(s)  # UTF-8 bytes longer than codepoints
        assert b.decode("utf-8") == s


class TestToStr:
    @pytest.fixture(autouse=True)
    def _newline_log(self):
        logger.debug("\n")

    def test_str_passthrough(self):
        s = "hello"
        assert to_str(s) == s

    def test_bytes_utf8(self):
        b = "日本語".encode("utf-8")
        logger.debug(b)
        assert to_str(b) == "日本語"

    def test_bytes_with_emoji(self):
        s = "👋🌍"
        b = s.encode("utf-8")
        output = to_str(b)
        logger.debug(s)
        logger.debug(output)
        assert output == s

    def test_bytearray(self):
        s = "café"
        ba = bytearray(s.encode("utf-8"))
        output = to_str(ba)
        logger.debug(s)
        logger.debug(output)
        assert output == s

    def test_non_utf8_bytes_with_replace(self):
        # Latin-1 encoded é will break under utf-8 and be replaced with U+FFFD
        bad_bytes = "café".encode("latin-1")
        result = to_str(bad_bytes, encoding="utf-8")
        logger.debug(bad_bytes)
        logger.debug(result)
        assert "caf" in result
        assert "�" in result  # replacement character

    def test_with_different_encoding(self):
        # Decode latin-1 correctly
        s = "café"
        latin1_bytes = s.encode("latin-1")
        output = to_str(latin1_bytes, encoding="latin-1")
        logger.debug(s)
        logger.debug(output)
        assert output == s

    def test_empty_inputs(self):
        assert to_str("") == ""
        assert to_str(b"") == ""
