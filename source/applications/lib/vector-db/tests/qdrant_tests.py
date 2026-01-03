# tests/test_vector_store_qdrant.py
import logging
import uuid

from core.logger import init_logging
from core.singelton import SingletonMeta
from domain.rag.indexer.model import Document, SplitNode
from domain_test.enviroment import embedding, rerank, test_containers
from domain_test.vector.vector_test import TestDBVectorStore
from llama_index_extension.build_components import (
    LLamaIndexHolder,
    LlamaIndexRAGConfig,
    LlamaIndexVectorStoreSession,
)
from llama_index_extension.vector_store_session import (
    LlamaIndexVectorStoreSessionConfig,
)
from rest_client.async_client import OTELAsyncHTTPClient
from testcontainers.qdrant import QdrantContainer
from text_embedding.async_client import CohereHttpRerankerClient, CohereRerankerConfig
from text_embedding.proto import EmbeddingClientConfig, GrpcEmbeddClient
from vector_db.qdrant_vector_store import (
    LlamaIndexVectorStore,
    LlamaIndexVectorStoreConfig,
)

init_logging("INFO")
logger = logging.getLogger(__name__)


class DummyDocumentSplitter:
    """A no-op implementation of DocumentSplitter for testing."""

    def split_documents(self, doc: Document) -> list[SplitNode]:
        # If content is a string, split by sentences (very basic).
        if isinstance(doc.content, str):
            parts = doc.content.split(".")
        else:
            # If it's a list of pages, concatenate all page text.
            parts = [str(page) for page in doc.content]

        # Filter out empty chunks and wrap in SplitNode
        return [
            SplitNode(
                id=str(uuid.uuid4()),
                content=part.strip(),
                metadata={**doc.metadata, "chunk_index": i},
            )
            for i, part in enumerate(parts)
            if part.strip()
        ]


# ------------------------------- config -------------------------------- #
collection = "qdrant_collection"
top_n_count_dens = 5
top_n_count_sparse = 5
top_n_count_reranker = 5


class TestQdrantVectorStore(TestDBVectorStore):
    """
    Concrete harness: spins up a Qdrant container, wires LlamaIndex, and
    provides a LlamaIndexVectorStore to the generic base tests.
    """

    __test__ = True

    qdrant: QdrantContainer

    def setup_method_sync(self, test_name: str):
        # Start Qdrant ephemeral container
        self.qdrant = (
            QdrantContainer(image=test_containers.QDRANT_VERSION)
            .with_exposed_ports(6333)
            .with_exposed_ports(6334)
        )
        self.qdrant.start()

        # Prepare vector DB config using exposed ports
        self._vdb_cfg = LlamaIndexVectorStoreSessionConfig(
            qdrant_host=self.qdrant.get_container_host_ip(),
            qdrant_port=int(self.qdrant.get_exposed_port(6333)),
            qdrant_api_key=None,
            qdrant_grpc_port=int(self.qdrant.get_exposed_port(6334)),
            qdrant_prefer_grpc=True,
            collection=collection,
            batch_size=20,
        )

        self._rag_cfg = LlamaIndexRAGConfig()

    async def setup_method_async(self, test_name: str):
        # Create vector store session and index holder (embedding + reranker)
        LlamaIndexVectorStoreSession.create(config=self._vdb_cfg)  # type: ignore

        LLamaIndexHolder.create(  # type: ignore
            config=self._rag_cfg,
        )

        # System under test
        self.vector_store = LlamaIndexVectorStore(
            note_splitter=DummyDocumentSplitter(),
            config=LlamaIndexVectorStoreConfig(
                top_n_count_dens=5,
                top_n_count_sparse=5,
                top_n_count_reranker=5,
                embedding=GrpcEmbeddClient(
                    address=embedding.EMBEDDING_HOST,
                    is_secure=False,
                    config=EmbeddingClientConfig(
                        normalize=True,
                        truncate=True,
                        truncate_direction="right",
                        prompt_name_doc=None,
                        prompt_name_query=None,
                    ),
                ),
                reranker=CohereHttpRerankerClient(
                    base_url=rerank.RERANKER_HOST,
                    api_key=rerank.RERANKER_API_KEY,
                    http=OTELAsyncHTTPClient(),
                    config=CohereRerankerConfig(model=rerank.MODEL_RERANKER),
                ),
            ),
        )

    def teardown_method_sync(self, test_name: str):
        try:
            self.qdrant.stop()
        finally:
            SingletonMeta.clear_all()

        self.vector_store = None
