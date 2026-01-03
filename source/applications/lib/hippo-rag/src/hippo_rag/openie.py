from __future__ import annotations
from copy import deepcopy

import asyncio
import json
import logging

from core.result import Result
from domain.hippo_rag.interfaces import OpenIEInterface
from domain.hippo_rag.model import (
    NerRawOutput,
    OpenIEResult,
    TripleRawOutput,
)
from domain.llm.interface import AsyncLLM
from domain.llm.model import TextChatMessage
from pydantic import BaseModel, Field

from hippo_rag.template.open_id_default_prompts import (
    DEFAULT_NER_EXTRACTION_HISTORY,
    DEFAULT_TRIPLE_EXTRACTION_HISTORY,
    DEFAULT_TRIPLE_EXTRACTION_USER_PROMPT,
)
from hippo_rag.utils.misc_utils import filter_invalid_triples

logger = logging.getLogger(__name__)


# ---------------------- structured response schemas for the LLM ----------------------


class _NerSO(BaseModel):
    named_entities: list[str] = Field(description="Contained named Entities")


class _TriplesSO(BaseModel):
    triples: list[list[str]] = Field(description="Contains a list of triples")


class OpenIEConfig(BaseModel):
    messages_ner: list[TextChatMessage] = DEFAULT_NER_EXTRACTION_HISTORY
    messages_triple_extraction: list[TextChatMessage] = (
        DEFAULT_TRIPLE_EXTRACTION_HISTORY
    )
    user_triple_message: str = DEFAULT_TRIPLE_EXTRACTION_USER_PROMPT
    retries: int = 3


