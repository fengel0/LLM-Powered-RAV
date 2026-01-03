import logging
from unittest.mock import Mock, patch, AsyncMock

from core.logger import init_logging

from core.result import Result
from domain.file_converter.model import TextFragement
from domain.rag.indexer.model import Document as RAGDocument
from domain.hippo_rag.model import (
    Document,
    DocumentCollection,
    NerRawOutput,
    TripleRawOutput,
    Node,
)
from domain.hippo_rag.interfaces import (
    EmbeddingStoreInterface,
    GraphDBInterface,
    StateStore,
    OpenIEInterface,
)
from domain.rag.indexer.interface import DocumentSplitter
from domain.rag.indexer.model import SplitNode

from hippo_rag.indexer import HippoRAGIndexer, IndexerConfig
from domain_test import AsyncTestBase

init_logging("debug")
logger = logging.getLogger(__name__)


# ----------------------------- helpers -----------------------------


class DocumentSplitterDummy(DocumentSplitter):
    def split_documents(self, doc: RAGDocument) -> list[SplitNode]:
        if isinstance(doc.content, str):
            return [SplitNode(id="", content=doc.content, metadata=doc.metadata)]
        return [
            SplitNode(id="", content=fragement.text, metadata=doc.metadata)
            for page in doc.content
            for fragement in page.document_fragements
            if isinstance(fragement, TextFragement)
        ]


def _default_config() -> IndexerConfig:
    return IndexerConfig(
        synonymy_edge_topk=10,
        synonymy_edge_sim_threshold=0.5,
        number_of_parallel_requests=4,
    )


def _make_common_mocks():
    # async stores
    vs_entity: AsyncMock = AsyncMock(spec=EmbeddingStoreInterface)
    vs_chunk: AsyncMock = AsyncMock(spec=EmbeddingStoreInterface)
    vs_fact: AsyncMock = AsyncMock(spec=EmbeddingStoreInterface)

    state: AsyncMock = AsyncMock(spec=StateStore)
    openie: AsyncMock = AsyncMock(spec=OpenIEInterface)

    graph: AsyncMock = AsyncMock(spec=GraphDBInterface)
    graph.get_values_from_attributes.return_value = Result.Ok([])
    graph.get_vs_map.return_value = Result.Ok({})
    graph.add_nodes.return_value = Result.Ok(None)
    graph.add_edges.return_value = Result.Ok(None)
    graph.delete_vertices.return_value = Result.Ok(None)
    graph.get_node_by_hash.return_value = Result.Ok(None)
    graph.get_not_existing_nodes.return_value = Result.Ok([])

    # state store defaults
    state.ent_node_to_chunk.return_value = Result.Ok([])
    state.triples_to_docs.return_value = Result.Ok([])
    state.load_openie_info_with_metadata.return_value = Result.Ok(
        DocumentCollection(docs=[])
    )
    state.fetch_chunks_by_ids.return_value = Result.Ok(DocumentCollection(docs=[]))
    state.delete_chunks.return_value = Result.Ok(None)

    # indexer-store defaults
    vs_entity.insert_strings.return_value = Result.Ok(None)
    vs_fact.insert_strings.return_value = Result.Ok(None)
    vs_chunk.insert_strings.return_value = Result.Ok(None)
    vs_entity.delete.return_value = Result.Ok(None)
    vs_fact.delete.return_value = Result.Ok(None)
    vs_chunk.delete.return_value = Result.Ok(None)

    return vs_entity, vs_chunk, vs_fact, state, openie, graph


# ================================ tests ================================


class TestHippoRAGInit(AsyncTestBase):
    __test__ = True
    """Init tests can stay sync"""

    def setup_method_sync(self, test_name: str):
        (
            self.mock_vector_store_entity,
            self.mock_vector_store_chunk,
            self.mock_vector_store_fact,
            self.mock_state_store,
            self.mock_openie,
            self.mock_graph,
        ) = _make_common_mocks()
        self.config = _default_config()

    def test_init_success(self):
        hippo_rag = HippoRAGIndexer(
            vector_store_entity=self.mock_vector_store_entity,
            vector_store_chunk=self.mock_vector_store_chunk,
            vector_store_fact=self.mock_vector_store_fact,
            graph=self.mock_graph,
            state_store=self.mock_state_store,
            openie=self.mock_openie,
            config=self.config,
            text_splitter=DocumentSplitterDummy(),
        )

        assert hippo_rag._vector_store_entity == self.mock_vector_store_entity
        assert hippo_rag._vector_store_chunk == self.mock_vector_store_chunk
        assert hippo_rag._vector_store_fact == self.mock_vector_store_fact
        assert hippo_rag._graph == self.mock_graph
        assert hippo_rag._state_store == self.mock_state_store
        assert hippo_rag._openie == self.mock_openie
        assert hippo_rag._config == self.config


