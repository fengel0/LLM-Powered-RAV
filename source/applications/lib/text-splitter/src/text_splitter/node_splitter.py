from __future__ import annotations
import re
import hashlib
import logging
from typing import Callable, List, Literal, Optional, Tuple

from pydantic import BaseModel
import pysbd
import tiktoken
from langdetect import detect, LangDetectException

from domain.file_converter.model import TableFragement, TextFragement
from domain.rag.indexer.interface import DocumentSplitter, SplitNode, Document

logger = logging.getLogger(__name__)

# ----------------------------- config ---------------------------------

DEFAULT_PARAGRAPH_SEP = "\n\n\n"
SECONDARY_REGEX = r"[^,.;:!?。？！；：]+[,.;:!?。？！；：]?|[,.;:!?。？！；：]"

PAGE_MARKER_RE = re.compile(r"\[PAGE\s+(\d+) Beginn\]")


class NodeSplitterConfig(BaseModel):
    # LlamaIndex-like core knobs (token-based)
    chunk_size: int = 512  # token budget per chunk
    chunk_overlap: int = 120  # token overlap between chunks (0+)
    paragraph_separator: str = DEFAULT_PARAGRAPH_SEP
    secondary_chunking_regex: str = SECONDARY_REGEX

    # Your features retained
    default_language: str = "en"

    # Optional: when a *single unit* is longer than chunk_size, choose fallback behavior
    overflow_strategy: Literal["fallback_split", "truncate"] = "fallback_split"
    truncate_marker: str = ""  # e.g. "..." if you want a visible marker


# ----------------------------- utils ----------------------------------


def _hash_id(text: str, salt: str = "") -> str:
    h = hashlib.sha256()
    h.update(salt.encode("utf-8"))
    h.update(text.encode("utf-8"))
    return h.hexdigest()[:24]


def detect_language(text: str, fallback: str = "en") -> str:
    try:
        if len(text.strip()) < 10:
            return fallback
        return detect(text)
    except LangDetectException:
        return fallback
    except Exception:
        return fallback


class _Tokenizer:
    def __init__(self):
        self.enc = tiktoken.get_encoding("cl100k_base")

    def count(self, text: str) -> int:
        return len(self.enc.encode(text))

    def encode(self, text: str) -> List[int]:
        return self.enc.encode(text)

    def slice_decode(self, tokens: List[int], start: int, end: int) -> str:
        return self.enc.decode(tokens[start:end])


# ----------------------- sentence & fallback splitters -----------------


def _split_by_sep(sep: str) -> Callable[[str], List[str]]:
    def _fn(text: str) -> List[str]:
        parts = text.split(sep)
        if len(parts) <= 1:
            return [text]
        out: List[str] = []
        for i, p in enumerate(parts):
            # re-attach the separator between blocks (except the last)
            out.append(p + (sep if i < len(parts) - 1 else ""))
        return [s for s in out if s]

    return _fn


def _split_by_regex(pattern: str) -> Callable[[str], List[str]]:
    rgx = re.compile(pattern)

    def _fn(text: str) -> List[str]:
        parts = rgx.findall(text)
        return parts if parts else [text]

    return _fn


def _split_by_words() -> Callable[[str], List[str]]:
    def _fn(text: str) -> List[str]:
        ws = text.split()
        if len(ws) <= 1:
            return [text]
        # preserve spaces between words on re-join during packing
        return [w + " " for w in ws[:-1]] + [ws[-1]]

    return _fn


def _split_by_chars() -> Callable[[str], List[str]]:
    def _fn(text: str) -> List[str]:
        return list(text) if text else []

    return _fn


# -------------------------- main splitter ------------------------------