class AsyncOpenIE(OpenIEInterface):
    def __init__(self, llm: AsyncLLM, config: OpenIEConfig):
        self.llm = llm
        self._config = config

    def _render(self, name: str, **kwargs: object) -> list[TextChatMessage]:
        return self.ptm.render(name=name, **kwargs)  # type: ignore

    async def ner(
        self,
        chunk_key: str,
        passage: str,
        metadata: dict[str, int | float | str] | None = None,
    ) -> Result[NerRawOutput]:
        messages = deepcopy(self._config.messages_ner)
        if metadata:
            messages.append(
                TextChatMessage(
                    role="user",
                    content=f"metadata:{json.dumps(metadata)} \n text:{passage}",
                )
            )
        else:
            messages.append(
                TextChatMessage(
                    role="user",
                    content=passage,
                )
            )
        logger.info("extracting ner")
        for i in range(self._config.retries):
            so_res = await self.llm.chat_structured_output(messages, _NerSO)
            if so_res.is_error():
                return so_res.propagate_exception()

            so = so_res.get_ok()
            unique_entities: set[str] = set()
            for e in so.named_entities:
                if len(e) > 0:
                    unique_entities.add(e)

            raw_dump = so.model_dump_json()
            if len(unique_entities) > 0:
                unique_entities_list = list(unique_entities)
                unique_entities_list.sort()
                return Result.Ok(
                    NerRawOutput(
                        chunk_id=chunk_key,
                        response=raw_dump,
                        unique_entities=unique_entities_list,
                        metadata=metadata or {},
                    )
                )
            logger.warning(f"no entities where found in ner try:{i} passage:{passage}")
        logger.warning(f"entitie extraction failed for passage:{passage}")
        raw_dump = _NerSO(named_entities=[]).model_dump_json()
        return Result.Ok(
            NerRawOutput(
                chunk_id=chunk_key,
                response=raw_dump,
                unique_entities=[],
                metadata={},
            )
        )

    async def triple_extraction(
        self,
        chunk_key: str,
        passage: str,
        named_entities: list[str],
        metadata: dict[str, int | float | str] | None = None,
    ) -> Result[TripleRawOutput]:
        messages = deepcopy(self._config.messages_triple_extraction)
        if metadata:
            messages.append(
                TextChatMessage(
                    role="user",
                    content=self._config.user_triple_message.format(
                        passage=f"metadata:{json.dumps(metadata)} \n text:{passage}",
                        named_entities=json.dumps({"named_entities": named_entities}),
                    ),
                )
            )
        else:
            messages.append(
                TextChatMessage(
                    role="user",
                    content=self._config.user_triple_message.format(
                        passage=passage,
                        named_entities=json.dumps({"named_entities": named_entities}),
                    ),
                )
            )

        logger.info("extract triple")
        for i in range(self._config.retries):
            so_res = await self.llm.chat_structured_output(messages, _TriplesSO)
            if so_res.is_error():
                return so_res.propagate_exception()

            so = so_res.get_ok()
            raw_dump = so.model_dump_json()
            try:
                triples = filter_invalid_triples(triples=so.triples)
            except Exception as e:
                logger.error(f"filtering for invalid triples failed {e}", exc_info=True)
                triples = []
            if len(triples) > 0:
                return Result.Ok(
                    TripleRawOutput(
                        chunk_id=chunk_key,
                        response=raw_dump,
                        metadata=metadata or {},
                        triples=triples,
                    )
                )
            logger.warning(
                f"no triples where extracted try: {i}, entiies:{named_entities} passage:{passage}"
            )
        logger.warning(f"triple extraction failed for passage:{passage}")
        raw_dump = _TriplesSO(triples=[]).model_dump_json()
        return Result.Ok(
            TripleRawOutput(
                chunk_id=chunk_key,
                response=raw_dump,
                metadata={},
                triples=[],
            )
        )

    async def openie(
        self,
        chunk_key: str,
        passage: str,
        metadata: dict[str, int | float | str] | None = None,
    ) -> Result[OpenIEResult]:
        ner_res = await self.ner(chunk_key, passage, metadata)
        if ner_res.is_error():
            return ner_res.propagate_exception()

        ner_out = ner_res.get_ok()

        triple_res = await self.triple_extraction(
            chunk_key, passage, ner_out.unique_entities, metadata
        )
        if triple_res.is_error():
            return triple_res.propagate_exception()

        triple_out = triple_res.get_ok()

        combined: OpenIEResult = OpenIEResult(ner=ner_out, triplets=triple_out)  # type: ignore[assignment]
        return Result.Ok(combined)

    async def batch_openie(
        self,
        chunks: dict[str, str],
        metadata: dict[str, int | float | str] | None = None,
    ) -> Result[tuple[dict[str, NerRawOutput], dict[str, TripleRawOutput]]]:
        # Phase 1: NER
        async def run_ner(
            k: str,
            v: str,
        ) -> tuple[str, Result[NerRawOutput]]:
            return k, await self.ner(k, v, metadata)

        ner_pairs = [run_ner(k, v) for k, v in chunks.items()]

        ner_ok: dict[str, NerRawOutput] = {}
        errors: list[str] = []
        for request in ner_pairs:
            k, res = await request
            if res.is_ok():
                ner_ok[k] = res.get_ok()
            else:
                errors.append(f"NER failed for {k}: {res.get_error()}")

        if not ner_ok:
            return Result.Err(
                Exception("; ".join(errors) if errors else "NER failed for all chunks.")
            )

        # Phase 2: Triples
        async def run_triples(
            k: str,
            passage: str,
            ents: list[str],
        ) -> tuple[str, Result[TripleRawOutput]]:
            return k, await self.triple_extraction(k, passage, ents, metadata)

        triple_pairs = await asyncio.gather(
            *[
                run_triples(k, chunks[k], ner_ok[k].unique_entities)
                for k in ner_ok.keys()
            ]
        )

        triples_ok: dict[str, TripleRawOutput] = {}
        for k, res in triple_pairs:
            if res.is_ok():
                triples_ok[k] = res.get_ok()
            else:
                errors.append(f"Triple extraction failed for {k}: {res.get_error()}")

        # Partial success is allowed; caller decides how to handle missing keys.
        return Result.Ok((ner_ok, triples_ok))
