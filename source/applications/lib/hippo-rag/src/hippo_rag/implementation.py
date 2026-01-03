import logging
import time
from ast import literal_eval
from collections import defaultdict
from dataclasses import dataclass

from domain.rag.model import (
    Message,
)
import numpy as np
from core.hash import compute_mdhash_id
from core.result import Result
from domain.hippo_rag.interfaces import (
    EmbeddingStoreInterface,
    GraphDBInterface,
    HippoRAGInterface,
    LLMReranker,
    SimilarNodes,
    StateStore,
)
from domain.hippo_rag.model import Chunk, QuerySolution, RerankLog, Triple
from domain.llm.interface import AsyncLLM
from domain.llm.model import TextChatMessage
from opentelemetry import trace
from domain.rag.interface import RAGLLM, Conversation
from domain.rag.model import RAGResponse, Node

from tqdm import tqdm

from hippo_rag.indexer import CollectionFilterAttribute
from hippo_rag.template.rag_system_prompts import DEFAULT_RAG_QA_SYSTEM
from hippo_rag.utils.misc_utils import (
    flatten_facts,
    min_max_normalize,
)

logger = logging.getLogger(__name__)


@dataclass
class HippoRAGConfig:
    retrieval_top_k: int = 10  # max docs to return
    linking_top_k: int = 5  # facts to rerank / link
    passage_node_weight: float = 0.05  # graph edge weighting factor
    qa_top_k: int = 3  # number of docs passed to QA
    damping: float = 0.5
    chunks_to_retrieve_ppr_seed: int = 30
    directional_ppr: bool = True
    system_config: str = DEFAULT_RAG_QA_SYSTEM


