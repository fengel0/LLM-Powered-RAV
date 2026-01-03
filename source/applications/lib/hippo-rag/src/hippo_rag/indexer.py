import logging
from typing import cast
from collections import defaultdict
from core.que_runner import index_with_queue
from domain.rag.indexer.interface import (
    AsyncDocumentIndexer,
    DocumentSplitter,
)
from domain.rag.indexer.model import Document as IndexDocument, SplitNode
from domain.rag.model import Node as NodeWithScore

from core.result import Result
from core.hash import compute_mdhash_id
from domain.hippo_rag.interfaces import (
    EmbeddingStoreInterface,
    GraphDBInterface,
    IndexerInterface,
    OpenIEInterface,
    StateStore,
)
from domain.hippo_rag.model import (
    Document,
    DocumentCollection,
    Edge,
    NerRawOutput,
    Node,
    Triple,
    TripleRawOutput,
)
from opentelemetry import trace
from pydantic import BaseModel
from tqdm import tqdm

from hippo_rag.utils.misc_utils import (
    extract_entity_nodes,
    flatten_facts,
    reformat_openie_results,
    text_processing,
    text_processing_word,
)

logger = logging.getLogger(__name__)


class IndexerConfig(BaseModel):
    synonymy_edge_topk: int
    synonymy_edge_sim_threshold: float
    number_of_parallel_requests: int


CollectionFilterAttribute = "project"