class AdvancedSentenceSplitter(DocumentSplitter):
    """LlamaIndex-like: greedy pack sentences into token-sized chunks with token overlap.
    Keeps your language detection and table handling intact.
    """

    _segers: dict[str, pysbd.Segmenter] = {}

    def __init__(self, config: NodeSplitterConfig):
        self._config = config
        self._tok = _Tokenizer()

        # sentence tokenizer per language (pysbd)
        self._segers[config.default_language] = pysbd.Segmenter(
            language=config.default_language, clean=True
        )

        # establish split function sequences (paragraph → sentence → sub-sentence)
        self._paragraph_split = _split_by_sep(config.paragraph_separator)

        # sub-sentence fallbacks: regex → words → chars
        self._sub_sentence_fns: List[Callable[[str], List[str]]] = [
            _split_by_regex(config.secondary_chunking_regex),
            _split_by_words(),
            _split_by_chars(),
        ]

    # ------------- token helpers & truncation (marker-aware) -------------

    def _token_len(self, text: str) -> int:
        return self._tok.count(text)

    def _truncate_to_tokens(self, text: str, max_tokens: int, marker: str = "") -> str:
        if max_tokens <= 0:
            return ""
        ids = self._tok.encode(text)
        if len(ids) <= max_tokens:
            return text
        if not marker:
            return self._tok.slice_decode(ids, 0, max_tokens).rstrip()
        marker_ids = self._tok.encode(marker)
        if len(marker_ids) >= max_tokens:
            return self._tok.slice_decode(ids, 0, max_tokens).rstrip()
        allowed = max_tokens - len(marker_ids)
        while allowed > 0:
            trimmed = self._tok.slice_decode(ids, 0, allowed).rstrip()
            cand = trimmed + marker
            if self._token_len(cand) <= max_tokens:
                return cand
            allowed -= 1
        return self._tok.slice_decode(ids, 0, max_tokens).rstrip()

    # ---------------------- language-aware sentences ---------------------

    def _segment_sentences(self, text: str) -> Tuple[str, List[str]]:
        lang = detect_language(text, fallback=self._config.default_language)
        seger = self._segers.get(lang)
        if not seger:
            try:
                seger = pysbd.Segmenter(language=lang, clean=True)
                self._segers[lang] = seger
            except Exception:
                lang = self._config.default_language
                seger = self._segers[lang]
        sentences: List[str] = seger.segment(text)  # type: ignore
        return lang, sentences if sentences else [text]

    # ------------------- recursive split (like LI _split) ----------------

    class _Split:
        __slots__ = ("text", "is_sentence", "tok_len")

        def __init__(self, text: str, is_sentence: bool, tok_len: int):
            self.text = text
            self.is_sentence = is_sentence
            self.tok_len = tok_len

    def _split_recursive(self, text: str, chunk_size: int) -> List[_Split]:
        """Break text into pieces <= chunk_size tokens. Prefer paragraphs → sentences,
        then sub-sentence fallbacks (regex→words→chars)."""
        if self._token_len(text) <= chunk_size:
            return [self._Split(text, True, self._token_len(text))]

        # 1) paragraph-level
        # para_parts = self._paragraph_split(text)
        # if len(para_parts) > 1:
        # out: List[AdvancedSentenceSplitter._Split] = []
        # for p in para_parts:
        # out.extend(self._split_recursive(p, chunk_size))
        # return out

        # 2) sentence-level (language-aware)
        _, sent_parts = self._segment_sentences(text)
        if len(sent_parts) > 1:
            collected: List[AdvancedSentenceSplitter._Split] = []
            for s in sent_parts:
                tlen = self._token_len(s)
                if tlen <= chunk_size:
                    collected.append(self._Split(s, True, tlen))
                else:
                    collected.extend(self._split_recursive(s, chunk_size))
            return collected

        # 3) sub-sentence fallbacks
        units: List[str] = [text]
        for fn in self._sub_sentence_fns:
            units = fn(text)
            if len(units) > 1:
                break

        out: List[AdvancedSentenceSplitter._Split] = []
        for u in units:
            tlen = self._token_len(u)
            if tlen <= chunk_size:
                out.append(self._Split(u, False, tlen))
            else:
                # last resort: hard truncate to fit
                truncated = self._truncate_to_tokens(
                    u, chunk_size, marker=self._config.truncate_marker
                )
                out.append(self._Split(truncated, False, self._token_len(truncated)))
        return out

    # ---------------------- greedy merge with overlap --------------------
    def _merge_to_chunks(
        self, splits: List[_Split], chunk_size: int, overlap: int
    ) -> List[str]:
        """Greedily pack splits up to chunk_size tokens.
        After closing a chunk, seed next chunk with up-to-`overlap` tokens from the tail.
        If the seeded overlap prevents adding the next split, drop the overlap."""
        # sanity: overlap cannot be >= chunk_size
        if overlap >= chunk_size:
            overlap = max(0, chunk_size - 1)

        chunks: List[str] = []
        cur: List[Tuple[str, int]] = []
        cur_tokens = 0
        new_chunk = True

        def seed_with_overlap_from(full_text: str) -> None:
            nonlocal cur, cur_tokens, new_chunk
            cur = []
            cur_tokens = 0
            new_chunk = True
            if overlap <= 0 or not full_text:
                return
            ids = self._tok.encode(full_text)
            if not ids:
                return
            keep = ids[-min(overlap, len(ids)) :]
            if not keep:
                return
            seed = self._tok.slice_decode(keep, 0, len(keep))
            if not seed:
                return
            cur.append((seed, len(keep)))
            cur_tokens = len(keep)
            new_chunk = False  # we already placed the overlap

        def close_chunk() -> None:
            nonlocal chunks, cur, cur_tokens, new_chunk
            if not cur:
                # nothing to close
                return
            full = "".join(t for t, _ in cur).strip()
            if full:
                chunks.append(full)
            # prepare next chunk with overlap from just-closed text
            seed_with_overlap_from(full)

        i = 0
        # hard safety to avoid infinite loops in extreme edge cases
        max_iters = max(10_000, len(splits) * 20)
        iters = 0

        while i < len(splits):
            iters += 1
            if iters > max_iters:
                # emergency break: finalize whatever we have and return
                if cur:
                    chunks.append("".join(t for t, _ in cur).strip())
                break

            s = splits[i]

            # Defensive: a single split shouldn't exceed chunk_size, but if it does, truncate
            if s.tok_len > chunk_size:
                forced = self._truncate_to_tokens(
                    s.text, chunk_size, marker=self._config.truncate_marker
                )
                chunks.append(forced.strip())
                # seed overlap from this forced chunk (optional; safe either way)
                seed_with_overlap_from(forced)
                i += 1
                continue

            # If current (maybe preseeded) chunk can't fit s, try to fix:
            if not new_chunk and cur_tokens + s.tok_len > chunk_size:
                # 1) Close current chunk (keeping overlap)
                close_chunk()
                # 2) If we *still* can't fit s (because overlap is too large), drop overlap
                if not new_chunk and cur_tokens + s.tok_len > chunk_size:
                    # clear the preseeded overlap and start a fresh chunk
                    cur = []
                    cur_tokens = 0
                    new_chunk = True
                # re-evaluate s with the new (possibly empty) chunk
                continue

            # Place s into the current chunk (always allow at least one in a new chunk)
            cur.append((s.text, s.tok_len))
            cur_tokens += s.tok_len
            new_chunk = False
            i += 1

        # flush last chunk
        if cur:
            chunks.append("".join(t for t, _ in cur).strip())

        # strip empties
        return [c for c in chunks if c]

    # -------------------------- public API -------------------------------

    def split_documents(self, doc: Document) -> List[SplitNode]:
        nodes: List[SplitNode] = []
        order = 0

        # Case 1: plain string
        if isinstance(doc.content, str):
            order += 1
            chunk_nodes = self._split_text_blob(
                text=doc.content,
                base_meta={
                    "fragment_type": "text",
                    **doc.metadata,
                    "doc_id": doc.id,
                },
                id_salt=f"{doc.id}-text",
            )
            # (Optional) scan for markers even in plain strings
            for n in chunk_nodes:
                pages = {int(p) for p in PAGE_MARKER_RE.findall(n.content or "")}
                if pages:
                    # strip markers from the text
                    # n.content = PAGE_MARKER_RE.sub("", n.content).strip()
                    n.metadata = {
                        **n.metadata,
                        "pages": ",".join(map(str, sorted(pages))),
                    }
            nodes.extend(chunk_nodes)
            return nodes

        # Case 2: paginated, merge across pages
        pages = doc.content

        text_buf: list[tuple[int, str]] = []  # [(page_number, text), ...]
        text_segment_idx = 0  # for unique id_salt suffix

        def flush_text_buf():
            nonlocal order, nodes, text_buf, text_segment_idx
            if not text_buf:
                return

            # Build merged text with explicit page markers
            merged_chunks: list[str] = []
            seen_pages: list[int] = []

            last_page = None
            for pn, txt in text_buf:
                if pn != last_page:
                    merged_chunks.append(f"[PAGE {pn} Beginn]")
                    seen_pages.append(pn)
                    last_page = pn
                if txt:
                    merged_chunks.append(txt)

            merged_text = "\n\n".join(merged_chunks).strip()
            if merged_text:
                order += 1
                text_segment_idx += 1
                base_meta = {
                    "fragment_type": "text",
                    "pages": ",".join(
                        str(p) for p in sorted(set(seen_pages))
                    ),  # coarse provenance
                    "order": str(order),
                    **doc.metadata,
                }
                chunk_nodes = self._split_text_blob(
                    text=merged_text,
                    base_meta=base_meta,
                    id_salt=f"{doc.id}-text-{text_segment_idx}",
                )

                # --- NEW: refine pages per chunk by scanning markers inside each chunk
                for n in chunk_nodes:
                    # 1) collect page ids in this chunk
                    chunk_pages = {int(p) for p in PAGE_MARKER_RE.findall(n.content)}
                    if chunk_pages:
                        # 2) strip markers so content is clean
                        # n.content = PAGE_MARKER_RE.sub("", n.content).strip()
                        # 3) set precise pages for this chunk
                        n.metadata = {
                            **n.metadata,
                            "pages": ",".join(map(str, sorted(chunk_pages))),
                        }
                        # (optional) convenience: single-page shortcut
                        if len(chunk_pages) == 1:
                            n.metadata["page"] = str(next(iter(chunk_pages)))

                nodes.extend(chunk_nodes)

            text_buf = []

        for p_idx, page in enumerate(pages):
            page_number = p_idx + 1
            frags = page.document_fragements

            for f_idx, frag in enumerate(frags):
                if isinstance(frag, TextFragement):
                    text_buf.append((page_number, frag.text or ""))

                elif isinstance(frag, TableFragement):
                    # Flush any accumulated text before the table
                    flush_text_buf()
                    order += 1
                    nodes.extend(
                        self._split_table_columns(
                            table=frag,
                            page_number=page_number,
                            base_order=order,
                            id_salt=f"{doc.id}-p{p_idx}-t{f_idx}",
                            metadata={**doc.metadata, "page": str(page_number)},
                        )
                    )
                else:
                    logger.warning("Unsupported Fragement Type")

        # Flush remaining text after last page
        flush_text_buf()

        return nodes

    # ---------------------- text path (token-based) ----------------------

    def _split_text_blob(
        self, text: str, base_meta: dict[str, str | int | float], id_salt: str
    ) -> List[SplitNode]:
        detected_language, _ = self._segment_sentences(text)
        splits = self._split_recursive(text, self._config.chunk_size)
        chunk_strs = self._merge_to_chunks(
            splits,
            chunk_size=self._config.chunk_size,
            overlap=self._config.chunk_overlap,
        )

        nodes: list[SplitNode] = []
        total = len(chunk_strs)
        for idx, content in enumerate(chunk_strs):
            meta = dict(base_meta)
            meta.update(
                {
                    "unit": "sentence_chunk",
                    "detected_language": detected_language,
                    "window_index": str(idx),
                    "window_count": str(total),
                }
            )
            node_id = _hash_id(content, f"{id_salt}-w{idx}")
            nodes.append(SplitNode(id=node_id, content=content, metadata=meta))
        return nodes

    # ---------------------- tables (unchanged) ---------------------------

    def _split_table_columns(
        self,
        table: TableFragement,
        page_number: int,
        base_order: int,
        id_salt: str,
        metadata: dict[str, str | int | float],
    ) -> List[SplitNode]:
        nodes: List[SplitNode] = []
        header = table.header
        rows = table.column
        row_number = 0

        sample_text = " ".join([str(row) for row in rows[:3]])
        detected_language = detect_language(
            sample_text, fallback=self._config.default_language
        )

        for row in rows:
            nodes.append(
                SplitNode(
                    content=f"{header}\n{row}",
                    metadata={
                        "fragment_type": "table",
                        "page": str(page_number),
                        "order": str(base_order),
                        "row_number": str(row_number),
                        "detected_language": detected_language,
                        **metadata,
                    },
                    id=f"{id_salt}-row-{row_number}",
                )
            )
            row_number += 1
        return nodes