class TestHippoRAGIndex(AsyncTestBase):
    """Async tests for indexing"""

    __test__ = True

    def setup_method_sync(self, test_name: str):
        (
            self.mock_vector_store_entity,
            self.mock_vector_store_chunk,
            self.mock_vector_store_fact,
            self.mock_state_store,
            self.mock_openie,
            self.mock_graph,
        ) = _make_common_mocks()
        self.config = _default_config()
        self.hippo_rag = HippoRAGIndexer(
            vector_store_entity=self.mock_vector_store_entity,
            vector_store_chunk=self.mock_vector_store_chunk,
            vector_store_fact=self.mock_vector_store_fact,
            graph=self.mock_graph,
            state_store=self.mock_state_store,
            openie=self.mock_openie,
            config=self.config,
            text_splitter=DocumentSplitterDummy(),
        )
        self.test_docs = ["Document 1 content", "Document 2 content"]

    @patch("hippo_rag.indexer.compute_mdhash_id")
    @patch("hippo_rag.indexer.reformat_openie_results")
    @patch("hippo_rag.indexer.extract_entity_nodes")
    @patch("hippo_rag.indexer.flatten_facts")
    @patch("hippo_rag.indexer.text_processing")
    async def test_index_basic_flow(
        self,
        mock_text_processing,
        mock_flatten_facts,
        mock_extract_entity_nodes,
        mock_reformat_openie,
        mock_hash,
    ):
        def mock_hash_func(*args, **kwargs):
            content = kwargs.get("content") or args[0]
            if content == "Document 1 content":
                return "chunk-1"
            elif content == "Document 2 content":
                return "chunk-2"
            elif content == "entity1":
                return "entity-hash-1"
            elif content == "entity2":
                return "entity-hash-2"
            elif content == "entity3":
                return "entity-hash-3"
            else:
                return f"hash-{hash(str(content))}"

        mock_hash.side_effect = mock_hash_func

        self.mock_graph.get_not_existing_nodes.return_value = Result.Ok(
            ["chunk-1", "chunk-2"]
        )
        self.hippo_rag._add_synonymy_edges = AsyncMock(return_value=Result.Ok({}))
        self.hippo_rag._augment_graph = AsyncMock(return_value=Result.Ok({}))

        mock_text_processing.side_effect = lambda x: x
        mock_extract_entity_nodes.return_value = (
            ["entity1", "entity2", "entity3"],
            [["entity1", "entity2"], ["entity3"]],
        )
        mock_flatten_facts.return_value = [
            ("entity1", "relates_to", "entity2"),
            ("entity3", "is", "thing"),
        ]

        mock_ner = {
            "chunk-1": NerRawOutput(
                chunk_id="chunk-1",
                unique_entities=["entity1", "entity2"],
                response="",
                metadata={},
            ),
            "chunk-2": NerRawOutput(
                chunk_id="chunk-2",
                unique_entities=["entity3"],
                response="",
                metadata={},
            ),
        }
        mock_triples = {
            "chunk-1": TripleRawOutput(
                chunk_id="chunk-1",
                response="",
                metadata={},
                triples=[("entity1", "relates_to", "entity2")],
            ),
            "chunk-2": TripleRawOutput(
                chunk_id="chunk-2",
                response="",
                metadata={},
                triples=[("entity3", "is", "thing")],
            ),
        }
        self.mock_openie.batch_openie.return_value = Result.Ok((mock_ner, mock_triples))

        def _merge_side_effect(
            chunks_to_save, ner_results_dict, triple_results_dict, metadata
        ):
            return [
                Document(
                    idx="chunk-1",
                    passage=self.test_docs[0],
                    extracted_entities=mock_ner["chunk-1"].unique_entities,
                    extracted_triples=mock_triples["chunk-1"].triples,
                    metadata=metadata or {},
                ),
                Document(
                    idx="chunk-2",
                    passage=self.test_docs[1],
                    extracted_entities=mock_ner["chunk-2"].unique_entities,
                    extracted_triples=mock_triples["chunk-2"].triples,
                    metadata=metadata or {},
                ),
            ]

        self.hippo_rag._merge_openie_results = Mock(side_effect=_merge_side_effect)
        self.hippo_rag._save_openie_results = AsyncMock(return_value=Result.Ok(None))

        mock_reformat_openie.return_value = (
            [
                NerRawOutput(
                    chunk_id="chunk-1",
                    response="",
                    metadata={},
                    unique_entities=["entity1", "entity2"],
                ),
                NerRawOutput(
                    chunk_id="chunk-2",
                    response="",
                    metadata={},
                    unique_entities=["entity3"],
                ),
            ],
            [
                TripleRawOutput(
                    chunk_id="chunk-1",
                    response="",
                    metadata={},
                    triples=[("entity1", "relates_to", "entity2")],
                ),
                TripleRawOutput(
                    chunk_id="chunk-2",
                    response="",
                    metadata={},
                    triples=[("entity3", "is", "thing")],
                ),
            ],
        )

        self.hippo_rag._add_fact_edges = AsyncMock(
            return_value=Result.Ok({("a", "b"): 1.0})
        )
        self.hippo_rag._add_passage_edges = AsyncMock(
            return_value=Result.Ok((2, {("c", "d"): 1.0}))
        )

        result = await self.hippo_rag.index(self.test_docs)
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()

        self.mock_vector_store_chunk.insert_strings.assert_awaited_once_with(
            self.test_docs
        )
        self.mock_openie.batch_openie.assert_awaited_once()
        self.hippo_rag._merge_openie_results.assert_called_once()
        self.hippo_rag._save_openie_results.assert_awaited_once()
        self.mock_vector_store_entity.insert_strings.assert_awaited_once()
        self.mock_vector_store_fact.insert_strings.assert_awaited_once()
        self.hippo_rag._add_fact_edges.assert_awaited_once()
        self.hippo_rag._add_passage_edges.assert_awaited_once()

    @patch("hippo_rag.indexer.compute_mdhash_id")
    async def test_index_triggers_synonymy_and_augment_when_new_chunks(self, mock_hash):
        def fake_hash(*args, **kwargs):
            v = kwargs.get("content") or (args[0] if args else None)
            if v == "d1":
                return "chunk-1"
            return f"h-{v}"

        mock_hash.side_effect = fake_hash
        self.mock_graph.get_not_existing_nodes.return_value = Result.Ok(["chunk-1"])

        mock_ner = {
            "chunk-1": NerRawOutput(
                chunk_id="chunk-1",
                response="",
                metadata={},
                unique_entities=["entity1"],
            )
        }
        mock_triples = {
            "chunk-1": TripleRawOutput(
                chunk_id="chunk-1",
                response="",
                metadata={},
                triples=[("e1", "is", "x")],
            )
        }
        self.mock_openie.batch_openie.return_value = Result.Ok((mock_ner, mock_triples))

        self.hippo_rag._merge_openie_results = Mock(
            return_value=[
                Document(
                    idx="chunk-1",
                    passage="d1",
                    extracted_entities=["entity1"],
                    extracted_triples=[("e1", "is", "x")],
                    metadata={},
                )
            ]
        )

        with (
            patch("hippo_rag.indexer.reformat_openie_results") as mock_refmt,
            patch("hippo_rag.indexer.extract_entity_nodes") as mock_extract,
            patch("hippo_rag.indexer.flatten_facts") as mock_flatten,
            patch("hippo_rag.indexer.text_processing") as mock_tp,
        ):
            mock_refmt.return_value = (
                [
                    NerRawOutput(
                        chunk_id="chunk-1",
                        response="",
                        metadata={},
                        unique_entities=["entity1"],
                    )
                ],
                [
                    TripleRawOutput(
                        chunk_id="chunk-1",
                        response="",
                        metadata={},
                        triples=[("e1", "is", "x")],
                    )
                ],
            )
            mock_tp.side_effect = lambda x: x
            mock_extract.return_value = (["entity1"], [["entity1"]])
            mock_flatten.return_value = [("e1", "is", "x")]

            self.hippo_rag._add_fact_edges = AsyncMock(
                return_value=Result.Ok({("n1", "n2"): 1.0})
            )
            self.hippo_rag._add_passage_edges = AsyncMock(
                return_value=Result.Ok((1, {("p", "n1"): 1.0}))
            )
            self.hippo_rag._add_synonymy_edges = AsyncMock(return_value=Result.Ok({}))
            self.hippo_rag._augment_graph = AsyncMock(return_value=Result.Ok({}))
            self.hippo_rag._save_openie_results = AsyncMock(
                return_value=Result.Ok(None)
            )

            result = await self.hippo_rag.index(["d1"])
            if result.is_error():
                logger.error(result.get_error())
            assert result.is_ok()
            self.hippo_rag._add_synonymy_edges.assert_awaited_once()
            self.hippo_rag._augment_graph.assert_awaited_once()