class HippoRAGIndexer(IndexerInterface, AsyncDocumentIndexer):
    _vector_store_entity: EmbeddingStoreInterface
    _vector_store_chunk: EmbeddingStoreInterface
    _vector_store_fact: EmbeddingStoreInterface
    _graph: GraphDBInterface
    _state_store: StateStore
    _openie: OpenIEInterface
    _config: IndexerConfig
    _text_splitter: DocumentSplitter

    def __init__(
        self,
        vector_store_entity: EmbeddingStoreInterface,
        vector_store_chunk: EmbeddingStoreInterface,
        vector_store_fact: EmbeddingStoreInterface,
        graph: GraphDBInterface,
        state_store: StateStore,
        openie: OpenIEInterface,
        text_splitter: DocumentSplitter,
        config: IndexerConfig,
    ):
        self._vector_store_entity = vector_store_entity
        self._vector_store_chunk = vector_store_chunk
        self._vector_store_fact = vector_store_fact
        self._state_store = state_store
        self._graph = graph
        self._openie = openie
        self._config = config
        self._text_splitter = text_splitter
        self.tracer = trace.get_tracer("HippoRAGIndex")

        self.rerank_filter = filter

    async def create_document(
        self, doc: IndexDocument, collection: str | None = None
    ) -> Result[None]:
        metadata_filter = {CollectionFilterAttribute: collection} if collection else {}
        nodes = self._text_splitter.split_documents(
            doc=doc
        )

        async def _index_one(node: SplitNode) -> Result[None]:
            try:
                return await self.index(
                    docs=[node.content],
                    metadata={**node.metadata, **metadata_filter},
                    collection=collection,
                )
            except Exception as e:
                return Result.Err(e)

        return await index_with_queue(
            objects=nodes,
            workers=max(1, self._config.number_of_parallel_requests),
            index_one=_index_one,
        )

    async def update_document(
        self, doc: IndexDocument, collection: str | None = None
    ) -> Result[None]:
        result = await self.delete_document(doc_id=doc.id, collection=collection)
        if result.is_error():
            return result.propagate_exception()
        return await self.create_document(doc=doc, collection=collection)

    async def delete_document(
        self, doc_id: str, collection: str | None = None
    ) -> Result[None]:
        result = await self._state_store.load_openie_info_with_metadata(
            metadata={"doc_id": [doc_id]}
        )
        if result.is_error():
            return result.propagate_exception()
        docs = [doc.passage for doc in result.get_ok().docs]
        return await self.delete(docs=docs)

    async def find_similar_nodes(
        self,
        query: str,
        metadata: dict[str, list[str] | list[float] | list[int]] | None = None,
        collection: str | None = None,
    ) -> Result[list[NodeWithScore]]:
        allowed_chunks: list[str] | None = None

        if collection:
            if not metadata:
                metadata = {}
            metadata[CollectionFilterAttribute] = [collection]

        if metadata:
            result = await self._state_store.load_openie_info_with_metadata(
                metadata=metadata
            )
            if result.is_error():
                return result.propagate_exception()
            allowed_chunks = [doc.idx for doc in result.get_ok().docs]
            if len(allowed_chunks) == 0:
                return Result.Err(Exception("No Nodes found"))
        result = await self._vector_store_chunk.query(
            query=query, allowd__point_ids=allowed_chunks
        )
        if result.is_error():
            return result.propagate_exception()
        nodes = result.get_ok()
        idx = [compute_mdhash_id(node.payload) for node in nodes]

        result = await self._state_store.fetch_chunks_by_ids(idx)
        if result.is_error():
            return result.propagate_exception()

        chunks = result.get_ok().docs
        if len(chunks) == 0:
            return Result.Err(Exception("No Nodes found"))
        metadata_lookup = {x.idx: x.metadata for x in chunks}
        return Result.Ok(
            [
                NodeWithScore(
                    id=node.id,
                    content=node.payload,
                    metadata=metadata_lookup[compute_mdhash_id(node.payload)],
                    similarity=node.score,
                )
                for node in nodes
            ]
        )

    async def does_object_with_metadata_exist(
        self, metadata: dict[str, str | float | int], collection: str | None = None
    ) -> Result[bool]:
        metadata_filter: dict[str, list[str] | list[float] | list[int]] = (
            {CollectionFilterAttribute: [collection]} if collection else {}
        )
        for key in metadata.keys():
            metadata_filter[key] = [metadata[key]]  # type: ignore
        result = await self._state_store.load_openie_info_with_metadata(metadata_filter)
        if result.is_error():
            return result.propagate_exception()
        return Result.Ok(len(result.get_ok().docs) > 0)

    async def index(
        self,
        docs: list[str],
        metadata: dict[str, str | int | float] | None = None,
        collection: str | None = None,
    ) -> Result[None]:
        result = await self._index(docs, metadata, collection=collection)
        return result

    async def rebuild_graph_and_vector_stor(self):
        with self.tracer.start_as_current_span("index"):
            logger.info("Indexing Documents")
            offset = 0
            chunk_size = 5000
            while True:
                result = await self._state_store.load_openie_info(
                    offset=offset, chunk_size=chunk_size
                )
                if result.is_error():
                    result.propagate_exception()

                chunks = result.get_ok().docs

                if len(chunks) == 0:
                    break

                result = await self._vector_store_chunk.insert_strings(
                    [chunk.passage for chunk in chunks]
                )
                if result.is_error():
                    return result.propagate_exception()

                chunk_ids = [chunk.idx for chunk in chunks]
                new_chunks_with_id = {k.idx: k.passage for k in chunks}

                # clean triple
                chunk_triples = [chunk.extracted_triples for chunk in chunks]
                facts = flatten_facts(chunk_triples)
                entity_nodes, chunk_triple_entities = extract_entity_nodes(
                    chunk_triples
                )
                logger.debug(facts)
                logger.debug(entity_nodes)
                logger.info(f"found facts {len(facts)}")
                logger.info(f"found entities {len(entity_nodes)}")
                logger.info("Encoding Entities")

                result = await self._vector_store_entity.insert_strings(entity_nodes)
                if result.is_error():
                    return result.propagate_exception()
                logger.info("Encoding Facts")
                result = await self._vector_store_fact.insert_strings(
                    [str(fact) for fact in facts]
                )
                if result.is_error():
                    return result.propagate_exception()

                logger.info("Constructing Graph")
                node_to_node_stats: dict[tuple[str, str], float] = {}
                node_to_node_stats_result = await self._add_fact_edges(
                    chunk_ids, chunk_triples, node_to_node_stats
                )
                if node_to_node_stats_result.is_error():
                    return node_to_node_stats_result.propagate_exception()
                node_to_node_stats = node_to_node_stats_result.get_ok()

                result = await self._add_passage_edges(
                    chunk_ids, chunk_triple_entities, node_to_node_stats
                )
                if result.is_error():
                    return result.propagate_exception()

                num_new_chunks, node_to_node_stats = result.get_ok()
                logger.info(f"Found {num_new_chunks} new chunks to save into graph.")

                node_to_node_stats_result = await self._add_synonymy_edges(
                    node_to_node_stats, entity_nodes
                )
                if node_to_node_stats_result.is_error():
                    return node_to_node_stats_result.propagate_exception()
                node_to_node_stats = node_to_node_stats_result.get_ok()

                entities_to_create = {
                    compute_mdhash_id(entity): entity for entity in entity_nodes
                }

                node_to_node_stats_result = await self._augment_graph(
                    node_to_node_stats,
                    chunks=new_chunks_with_id,
                    entities=entities_to_create,
                )
                if node_to_node_stats_result.is_error():
                    return node_to_node_stats_result.propagate_exception()

                offset = offset + chunk_size
                logger.info(f"Proccessed {offset}")
        return Result.Ok()

    async def _index(
        self,
        docs: list[str],
        metadata: dict[str, str | int | float] | None = None,
        collection: str | None = None,
    ) -> Result[None]:
        with self.tracer.start_as_current_span("index"):
            logger.info("Indexing Documents")

            # 1. instert chunks
            result = await self._vector_store_chunk.insert_strings(docs)
            if result.is_error():
                return result.propagate_exception()

            # 2.  load all chunks
            chunks = {compute_mdhash_id(doc): doc for doc in docs}

            # 3. load existing Entity + Triple
            result = await self._graph.get_not_existing_nodes(list(chunks.keys()))
            if result.is_error():
                return result.propagate_exception()
            not_existing_hash_keys = result.get_ok()
            chunk_keys_to_process = set(not_existing_hash_keys)
            new_chunks_with_id = {k: chunks[k] for k in chunk_keys_to_process}

            # extrahieren entity + triple
            if len(chunk_keys_to_process) == 0:
                logger.info("no chunks to process")
                return Result.Ok()
            logger.info(f"{len(chunk_keys_to_process)} chunks to process")

            result = await self._openie.batch_openie(new_chunks_with_id)
            if result.is_error():
                return result.propagate_exception()
            new_ner_results_dict, new_triple_results_dict = result.get_ok()

            new_chunks = self._merge_openie_results(
                chunks_to_save=new_chunks_with_id,
                ner_results_dict=new_ner_results_dict,
                triple_results_dict=new_triple_results_dict,
                metadata=metadata,
            )
            result = await self._save_openie_results(new_chunks)
            if result.is_error():
                return result.propagate_exception()

            ner_results_chunks, triple_results_chunks = reformat_openie_results(
                new_chunks
            )

            logger.info(
                f"chunk_to_rows:{len(chunk_keys_to_process)} | ner_results_dict:{len(ner_results_chunks)} | triple_results_dict:{len(triple_results_chunks)}"
            )
            # dient nur zur pruefung das aus jedem chunk ner und triple extrahiert wurden
            assert (
                len(chunk_keys_to_process)
                == len(ner_results_chunks)
                == len(triple_results_chunks)
            )

            chunk_ids = list(chunk_keys_to_process)

            # clean triple
            chunk_triples = [chunk.extracted_triples for chunk in new_chunks]
            facts = flatten_facts(chunk_triples)
            entity_nodes, chunk_triple_entities = extract_entity_nodes(chunk_triples)

            logger.info(f"found facts {len(facts)}")
            logger.info(f"found entities {len(entity_nodes)}")
            logger.info("Encoding Entities")

            result = await self._vector_store_entity.insert_strings(entity_nodes)
            if result.is_error():
                return result.propagate_exception()
            logger.info("Encoding Facts")
            result = await self._vector_store_fact.insert_strings(
                [str(fact) for fact in facts]
            )
            if result.is_error():
                return result.propagate_exception()

            logger.info("Constructing Graph")
            node_to_node_stats: dict[tuple[str, str], float] = {}
            node_to_node_stats_result = await self._add_fact_edges(
                chunk_ids, chunk_triples, node_to_node_stats
            )
            if node_to_node_stats_result.is_error():
                return node_to_node_stats_result.propagate_exception()
            node_to_node_stats = node_to_node_stats_result.get_ok()

            result = await self._add_passage_edges(
                chunk_ids, chunk_triple_entities, node_to_node_stats
            )
            if result.is_error():
                return result.propagate_exception()

            num_new_chunks, node_to_node_stats = result.get_ok()
            if num_new_chunks > 0:
                logger.info(f"Found {num_new_chunks} new chunks to save into graph.")

                node_to_node_stats_result = await self._add_synonymy_edges(
                    node_to_node_stats, entity_nodes
                )
                if node_to_node_stats_result.is_error():
                    return node_to_node_stats_result.propagate_exception()
                node_to_node_stats = node_to_node_stats_result.get_ok()

                entities_to_create = {
                    compute_mdhash_id(entity): entity for entity in entity_nodes
                }

                node_to_node_stats_result = await self._augment_graph(
                    node_to_node_stats,
                    chunks=new_chunks_with_id,
                    entities=entities_to_create,
                )
                if node_to_node_stats_result.is_error():
                    return node_to_node_stats_result.propagate_exception()
            else:
                logger.warning("no new chunks is that right?")
                logger.warning(f"{node_to_node_stats}")
                logger.warning(f"chunk ids{chunk_ids}")
                logger.warning(f"triples {chunk_triples}")
            return Result.Ok()

    async def delete(self, docs: list[str]) -> Result[None]:
        with self.tracer.start_as_current_span("delete"):
            """
            Deletes the given documents from all data structures within the HippoRAG class.
            Note that triples and entities which are indexed from chunks that are not being removed will not be removed.

            Parameters:
                docs : List[str]
                    A list of documents to be deleted.
            """

            docs_to_delete = docs

            # Get ids for chunks to delete
            chunk_ids_to_delete: set[str] = set(
                [compute_mdhash_id(doc) for doc in docs_to_delete]
            )

            chunks_result = await self._state_store.fetch_chunks_by_ids(
                hash_ids=list(chunk_ids_to_delete)
            )
            if chunks_result.is_error():
                return chunks_result.propagate_exception()

            chunks = chunks_result.get_ok()
            if len(chunks.docs) == 0:
                return Result.Ok()

            triples_to_delete_flattend = flatten_facts(
                [doc.extracted_triples for doc in chunks.docs]
            )

            true_triples_to_delete: list[Triple] = []

            for triple in triples_to_delete_flattend:
                proc_triple = text_processing(triple)

                result = await self._state_store.triples_to_docs(proc_triple)
                if result.is_error():
                    return result.propagate_exception()
                doc_ids = set(result.get_ok())

                non_deleted_docs = doc_ids.difference(chunk_ids_to_delete)

                if len(non_deleted_docs) == 0:
                    true_triples_to_delete.append(triple)

            processed_true_triples_to_delete = true_triples_to_delete
            entities_to_delete, _ = extract_entity_nodes(
                [processed_true_triples_to_delete]
            )
            processed_true_triples_to_delete = flatten_facts(
                [processed_true_triples_to_delete]
            )

            triple_ids_to_delete: set[str] = set()
            for triple in processed_true_triples_to_delete:
                triple_ids_to_delete.update(compute_mdhash_id(str(triple)))

            # Filter out entities that appear in unaltered chunks
            ent_ids_to_delete: list[str] = []
            for ent in entities_to_delete:
                ent_ids_to_delete.append(compute_mdhash_id(ent))

            filtered_ent_ids_to_delete: list[str] = []

            for ent_node in ent_ids_to_delete:
                result = await self._state_store.ent_node_to_chunk(ent_node)
                if result.is_error():
                    result.propagate_exception()
                doc_ids: set[str] = set(result.get_ok())
                non_deleted_docs = doc_ids.difference(chunk_ids_to_delete)
                if len(non_deleted_docs) == 0:
                    filtered_ent_ids_to_delete.append(ent_node)

            logger.info(f"Deleting {len(chunk_ids_to_delete)} Chunks")
            logger.info(f"Deleting {len(triple_ids_to_delete)} Triples")
            logger.info(f"Deleting {len(filtered_ent_ids_to_delete)} Entities")

            result = await self._vector_store_entity.delete(filtered_ent_ids_to_delete)
            if result.is_error():
                return result.propagate_exception()
            result = await self._vector_store_fact.delete(list(triple_ids_to_delete))
            if result.is_error():
                return result.propagate_exception()
            result = await self._vector_store_chunk.delete(list(chunk_ids_to_delete))
            if result.is_error():
                return result.propagate_exception()

            # Delete Nodes from Graph
            result = await self._graph.delete_vertices(
                list(filtered_ent_ids_to_delete) + list(chunk_ids_to_delete)
            )
            if result.is_error():
                return result.propagate_exception()

            return await self._state_store.delete_chunks(list(chunk_ids_to_delete))

    def _merge_openie_results(
        self,
        chunks_to_save: dict[str, str],
        ner_results_dict: dict[str, NerRawOutput],
        triple_results_dict: dict[str, TripleRawOutput],
        metadata: dict[str, str | int | float] | None = None,
    ) -> list[Document]:
        with self.tracer.start_as_current_span("merge-openie-results"):
            """
            Merges OpenIE extraction results with corresponding passage and metadata.

            This function integrates the OpenIE extraction results, including named-entity
            recognition (NER) entities and triples, with their respective text passages
            using the provided chunk keys. The resulting merged data is appended to
            the `all_openie_info` list containing dictionaries with combined and organized
            data for further processing or storage.

            Parameters:
                all_openie_info (List[dict]): A list to hold dictionaries of merged OpenIE
                    results and metadata for all chunks.
                chunks_to_save (Dict[str, dict]): A dict of chunk identifiers (keys) to process
                    and merge OpenIE results to dictionaries with `hash_id` and `content` keys.
                ner_results_dict (Dict[str, NerRawOutput]): A dictionary mapping chunk keys
                    to their corresponding NER extraction results.
                triple_results_dict (Dict[str, TripleRawOutput]): A dictionary mapping chunk
                    keys to their corresponding OpenIE triple extraction results.

            Returns:
                List[dict]: The `all_openie_info` list containing dictionaries with merged
                OpenIE results, metadata, and the passage content for each chunk.

            """
            logger.info("merge openie results")
            new_documents: list[Document | None] = [None] * len(chunks_to_save)

            for (
                index,
                (chunk_key, row),
            ) in enumerate(chunks_to_save.items()):
                passage = row
                extracted_triples = [
                    text_processing(t) for t in triple_results_dict[chunk_key].triples
                ]

                new_documents[index] = Document(
                    idx=chunk_key,
                    passage=passage,
                    extracted_entities=ner_results_dict[chunk_key].unique_entities,
                    extracted_triples=extracted_triples,
                    metadata=metadata or {},
                )

            return cast(list[Document], new_documents)

    async def _add_fact_edges(
        self,
        chunk_ids: list[str],
        chunk_triples: list[list[Triple]],
        node_to_node_stats: dict[tuple[str, str], float],
    ) -> Result[dict[tuple[str, str], float]]:
        with self.tracer.start_as_current_span("add-fact-edges"):
            """
            Adds fact edges from given triples to the graph.

            The method processes chunks of triples, computes unique identifiers
            for entities and relations, and updates various internal statistics
            to build and maintain the graph structure. Entities are uniquely
            identified and linked based on their relationships.

            Parameters:
                chunk_ids: List[str]
                    A list of unique identifiers for the chunks being processed.
                chunk_triples: List[Tuple]
                    A list of tuples representing triples to process. Each triple
                    consists of a subject, predicate, and object.

            Raises:
                Does not explicitly raise exceptions within the provided function logic.
            """
            names_result = await self._graph.get_values_from_attributes("hash_id")
            if names_result.is_error():
                return names_result.propagate_exception()
            logger.info("Adding OpenIE triples to graph.")

            for chunk_key, triples in tqdm(zip(chunk_ids, chunk_triples)):
                entities_in_chunk: set[str] = set()
                chunk_id_result = await self._graph.get_node_by_hash(chunk_key)
                if chunk_id_result.is_error():
                    return chunk_id_result.propagate_exception()

                if chunk_id_result.get_ok() is None:
                    for triple in triples:
                        triple_tupel = tuple(triple)

                        node_key = compute_mdhash_id(content=triple_tupel[0])
                        node_2_key = compute_mdhash_id(content=triple_tupel[2])

                        node_to_node_stats[(node_key, node_2_key)] = (
                            node_to_node_stats.get((node_key, node_2_key), 0.0) + 1
                        )
                        node_to_node_stats[(node_2_key, node_key)] = (
                            node_to_node_stats.get((node_2_key, node_key), 0.0) + 1
                        )

                        entities_in_chunk.add(node_key)
                        entities_in_chunk.add(node_2_key)

            return Result.Ok(node_to_node_stats)

    async def _add_passage_edges(
        self,
        chunk_ids: list[str],
        chunk_triple_entities: list[list[str]],
        node_to_node_stats: dict[tuple[str, str], float],
    ) -> Result[tuple[int, dict[tuple[str, str], float]]]:
        with self.tracer.start_as_current_span("add-passage-edges"):
            """
            Adds edges connecting passage nodes to phrase nodes in the graph.

            This method is responsible for iterating through a list of chunk identifiers
            and their corresponding triple entities. It calculates and adds new edges
            between the passage nodes (defined by the chunk identifiers) and the phrase
            nodes (defined by the computed unique hash IDs of triple entities). The method
            also updates the node-to-node statistics map and keeps count of newly added
            passage nodes.

            Parameters:
                chunk_ids : List[str]
                    A list of identifiers representing passage nodes in the graph.
                chunk_triple_entities : List[List[str]]
                    A list of lists where each sublist contains entities (strings) associated
                    with the corresponding chunk in the chunk_ids list.

            Returns:
                int
                    The number of new passage nodes added to the graph.
            """

            num_new_chunks = 0
            logger.info("Connecting passage nodes to phrase nodes.")

            for idx, chunk_key in tqdm(enumerate(chunk_ids)):
                chunk_key_result = await self._graph.get_node_by_hash(chunk_key)
                if chunk_key_result.is_error():
                    return chunk_key_result.propagate_exception()
                if chunk_key_result.get_ok() is None:
                    for chunk_ent in chunk_triple_entities[idx]:
                        node_key = compute_mdhash_id(chunk_ent)

                        node_to_node_stats[(chunk_key, node_key)] = 1.0

                    num_new_chunks += 1

            return Result.Ok((num_new_chunks, node_to_node_stats))

    async def _augment_graph(
        self,
        node_to_node_stats: dict[tuple[str, str], float],
        chunks: dict[str, str],
        entities: dict[str, str],
    ) -> Result[dict[tuple[str, str], float]]:
        with self.tracer.start_as_current_span("augment-graph"):
            """
            Provides utility functions to augment a graph by adding new nodes and edges.
            It ensures that the graph structure is extended to include additional components,
            and logs the completion status along with printing the updated graph information.
            """

            result = await self._add_new_nodes(chunks=chunks, entities=entities)
            if result.is_error():
                return result.propagate_exception()
            node_to_node_stats_result = await self._add_new_edges(node_to_node_stats)
            logger.info("Graph construction completed!")
            return node_to_node_stats_result

    async def _add_synonymy_edges(
        self,
        node_to_node_stats: dict[tuple[str, str], float],
        entity_nodes: list[str],
        collection: str | None = None,
    ) -> Result[dict[tuple[str, str], float]]:
        with self.tracer.start_as_current_span("add-synonymy-edges"):
            """
                Adds synonymy edges between similar nodes in the graph to enhance connectivity by identifying and linking synonym entities.

                This method performs key operations to compute and add synonymy edges. It first retrieves embeddings for all nodes, then conducts
                a nearest neighbor (KNN) search to find similar nodes. These similar nodes are identified based on a score threshold, and edges
                are added to represent the synonym relationship.

                Attributes:
                    entity_id_to_row: dict (populated within the function). Maps each entity ID to its corresponding row data, where rows
                                      contain `content` of entities used for comparison.
                    entity_embedding_store: Manages retrieval of texts and embeddings for all rows related to entities.
                    global_config: Configuration object that defines parameters such as `synonymy_edge_topk`, `synonymy_edge_sim_threshold`,
                                   `synonymy_edge_query_batch_size`, and `synonymy_edge_key_batch_size`.
                    node_to_node_stats: dict. Stores scores for edges between nodes representing their relationship.

                """
            logger.info("Expanding graph with synonymy edges")

            entity_node_keys = list(compute_mdhash_id(node) for node in entity_nodes)
            hash_to_entity = {compute_mdhash_id(node): node for node in entity_nodes}

            logger.info(
                f"Performing KNN retrieval for each phrase nodes ({len(entity_node_keys)})."
            )

            entitie_ids: list[str] | None = None
            if collection:
                result = await self._state_store.load_openie_info_with_metadata(
                    metadata={CollectionFilterAttribute: [collection]}
                )
                if result.is_error():
                    return result.propagate_exception()
                docs = result.get_ok().docs
                triples = flatten_facts([doc.extracted_triples for doc in docs])

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

            # Here we build synonymy edges only between newly inserted phrase nodes and all phrase nodes in the storage to reduce cost for incremental graph updates
            query_node_key2knn_node_keys_result = (
                await self._vector_store_entity.knn_by_ids(
                    query_ids=entity_node_keys,
                    top_k=self._config.synonymy_edge_topk,
                    min_similarity=self._config.synonymy_edge_sim_threshold,
                    allowd__point_ids=entitie_ids,
                )
            )
            if query_node_key2knn_node_keys_result.is_error():
                return query_node_key2knn_node_keys_result.propagate_exception()
            query_node_key2knn_node_keys = query_node_key2knn_node_keys_result.get_ok()

            num_synonym_triple = 0

            for node_key in tqdm(
                query_node_key2knn_node_keys.keys(),
                total=len(query_node_key2knn_node_keys),
            ):
                entity = hash_to_entity[node_key]

                if len(text_processing_word(entity)) <= 2:
                    continue

                nns = query_node_key2knn_node_keys[node_key]
                num_nns = 0
                for node in nns:
                    nn_phrase = node.payload

                    if node.id != node_key and nn_phrase:
                        sim_edge = (node_key, str(node.id))
                        num_synonym_triple += 1
                        # Need to seriously discuss on this -> from original code i think it is fine
                        node_to_node_stats[sim_edge] = node.score
                        num_nns += 1

                # synonym_candidates.append((node_key, synonyms))
            return Result.Ok(node_to_node_stats)

    async def _add_new_nodes(
        self,
        chunks: dict[str, str],
        entities: dict[str, str],
    ) -> Result[None]:
        with self.tracer.start_as_current_span("add-new-graphs"):
            """
            Adds new nodes to the graph from entity and passage embedding stores based on their attributes.

            This method identifies and adds new nodes to the graph by comparing existing nodes
            in the graph and nodes retrieved from the entity embedding store and the passage
            embedding store. The method checks attributes and ensures no duplicates are added.
            New nodes are prepared and added in bulk to optimize graph updates.
            """
            result = await self._graph.get_not_existing_nodes(list(entities.keys()))
            if result.is_error():
                return result.propagate_exception()
            entities_to_create = result.get_ok()

            new_nodes: list[Node] = []

            for node_id, node in chunks.items():
                new_nodes.append(
                    Node(
                        hash_id=node_id,
                        content=node,
                        node_type="chunk",
                    )
                )

            for node_id in entities_to_create:
                new_nodes.append(
                    Node(
                        hash_id=node_id,
                        content=entities[node_id],
                        node_type="entity",
                    )
                )

            if len(new_nodes) > 0:
                return await self._graph.add_nodes(nodes=new_nodes)
            return Result.Ok()

    async def _add_new_edges(
        self,
        node_to_node_stats: dict[tuple[str, str], float],
    ) -> Result[dict[tuple[str, str], float]]:
        with self.tracer.start_as_current_span("add-new-edges"):
            """
            Processes edges from `node_to_node_stats` to add them into a graph object while
            managing adjacency lists, validating edges, and logging invalid edge cases.
            """

            graph_adj_list: dict[str, dict[str, float]] = defaultdict(dict)
            graph_inverse_adj_list: dict[str, dict[str, float]] = defaultdict(dict)
            edge_source_node_keys: list[str] = []
            edge_target_node_keys: list[str] = []
            edge_metadata: list[dict[str, str | float | int]] = []

            for edge, weight in node_to_node_stats.items():
                if edge[0] == edge[1]:
                    continue
                graph_adj_list[edge[0]][edge[1]] = weight
                graph_inverse_adj_list[edge[1]][edge[0]] = weight

                edge_source_node_keys.append(edge[0])
                edge_target_node_keys.append(edge[1])
                edge_metadata.append({"weight": weight})

            # valid_edges: list[tuple[str, str]] = []
            # valid_weights: dict[str, list[float | int | str]] = {"weight": []}
            edges: list[Edge] = []
            names_result = await self._graph.get_values_from_attributes(key="hash_id")
            if names_result.is_error():
                return names_result.propagate_exception()
            names = names_result.get_ok()
            current_node_ids = set(names)
            for source_node_id, target_node_id, edge_d in zip(
                edge_source_node_keys, edge_target_node_keys, edge_metadata
            ):
                if (
                    source_node_id in current_node_ids
                    and target_node_id in current_node_ids
                ):
                    edges.append(
                        Edge(
                            src=source_node_id,
                            dst=target_node_id,
                            weight=float(edge_d.get("weight", 1.0)),
                        )
                    )
                else:
                    logger.warning(
                        f"Edge {source_node_id} -> {target_node_id} is not valid."
                    )
            result = await self._graph.add_edges(edges=edges)
            if result.is_error():
                return result.propagate_exception()
            return Result.Ok(node_to_node_stats)

    ### Functions to remove because unneeded if a database is used

    async def _load_existing_openie(
        self, chunk_keys: list[str]
    ) -> Result[tuple[list[Document], set[str]]]:
        with self.tracer.start_as_current_span("load-existing-openie"):
            """
            Loads existing OpenIE results from the specified file if it exists and combines
            them with new content while standardizing indices. If the file does not exist or
            is configured to be re-initialized from scratch with the flag `force_openie_from_scratch`,
            it prepares new entries for processing.

            Args:
                chunk_keys (List[str]): A list of chunk keys that represent identifiers
                                         for the content to be processed.

            Returns:
                Tuple[List[dict], Set[str]]: A tuple where the first element is the existing OpenIE
                                             information (if any) loaded from the file, and the
                                             second element is a set of chunk keys that still need to
                                             be saved or processed.
            """

            # combine openie_results with contents already in file, if file exists
            chunk_keys_to_save: set[str] = set()
            renamed_openie_info: list[Document] = []

            result = await self._state_store.load_openie_info()
            if result.is_error():
                return result.propagate_exception()

            all_openie_info = result.get_ok()
            for openie_info in all_openie_info.docs:
                renamed_openie_info.append(openie_info)

            all_openie_info = renamed_openie_info

            existing_openie_keys = set([info.idx for info in all_openie_info])

            for chunk_key in chunk_keys:
                if chunk_key not in existing_openie_keys:
                    chunk_keys_to_save.add(chunk_key)

            return Result.Ok((all_openie_info, chunk_keys_to_save))

    async def _save_openie_results(
        self, all_openie_info: list[Document]
    ) -> Result[None]:
        with self.tracer.start_as_current_span("save-existing-openie"):
            return await self._state_store.store_openie_info(
                DocumentCollection(docs=all_openie_info)
            )