class HippoRAG(HippoRAGInterface, RAGLLM):
    _vector_store_entity: EmbeddingStoreInterface
    _vector_store_chunk: EmbeddingStoreInterface
    _vector_store_fact: EmbeddingStoreInterface
    _llm: AsyncLLM
    _graph: GraphDBInterface
    _rerank_filter: LLMReranker
    _state_store: StateStore

    def __init__(
        self,
        vector_store_entity: EmbeddingStoreInterface,
        vector_store_chunk: EmbeddingStoreInterface,
        vector_store_fact: EmbeddingStoreInterface,
        llm: AsyncLLM,
        graph: GraphDBInterface,
        filter: LLMReranker,
        state_store: StateStore,
        config: HippoRAGConfig,
    ):
        self._vector_store_entity = vector_store_entity
        self._vector_store_chunk = vector_store_chunk
        self._vector_store_fact = vector_store_fact
        self._llm = llm
        self._graph = graph
        self._rerank_filter = filter
        self._state_store = state_store

        self.openie_results_path = ""
        self.global_config = config

        # runtime flags/metrics (kept because you already log them)
        self.ppr_time = 0.0
        self.rerank_time = 0.0
        self.all_retrieval_time = 0.0

        self.tracer = trace.get_tracer("HippoRAG")

    # ------------------------------- indexing

    async def request(
        self,
        conversation: Conversation,
        metadata_filters: dict[str, list[str] | list[int] | list[float]] | None = None,
        collection: str | None = None,
    ) -> Result[RAGResponse]:
        with self.tracer.start_as_current_span("request"):
            if collection and metadata_filters:
                metadata_filters[CollectionFilterAttribute] = [collection]
            if collection and not metadata_filters:
                metadata_filters = {}
                metadata_filters[CollectionFilterAttribute] = [collection]

            # if len(conversation.messages) == 1:
            assert len(conversation.messages) > 0
            query = conversation.messages[-1].message

            queries_result = await self.retrieve(
                queries=[query],
                metadata=metadata_filters,
                model=conversation.model,
            )  # type: ignore
            if queries_result.is_error():
                return queries_result.propagate_exception()
            retrieved_docs = queries_result.get_ok()[0]

            retrieved_passages = retrieved_docs.docs[: self.global_config.qa_top_k]

            prompt_user = ""
            for passage in retrieved_passages:
                prompt_user += f"Retrived Information: {passage.content}\n\n"
            prompt_user += "Question: " + query + "\nThought: "

            all_qa_messages = [
                TextChatMessage(
                    role="system", content=self.global_config.system_config
                ),
                TextChatMessage(role="user", content=prompt_user),
            ]
            result = await self._llm.stream_chat(
                all_qa_messages, llm_model=conversation.model
            )
            if result.is_error():
                return result.propagate_exception()

            final_response = result.get_ok()

            return Result.Ok(
                RAGResponse.create_stream_response(
                    nodes=[
                        Node(
                            id=passage.id,
                            content=passage.content,
                            similarity=passage.score,
                            metadata=passage.metadata,
                        )
                        for passage in retrieved_passages
                    ],
                    generator=final_response,
                )
            )


    async def _search_passages(
        self, query: str, k: int, allowed_chunks: list[str] | None = None
    ) -> Result[dict[str, float]]:
        with self.tracer.start_as_current_span("dense chunk retrival"):
            try:
                if hasattr(self._vector_store_chunk, "query"):
                    res = await self._vector_store_chunk.query(
                        query=query, top_k=k, allowd__point_ids=allowed_chunks
                    )
                    if res.is_error():
                        return res.propagate_exception()
                    hits = res.get_ok()
                    # tolerate dict or attr objects
                    return Result.Ok({h.id: h.score for h in hits})
                # optional: add indexer-based querying here if your store supports it
                return Result.Err(
                    NotImplementedError("Vector store has no usable query method")
                )
            except Exception as e:
                logger.exception("Passage search failed")
                return Result.Err(e)

    async def _fetch_docs_by_ids(self, ids: list[str]) -> Result[list[str]]:
        if not ids:
            return Result.Ok([])
        res = await self._vector_store_chunk.get_rows(ids)
        if res.is_error():
            return res.propagate_exception()
        rows = res.get_ok()  # dict[str, Row]
        docs = [rows[i].content for i in ids if i in rows]
        return Result.Ok(docs)

    # ============================== Hauptfunktion ==============================

    def _get_top_k_weights(
        self,
        link_top_k: int,
        all_phrase_weights: dict[str, float],
        linking_score_map: dict[str, float],
    ) -> tuple[dict[str, float], dict[str, float]]:
        # choose top ranked nodes in linking_score_map
        linking_score_map = dict(
            sorted(linking_score_map.items(), key=lambda x: x[1], reverse=True)[
                :link_top_k
            ]
        )
        top_k_phrases = set(linking_score_map.keys())  # Das sind bereits hashes!
        filtered_phrase_weights = {
            phrase_hash: scores
            for phrase_hash, scores in all_phrase_weights.items()
            if phrase_hash in top_k_phrases
        }

        return filtered_phrase_weights, linking_score_map

    async def _graph_search_with_fact_entities(
        self,
        query: str,
        link_top_k: int,
        query_fact_scores: list[SimilarNodes],  # bereits passend zu top_k_facts gereiht
        top_k_facts: list[Triple],  # (subj, pred, obj)
        num_to_retrieve: int,
        chunks_to_retrieve_ppr_seed: int,
        directional_ppr: bool,
        damping: float,
        passage_node_weight: float = 0.05,
        allowed_entities: list[str] | None = None,
        allowed_chunks: list[str] | None = None,
    ) -> Result[dict[str, float]]:
        with self.tracer.start_as_current_span("graph-search-with-fact-entitis"):
            if allowed_entities is None:
                allowed_entities = []
            if allowed_chunks is None:
                allowed_chunks = []
            try:
                occurs_by_entity: dict[str, int] = defaultdict(int)
                linking_score_map: dict[str, float] = {}

                phrase_weights: dict[str, float] = {}
                passage_weights: dict[str, float] = {}

                phrase_scores: dict[str, list[float]] = {}
                phrase_and_ids: set[tuple[str, str]] = set()

                """
                Block berechnet für entitäten in fakten einen score
                dieser setzt sich aus dem start score und der anzahl an chunks zusammen mit welche diese Verbunden ist.
                """
                for rank, (subj, _, obj) in enumerate(top_k_facts):
                    raw = float(query_fact_scores[rank].score)
                    # clamp negatives/NaNs wie im Original-Reset
                    score = 0.0 if raw < 0.0 else raw

                    for entity in [subj.lower(), obj.lower()]:
                        entity_hid = compute_mdhash_id(entity)  # Prefix egal laut dir

                        # filter nicht erlaubter entitäten theortisch passiert das nicht
                        if allowed_entities and (entity_hid not in allowed_entities):
                            continue

                        ent_res = await self._graph.get_node_by_hash(hash_id=entity_hid)
                        if ent_res.is_error():
                            return ent_res.propagate_exception()
                        # sollte nicht passieren
                        if ent_res.get_ok() is None:
                            continue

                        chunks_res = (
                            await self._graph.get_chunk_node_connection_for_entity(
                                hash_id=entity_hid, allowed_chunks=list(allowed_chunks)
                            )
                        )
                        if chunks_res.is_error():
                            return chunks_res.propagate_exception()
                        chunk_nodes = chunks_res.get_ok()

                        # zählen verbindungen zu chunks
                        deg = len({c.hash_id for c in chunk_nodes})
                        if deg == 0:
                            deg = 1

                        weighted = score / deg
                        phrase_weights.setdefault(entity_hid, 0.0)
                        phrase_weights[entity_hid] += weighted
                        occurs_by_entity[entity_hid] += 1
                        phrase_and_ids.add((entity_hid, entity))

                """
                Normalisieren gewichte mit auftritts häufigkeit in retrievten fakten
                """
                for entity_hid, cnt in occurs_by_entity.items():
                    if cnt > 0:
                        phrase_weights[entity_hid] /= cnt

                """
                anpassen der gewichtung der einzelnen Frasen basierend auf der Gewichtung der Entitäten
                """
                for phrase_id, _ in phrase_and_ids:
                    if phrase_id not in list(phrase_scores.keys()):
                        phrase_scores[phrase_id] = []
                    phrase_scores[phrase_id].append(phrase_weights[phrase_id])

                """
                Berechnen des Durchschnittelchen Scores
                """
                for phrase_id, scores in phrase_scores.items():
                    linking_score_map[phrase_id] = float(np.mean(scores))

                """
                Wenn gewünscht gib mir die besten
                """
                if link_top_k:
                    phrase_weights, linking_score_map = self._get_top_k_weights(
                        link_top_k, phrase_weights, linking_score_map
                    )

                """
                suche nach wichtigesten chunks
                """
                dpr_res = await self._vector_store_chunk.query(
                    query=query,
                    allowd__point_ids=allowed_chunks,
                    top_k=chunks_to_retrieve_ppr_seed,
                )
                if dpr_res.is_error():
                    return dpr_res.propagate_exception()
                dpr_hits = dpr_res.get_ok()

                dpr_norm = min_max_normalize([h.score for h in dpr_hits])

                for i, hit in enumerate(dpr_hits):
                    chunk_id = hit.id
                    score = dpr_norm[i]
                    passage_weights[chunk_id] = score * passage_node_weight
                    linking_score_map[chunk_id] = score * passage_node_weight

                node_weights: dict[str, float] = {
                    **linking_score_map,
                    **passage_weights,
                }

                if len(linking_score_map) > 30:
                    linking_score_map = dict(
                        sorted(
                            linking_score_map.items(), key=lambda x: x[1], reverse=True
                        )[:30]
                    )

                assert sum(node_weights.values()) > 0, (
                    f"No phrases found in the graph for the given facts: {top_k_facts}"
                )

                return await self._graph.personalized_pagerank(
                    seeds=node_weights,
                    damping=damping,
                    top_k=num_to_retrieve,
                    directed=directional_ppr,
                    allowed_hash_ids=[*allowed_chunks, *allowed_entities],
                )

            except Exception as e:
                logger.error(e, exc_info=True)
                return Result.Err(e)

    def top_k_seeds(
        self,
        weights: dict[str, float],  # hash_id -> weight
        k: int,
        sparse: bool = True,
    ) -> dict[str, float]:
        if k <= 0 or not weights:
            return {} if sparse else {h: 0.0 for h in weights}

        items = sorted(weights.items(), key=lambda x: x[1], reverse=True)[:k]
        if sparse:
            return dict(items)

        keep = {h for h, _ in items}
        return {h: (w if h in keep else 0.0) for h, w in weights.items()}

    # ------------------------------- retrieval: full pipeline
    async def retrieve(
        self,
        queries: list[str],
        metadata: dict[str, list[str] | list[int] | list[float]] | None = None,
        model: str | None = None,
    ) -> Result[list[QuerySolution]]:
        with self.tracer.start_as_current_span("retrieval"):
            retrieve_start_time = time.time()

            triples: list[Triple] | None = None
            ids_chunks: list[str] | None = None
            triple_ids: list[str] | None = None
            entitie_ids: list[str] | None = None

            if metadata is not None:
                result = await self._state_store.load_openie_info_with_metadata(
                    metadata=metadata
                )
                if result.is_error():
                    return result.propagate_exception()
                docs = result.get_ok().docs
                logger.debug(f"docs found {len(docs)}")
                if len(docs) == 0:
                    result = [
                        QuerySolution(question=query, docs=[]) for query in queries
                    ]
                    return Result.Ok(result)

                triples = flatten_facts([doc.extracted_triples for doc in docs])

                ids_chunks = [doc.idx for doc in docs]
                triple_ids = [compute_mdhash_id(str(triple)) for triple in triples]
                entitie_ids = list(
                    set(
                        [
                            compute_mdhash_id(obj)
                            for triple in triples
                            for id, obj in enumerate(triple)
                            if id % 2 == 0
                        ]
                    )
                )

            num_to_retrieve = self.global_config.retrieval_top_k
            link_top_k = self.global_config.linking_top_k
            passage_node_weight = self.global_config.passage_node_weight
            chunks_to_retrieve_ppr_seed = self.global_config.chunks_to_retrieve_ppr_seed
            directional_ppr = self.global_config.directional_ppr
            damping = self.global_config.damping

            retrieval_results: list[QuerySolution] = []

            for query in tqdm(queries, desc="Retrieving", total=len(queries)):
                query_result = await self._vector_store_fact.query(
                    query, allowd__point_ids=triple_ids, top_k=num_to_retrieve
                )
                if query_result.is_error():
                    return query_result.propagate_exception()
                query_fact_scores: list[SimilarNodes] = [
                    n for n in query_result.get_ok()
                ]

                rerank_start = time.time()
                rr = await self._rerank_facts(query, query_fact_scores, model)
                if rr.is_error():
                    return rr.propagate_exception()
                top_k_fact_indices, top_k_facts, _ = rr.get_ok()
                self.rerank_time += time.time() - rerank_start

                if not top_k_facts:
                    # pure DPR fallback
                    logger.warning("No facts after rerank; using DPR results.")
                    dpr = await self._search_passages(
                        query, k=num_to_retrieve, allowed_chunks=ids_chunks
                    )
                    if dpr.is_error():
                        return dpr.propagate_exception()
                    id_and_scores = dpr.get_ok()
                else:
                    # graph path (currently DPR-shaped shim)
                    gs = await self._graph_search_with_fact_entities(
                        query=query,
                        link_top_k=link_top_k,
                        query_fact_scores=top_k_fact_indices,
                        top_k_facts=top_k_facts,
                        num_to_retrieve=num_to_retrieve,
                        chunks_to_retrieve_ppr_seed=chunks_to_retrieve_ppr_seed,
                        directional_ppr=directional_ppr,
                        damping=damping,
                        passage_node_weight=passage_node_weight,
                        allowed_chunks=ids_chunks,
                        allowed_entities=entitie_ids,
                    )
                    if gs.is_error():
                        return gs.propagate_exception()
                    id_and_scores = gs.get_ok()

                if len(id_and_scores) == 0:
                    return Result.Err(Exception("Failed to retrieve Any Chunks"))
                result = await self._state_store.fetch_chunks_by_ids(
                    hash_ids=[id for id in id_and_scores.keys()]
                )
                if result.is_error():
                    return result.propagate_exception()

                docs = [
                    Chunk(
                        id=doc.idx,
                        content=doc.passage,
                        score=id_and_scores[doc.idx],
                        metadata=doc.metadata,
                    )
                    for doc in result.get_ok().docs
                ]

                docs.sort(key=lambda x: x.score, reverse=True)
                retrieval_results.append(QuerySolution(question=query, docs=docs))

            self.all_retrieval_time += time.time() - retrieve_start_time
            logger.info(f"Total Retrieval Time {self.all_retrieval_time:.2f}s")
            logger.info(f"Total Recognition Memory Time {self.rerank_time:.2f}s")
            logger.info(f"Total PPR Time {self.ppr_time:.2f}s")
            logger.info(
                f"Total Misc Time {self.all_retrieval_time - (self.rerank_time + self.ppr_time):.2f}s"
            )
            return Result.Ok(retrieval_results)

    async def retrieve_dpr(
        self,
        queries: list[str],
        metadata: dict[str, list[str] | list[int] | list[float]] | None = None,
        num_to_retrieve: int | None = None,
    ) -> Result[list[QuerySolution]]:
        with self.tracer.start_as_current_span("retrieval-dens"):
            retrieve_start_time = time.time()
            if num_to_retrieve is None:
                num_to_retrieve = self.global_config.retrieval_top_k

            ids_chunks: list[str] | None = None

            if metadata is not None:
                result = await self._state_store.load_openie_info_with_metadata(
                    metadata=metadata
                )
                if result.is_error():
                    return result.propagate_exception()
                docs = result.get_ok().docs

                ids_chunks = [doc.idx for doc in docs]

            out: list[QuerySolution] = []
            for query in tqdm(queries, desc="Retrieving (DPR)", total=len(queries)):
                dpr = await self._search_passages(
                    query, k=num_to_retrieve, allowed_chunks=ids_chunks
                )
                if dpr.is_error():
                    return dpr.propagate_exception()

                id_and_scores = dpr.get_ok()
                result = await self._state_store.fetch_chunks_by_ids(
                    hash_ids=[id for id in id_and_scores.keys()]
                )
                if result.is_error():
                    return result.propagate_exception()

                docs = [
                    Chunk(
                        id=doc.idx,
                        content=doc.passage,
                        score=id_and_scores[doc.idx],
                        metadata=doc.metadata,
                    )
                    for doc in result.get_ok().docs
                ]
                docs.sort(key=lambda x: x.score, reverse=True)
                out.append(QuerySolution(question=query, docs=docs))

            self.all_retrieval_time += time.time() - retrieve_start_time
            logger.info(f"Total Retrieval Time {self.all_retrieval_time:.2f}s")
            return Result.Ok(out)

    async def rag_qa(
        self,
        queries: list[str] | list[QuerySolution],
        metadata: dict[str, list[str] | list[int] | list[float]] | None = None,
    ) -> Result[tuple[list[QuerySolution], list[str]]]:
        with self.tracer.start_as_current_span("retrieval-question-answering"):
            if isinstance(queries[0], str):
                queries_result = await self.retrieve(queries=queries, metadata=metadata)  # type: ignore
                if queries_result.is_error():
                    return queries_result.propagate_exception()
                queries = queries_result.get_ok()

            assert isinstance(queries[0], QuerySolution)
            result = await self._qa(queries)  # type: ignore
            if result.is_error():
                return result.propagate_exception()
            queries_solutions, all_response_message = result.get_ok()
            return Result.Ok((queries_solutions, all_response_message))

    async def rag_qa_dpr(
        self,
        queries: list[str] | list[QuerySolution],
        metadata: dict[str, list[str] | list[int] | list[float]] | None = None,
    ) -> Result[tuple[list[QuerySolution], list[str]]]:
        with self.tracer.start_as_current_span("retrieval-dense-question-answering"):
            if isinstance(queries[0], str):
                queries_result = await self.retrieve_dpr(
                    queries=[q for q in queries if isinstance(q, str)],
                    metadata=metadata,
                )
                if queries_result.is_error():
                    return queries_result.propagate_exception()
                queries = queries_result.get_ok()

            result = await self._qa(queries)  # type: ignore
            if result.is_error():
                return result.propagate_exception()
            queries_solutions, all_response_message = result.get_ok()  # type: ignore
            return Result.Ok((queries_solutions, all_response_message))

    async def _qa(
        self, queries: list[QuerySolution]
    ) -> Result[tuple[list[QuerySolution], list[str]]]:
        with self.tracer.start_as_current_span("QA-Call"):
            all_qa_messages: list[list[TextChatMessage]] = []

            for query_solution in tqdm(queries, desc="Collecting QA prompts"):
                retrieved_passages = query_solution.docs[: self.global_config.qa_top_k]

                prompt_user = ""
                for passage in retrieved_passages:
                    prompt_user += f"Retrived Information: {passage.content}\n\n"
                prompt_user += "Question: " + query_solution.question + "\nThought: "

                all_qa_messages.append(
                    [
                        TextChatMessage(
                            role="system", content=self.global_config.system_config
                        ),
                        TextChatMessage(role="user", content=prompt_user),
                    ]
                )
            all_qa_results = [
                self._llm.chat(qa_messages)
                for qa_messages in tqdm(all_qa_messages, desc="QA Reading")
            ]
            all_responses: list[str] = []
            for qa_run in all_qa_results:
                result = await qa_run
                if result.is_error():
                    return result.propagate_exception()
                all_responses.append(result.get_ok())

            queries_solutions: list[QuerySolution] = []
            for query_solution_idx, query_solution in tqdm(
                enumerate(queries), desc="Extraction Answers from LLM Response"
            ):
                response_content = all_responses[query_solution_idx]
                try:
                    pred_ans = response_content.split("Answer:")[1].strip()
                except Exception as e:
                    logger.warning(
                        f"Error parsing 'Answer:' from LLM response: {str(e)}"
                    )
                    pred_ans = response_content

                query_solution.answer = pred_ans
                queries_solutions.append(query_solution)

            return Result.Ok((queries_solutions, all_responses))

    async def _rerank_facts(
        self,
        query: str,
        query_fact_scores: list[SimilarNodes],
        model: str | None = None,
    ) -> Result[tuple[list[SimilarNodes], list[Triple], RerankLog]]:
        with self.tracer.start_as_current_span("rerank-facts"):
            link_top_k = self.global_config.linking_top_k

            if not query_fact_scores:
                logger.warning("No relevant Facts where retrived")
                return Result.Ok(
                    ([], [], RerankLog(facts_after_rerank=[], facts_before_rerank=[]))
                )

            # sort by score desc
            hits = sorted(query_fact_scores, key=lambda h: h.score, reverse=True)[
                :link_top_k
            ]

            # parse triples from payloads
            candidate_facts: list[Triple] = []
            for h in hits:
                try:
                    triple = literal_eval(h.payload)
                    candidate_facts.append(triple)
                except Exception as e:
                    logger.warning(f"Could not parse triple for fact {h.id}: {e}")

            logger.debug("facts for retrival")
            for fact in candidate_facts:
                logger.debug(fact)

            # run rerank filter on these facts
            result = await self._rerank_filter.rerank(
                query,
                candidate_facts,
                [i for i, _ in enumerate(hits)],
                len_after_rerank=link_top_k,
                model=model,
            )
            if result.is_error():
                return result.propagate_exception()

            top_ids, top_facts, _ = result.get_ok()

            rerank_log = RerankLog(
                facts_before_rerank=candidate_facts,
                facts_after_rerank=top_facts,
            )

            top_ids = [hits[i] for i in top_ids]
            if not top_facts:
                logger.warning("no top_facts after reranking")
                logger.warning("used retrival score as fallback")
                top_ids = hits
                top_facts = candidate_facts

            return Result.Ok((top_ids, top_facts, rerank_log))