class TestHippoRAGAsyncDocumentIndexer(AsyncTestBase):
    """Test the AsyncDocumentIndexer interface methods"""

    __test__ = True

    def setup_method_sync(self, test_name: str):
        (
            self.mock_vector_store_entity,
            self.mock_vector_store_chunk,
            self.mock_vector_store_fact,
            self.mock_state_store,
            self.mock_openie,
            self.mock_graph,
        ) = _make_common_mocks()
        self.config = _default_config()
        self.hippo_rag = HippoRAGIndexer(
            vector_store_entity=self.mock_vector_store_entity,
            vector_store_chunk=self.mock_vector_store_chunk,
            vector_store_fact=self.mock_vector_store_fact,
            graph=self.mock_graph,
            state_store=self.mock_state_store,
            openie=self.mock_openie,
            config=self.config,
            text_splitter=DocumentSplitterDummy(),
        )

    async def test_update_document(self):
        doc = RAGDocument(id="doc1", content="Test content", metadata={})
        collection = "test_collection"

        self.hippo_rag.delete_document = AsyncMock(return_value=Result.Ok(None))
        self.hippo_rag.create_document = AsyncMock(return_value=Result.Ok(None))

        result = await self.hippo_rag.update_document(doc, collection)
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()

        self.hippo_rag.delete_document.assert_awaited_once_with(
            doc_id="doc1", collection=collection
        )
        self.hippo_rag.create_document.assert_awaited_once_with(
            doc=doc, collection=collection
        )

    async def test_delete_document(self):
        doc_id = "doc1"
        collection = "test_collection"

        test_docs = DocumentCollection(
            docs=[
                Document(
                    idx="chunk1",
                    passage="test content",
                    extracted_entities=[],
                    extracted_triples=[],
                    metadata={"doc_id": doc_id},
                )
            ]
        )
        self.mock_state_store.load_openie_info_with_metadata.return_value = Result.Ok(
            test_docs
        )
        self.hippo_rag.delete = AsyncMock(return_value=Result.Ok(None))

        result = await self.hippo_rag.delete_document(doc_id, collection)
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()

        self.mock_state_store.load_openie_info_with_metadata.assert_awaited_once_with(
            metadata={"doc_id": [doc_id]}
        )
        self.hippo_rag.delete.assert_awaited_once_with(docs=["test content"])

    async def test_does_object_with_metadata_exist(self):
        metadata = {"key": "value"}
        collection = "test_collection"

        self.mock_state_store.load_openie_info_with_metadata.return_value = Result.Ok(
            DocumentCollection(docs=[])
        )
        result = await self.hippo_rag.does_object_with_metadata_exist(
            metadata, collection
        )
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()
        assert result.get_ok() is False

        self.mock_state_store.load_openie_info_with_metadata.return_value = Result.Ok(
            DocumentCollection(
                docs=[
                    Document(
                        idx="test",
                        passage="test",
                        extracted_entities=[],
                        extracted_triples=[],
                        metadata=metadata,
                    )
                ]
            )
        )
        result = await self.hippo_rag.does_object_with_metadata_exist(
            metadata, collection
        )
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()
        assert result.get_ok() is True


class TestHippoRAGDelete(AsyncTestBase):
    __test__ = True

    def setup_method_sync(self, test_name: str):
        (
            self.mock_vector_store_entity,
            self.mock_vector_store_chunk,
            self.mock_vector_store_fact,
            self.mock_state_store,
            self.mock_openie,
            self.mock_graph,
        ) = _make_common_mocks()
        self.config = _default_config()
        self.hippo_rag = HippoRAGIndexer(
            vector_store_entity=self.mock_vector_store_entity,
            vector_store_chunk=self.mock_vector_store_chunk,
            vector_store_fact=self.mock_vector_store_fact,
            graph=self.mock_graph,
            state_store=self.mock_state_store,
            openie=self.mock_openie,
            config=self.config,
            text_splitter=DocumentSplitterDummy(),
        )

    @patch("hippo_rag.indexer.compute_mdhash_id")
    @patch("hippo_rag.indexer.extract_entity_nodes")
    @patch("hippo_rag.indexer.flatten_facts")
    @patch("hippo_rag.indexer.text_processing")
    async def test_delete_basic_flow(
        self,
        mock_text_processing,
        mock_flatten_facts,
        mock_extract_entity_nodes,
        mock_hash,
    ):
        docs_to_delete = ["Document 1 content"]

        def mock_hash_func(*args, **kwargs):
            content = kwargs.get("content") or args[0]
            if content == "Document 1 content":
                return "chunk-1"
            elif content == ("entity1", "is", "test"):
                return "triple-1"
            elif content == "entity1":
                return "entity-1"
            else:
                return f"hash-{hash(str(content))}"

        mock_hash.side_effect = mock_hash_func

        openie_doc = Document(
            idx="chunk-1",
            passage="Document 1 content",
            extracted_entities=["entity1"],
            extracted_triples=[("entity1", "is", "test")],
            metadata={},
        )
        self.mock_state_store.fetch_chunks_by_ids.return_value = Result.Ok(
            DocumentCollection(docs=[openie_doc])
        )

        self.mock_state_store.triples_to_docs.return_value = Result.Ok(["chunk-1"])
        self.mock_state_store.ent_node_to_chunk.return_value = Result.Ok(["chunk-1"])

        mock_text_processing.side_effect = lambda x: x
        mock_flatten_facts.return_value = [("entity1", "is", "test")]
        mock_extract_entity_nodes.return_value = (["entity1"], [])

        result = await self.hippo_rag.delete(docs_to_delete)
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()

        self.mock_vector_store_entity.delete.assert_awaited_once()
        self.mock_vector_store_fact.delete.assert_awaited_once()
        self.mock_vector_store_chunk.delete.assert_awaited_once()
        self.mock_graph.delete_vertices.assert_awaited_once()
        self.mock_state_store.delete_chunks.assert_awaited_once()

    @patch("hippo_rag.indexer.compute_mdhash_id")
    async def test_delete_no_chunks_found(self, mock_hash):
        mock_hash.side_effect = lambda *args, **kwargs: "chunk-1"

        doc = Document(
            idx="dummy",
            passage="dummy",
            extracted_triples=[("123", "123", "123")],
            extracted_entities=["123"],
            metadata={},
        )
        self.mock_state_store.fetch_chunks_by_ids.return_value = Result.Ok(
            DocumentCollection(docs=[doc])
        )

        result = await self.hippo_rag.delete(["Non-existent document"])
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()

        self.mock_vector_store_entity.delete.assert_awaited_once()
        self.mock_vector_store_fact.delete.assert_awaited_once()
        self.mock_vector_store_chunk.delete.assert_awaited_once()
        self.mock_graph.delete_vertices.assert_awaited_once()


class TestHippoRAGGraphBuilding(AsyncTestBase):
    __test__ = True

    def setup_method_sync(self, test_name: str):
        (
            self.mock_vector_store_entity,
            self.mock_vector_store_chunk,
            self.mock_vector_store_fact,
            self.mock_state_store,
            self.mock_openie,
            self.mock_graph,
        ) = _make_common_mocks()
        self.config = _default_config()
        self.hippo_rag = HippoRAGIndexer(
            vector_store_entity=self.mock_vector_store_entity,
            text_splitter=DocumentSplitterDummy(),
            vector_store_chunk=self.mock_vector_store_chunk,
            vector_store_fact=self.mock_vector_store_fact,
            graph=self.mock_graph,
            state_store=self.mock_state_store,
            openie=self.mock_openie,
            config=self.config,
        )

    @patch("hippo_rag.indexer.compute_mdhash_id")
    async def test_add_fact_edges(self, mock_compute_hash):
        chunk_ids = ["chunk-1"]
        chunk_triples = [[("entity1", "relates_to", "entity2")]]

        self.mock_graph.get_values_from_attributes.return_value = Result.Ok([])
        mock_compute_hash.side_effect = ["entity-hash-1", "entity-hash-2"]

        result = await self.hippo_rag._add_fact_edges(
            chunk_ids, chunk_triples, node_to_node_stats={}
        )
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()
        mapping = result.get_ok()
        assert ("entity-hash-1", "entity-hash-2") in mapping
        assert ("entity-hash-2", "entity-hash-1") in mapping

    @patch("hippo_rag.indexer.compute_mdhash_id")
    async def test_add_passage_edges(self, mock_compute_hash):
        chunk_ids = ["chunk-1"]
        chunk_triple_entities = [["entity1", "entity2"]]

        self.mock_graph.get_values_from_attributes.return_value = Result.Ok([])
        mock_compute_hash.side_effect = ["entity-hash-1", "entity-hash-2"]

        result = await self.hippo_rag._add_passage_edges(
            chunk_ids, chunk_triple_entities, node_to_node_stats={}
        )
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()
        num_new_chunks, mapping = result.get_ok()
        assert num_new_chunks == 1
        assert ("chunk-1", "entity-hash-1") in mapping
        assert ("chunk-1", "entity-hash-2") in mapping

    @patch("hippo_rag.indexer.compute_mdhash_id")
    async def test_add_synonymy_edges(self, mock_hash):
        class KNNNode:
            def __init__(self, id, payload, score):
                self.id = id
                self.payload = payload
                self.score = score

        entity_nodes = ["apple fruit", "orange citrus"]

        def fake_hash(*args, **kwargs):
            content = kwargs.get("content") or (args[0] if args else None)
            mapping = {"apple fruit": "id1", "orange citrus": "id2"}
            return mapping[content]

        mock_hash.side_effect = fake_hash
        self.mock_vector_store_entity.knn_by_ids.return_value = Result.Ok(
            {
                "id1": [KNNNode("id2", "orange citrus", 0.8)],
                "id2": [KNNNode("id1", "apple fruit", 0.81)],
            }
        )

        result = await self.hippo_rag._add_synonymy_edges(
            node_to_node_stats={}, entity_nodes=entity_nodes
        )
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()
        mapping = result.get_ok()
        assert len(mapping) > 0
        self.mock_vector_store_entity.knn_by_ids.assert_awaited_once()

    async def test_add_new_nodes(self):
        chunks = {"chunk-1": "Apple is fruit"}
        entities = {"entity-1": "apple", "entity-2": "orange"}

        self.mock_graph.get_not_existing_nodes.return_value = Result.Ok(["entity-1"])

        result = await self.hippo_rag._add_new_nodes(chunks=chunks, entities=entities)
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()

        self.mock_graph.add_nodes.assert_awaited_once()
        nodes = self.mock_graph.add_nodes.call_args.kwargs["nodes"]
        assert len(nodes) == 2  # one chunk + one new entity
        assert isinstance(nodes[0], Node)
        assert isinstance(nodes[1], Node)

    async def test_add_new_edges_safeguard(self):
        self.mock_graph.get_values_from_attributes.return_value = Result.Ok(
            ["node-1", "node-2"]
        )
        result = await self.hippo_rag._add_new_edges(node_to_node_stats={})
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()
        returned = result.get_ok()
        assert returned == {}
        self.mock_graph.add_edges.assert_awaited_once()
        edges = self.mock_graph.add_edges.call_args.kwargs["edges"]
        assert edges == []

    async def test_augment_graph(self):
        node_to_node_stats = {("n1", "n2"): 1.0}
        chunks = {"chunk-1": "content"}
        entities = {"entity-1": "apple"}

        self.hippo_rag._add_new_nodes = AsyncMock(return_value=Result.Ok(None))
        self.hippo_rag._add_new_edges = AsyncMock(
            return_value=Result.Ok(node_to_node_stats)
        )

        result = await self.hippo_rag._augment_graph(
            node_to_node_stats, chunks, entities
        )
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()

        self.hippo_rag._add_new_nodes.assert_awaited_once_with(
            chunks=chunks, entities=entities
        )
        self.hippo_rag._add_new_edges.assert_awaited_once_with(node_to_node_stats)


class TestHippoRAGOpenIEOperations(AsyncTestBase):
    __test__ = True
    """Helpers with async boundaries"""

    def setup_method_sync(self, test_name: str):
        (
            self.mock_vector_store_entity,
            self.mock_vector_store_chunk,
            self.mock_vector_store_fact,
            self.mock_state_store,
            self.mock_openie,
            self.mock_graph,
        ) = _make_common_mocks()
        self.config = _default_config()
        self.hippo_rag = HippoRAGIndexer(
            vector_store_entity=self.mock_vector_store_entity,
            text_splitter=DocumentSplitterDummy(),
            vector_store_chunk=self.mock_vector_store_chunk,
            vector_store_fact=self.mock_vector_store_fact,
            graph=self.mock_graph,
            state_store=self.mock_state_store,
            openie=self.mock_openie,
            config=self.config,
        )

    async def test_load_existing_openie(self):
        chunk_keys = ["chunk-1", "chunk-2"]
        existing_docs = [
            Document(
                idx="chunk-1",
                passage="Document content",
                extracted_entities=["entity1"],
                extracted_triples=[("entity1", "is", "test")],
                metadata={},
            )
        ]
        doc_collection = DocumentCollection(docs=existing_docs)
        self.mock_state_store.load_openie_info.return_value = Result.Ok(doc_collection)

        res = await self.hippo_rag._load_existing_openie(chunk_keys)
        if res.is_error():
            logger.error(res.get_error())
        assert res.is_ok()

        loaded_docs, keys_to_process = res.get_ok()
        assert len(loaded_docs) == 1
        assert loaded_docs[0].idx == "chunk-1"
        assert "chunk-2" in keys_to_process
        assert "chunk-1" not in keys_to_process

    def test_merge_openie_results(self):
        chunks_to_save = {"chunk-1": "Test content"}
        ner_results = {
            "chunk-1": NerRawOutput(
                chunk_id="chunk-1",
                response="",
                metadata={},
                unique_entities=["entity1"],
            )
        }
        triple_results = {
            "chunk-1": TripleRawOutput(
                chunk_id="chunk-1",
                response="",
                metadata={},
                triples=[("entity1", "is", "test")],
            )
        }

        with patch("hippo_rag.indexer.text_processing") as mock_text_processing:
            mock_text_processing.side_effect = lambda x: x
            result = self.hippo_rag._merge_openie_results(
                chunks_to_save, ner_results, triple_results, metadata=None
            )
            assert len(result) == 1
            assert result[0].idx == "chunk-1"
            assert result[0].passage == "Test content"
            assert result[0].extracted_entities == ["entity1"]

    async def test_save_openie_results(self):
        openie_docs = [
            Document(
                idx="chunk-1",
                passage="Test content",
                extracted_entities=["entity1"],
                extracted_triples=[("entity1", "is", "test")],
                metadata={},
            )
        ]
        self.mock_state_store.store_openie_info.return_value = Result.Ok(None)

        res = await self.hippo_rag._save_openie_results(openie_docs)
        if res.is_error():
            logger.error(res.get_error())
        assert res.is_ok()

        self.mock_state_store.store_openie_info.assert_awaited_once()
        arg = self.mock_state_store.store_openie_info.call_args[0][0]
        assert isinstance(arg, DocumentCollection)
        assert len(arg.docs) == 1


class TestHippoRAGIntegration(AsyncTestBase):
    __test__ = True

    def setup_method_sync(self, test_name: str):
        (
            self.mock_vector_store_entity,
            self.mock_vector_store_chunk,
            self.mock_vector_store_fact,
            self.mock_state_store,
            self.mock_openie,
            self.mock_graph,
        ) = _make_common_mocks()
        self.config = _default_config()
        self.hippo_rag = HippoRAGIndexer(
            text_splitter=DocumentSplitterDummy(),
            vector_store_entity=self.mock_vector_store_entity,
            vector_store_chunk=self.mock_vector_store_chunk,
            vector_store_fact=self.mock_vector_store_fact,
            graph=self.mock_graph,
            state_store=self.mock_state_store,
            openie=self.mock_openie,
            config=self.config,
        )

    @patch("hippo_rag.indexer.compute_mdhash_id")
    @patch("hippo_rag.indexer.reformat_openie_results")
    @patch("hippo_rag.indexer.extract_entity_nodes")
    @patch("hippo_rag.indexer.flatten_facts")
    @patch("hippo_rag.indexer.text_processing")
    async def test_complete_indexing_pipeline(
        self,
        mock_text_processing,
        mock_flatten_facts,
        mock_extract_entity_nodes,
        mock_reformat_openie,
        mock_hash,
    ):
        test_docs = ["Apple is a fruit that grows on trees"]

        def fake_hash(*args, **kwargs):
            v = kwargs.get("content") or (args[0] if args else None)
            if v == test_docs[0]:
                return "chunk-1"
            return f"h-{v}"

        mock_hash.side_effect = fake_hash
        self.mock_graph.get_not_existing_nodes.return_value = Result.Ok(["chunk-1"])

        mock_ner_result = NerRawOutput(
            chunk_id="chunk-1",
            response="",
            metadata={},
            unique_entities=["apple", "fruit"],
        )
        mock_triple_result = TripleRawOutput(
            chunk_id="chunk-1",
            response="",
            metadata={},
            triples=[("apple", "is", "fruit")],
        )
        self.mock_openie.batch_openie.return_value = Result.Ok(
            ({"chunk-1": mock_ner_result}, {"chunk-1": mock_triple_result})
        )

        self.hippo_rag._merge_openie_results = Mock(
            return_value=[
                Document(
                    idx="chunk-1",
                    passage=test_docs[0],
                    extracted_entities=["apple", "fruit"],
                    extracted_triples=[("apple", "is", "fruit")],
                    metadata={},
                )
            ]
        )
        self.hippo_rag._save_openie_results = AsyncMock(return_value=Result.Ok(None))

        mock_reformat_openie.return_value = ([mock_ner_result], [mock_triple_result])
        mock_text_processing.side_effect = lambda x: x
        mock_extract_entity_nodes.return_value = (
            ["apple", "fruit"],
            [["apple", "fruit"]],
        )
        mock_flatten_facts.return_value = [("apple", "is", "fruit")]

        self.mock_graph.get_values_from_attributes.return_value = Result.Ok([])

        self.hippo_rag._add_fact_edges = AsyncMock(
            return_value=Result.Ok({("n1", "n2"): 1.0})
        )
        self.hippo_rag._add_passage_edges = AsyncMock(
            return_value=Result.Ok((1, {("p", "n1"): 1.0}))
        )
        self.hippo_rag._add_synonymy_edges = AsyncMock(return_value=Result.Ok({}))
        self.hippo_rag._augment_graph = AsyncMock(return_value=Result.Ok({}))

        self.mock_vector_store_chunk.insert_strings.return_value = Result.Ok(None)
        self.mock_vector_store_entity.insert_strings.return_value = Result.Ok(None)
        self.mock_vector_store_fact.insert_strings.return_value = Result.Ok(None)

        result = await self.hippo_rag.index(test_docs)
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()

        self.mock_vector_store_chunk.insert_strings.assert_awaited_once_with(test_docs)
        self.mock_openie.batch_openie.assert_awaited_once()
        self.hippo_rag._merge_openie_results.assert_called_once()
        self.hippo_rag._save_openie_results.assert_awaited_once()
        self.mock_vector_store_entity.insert_strings.assert_awaited_once()
        self.mock_vector_store_fact.insert_strings.assert_awaited_once()
        self.hippo_rag._add_synonymy_edges.assert_awaited_once()
        self.hippo_rag._augment_graph.assert_awaited_once()
