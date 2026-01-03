from __future__ import annotations

import uuid
import logging
from domain_test.hippo_rag.hippo_rag_vector_store import TestQdrantEmbeddingStoreBase
from testcontainers.qdrant import QdrantContainer
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance
from text_embedding.proto import EmbeddingClientConfig, GrpcEmbeddClient

from domain_test.enviroment import test_containers, embedding

from hippo_rag_vectore_store.vector_store import (
    HippoRAGVectorStoreSession,
    QdrantConfig,
    QdrantEmbeddingStore,
    QdrantEmbeddingStoreConfig,
)

from core.logger import BaseSingleton, init_logging


init_logging("debug")
logger = logging.getLogger(__name__)

QDRANT_HTTP_PORT = 6333
QDRANT_GRPC_PORT = 6334


class TestQdrantEmbeddingStore(TestQdrantEmbeddingStoreBase):
    __test__ = True

    container: QdrantContainer
    _probe_client: AsyncQdrantClient

    # ---------------- hooks ----------------

    def setup_method_sync(self, test_name: str):
        # Clear any global singletons before boot
        BaseSingleton.clear_all()

        # Start Qdrant container
        self.container = (
            QdrantContainer(image=test_containers.QDRANT_VERSION)
            .with_exposed_ports(QDRANT_HTTP_PORT)
            .with_exposed_ports(QDRANT_GRPC_PORT)
        )
        self.container.start()

        host = self.container.get_container_host_ip()
        http_port = int(self.container.get_exposed_port(QDRANT_HTTP_PORT))
        grpc_port = int(self.container.get_exposed_port(QDRANT_GRPC_PORT))

        self.host = host
        self.port = http_port
        self.grpc_port = grpc_port
        self.base_url = f"http://{host}:{http_port}"

        logger.info(
            f"[{test_name}] Qdrant container started at {self.base_url} (gRPC:{grpc_port})"
        )

    async def setup_method_async(self, test_name: str):
        # Wait for Qdrant to be ready

        collection = f"test_{uuid.uuid4().hex[:8]}"

        cfg_qdrant = QdrantConfig(
            host=self.host,
            prefere_grpc=True,
            grpc_port=self.grpc_port,
            port=self.port,
        )
        # (Re)create session for each store to ensure isolation by collection
        HippoRAGVectorStoreSession.create(config=cfg_qdrant)

        cfg = QdrantEmbeddingStoreConfig(
            namespace="entity",
            collection=collection,
            dim=embedding.EMBEDDING_SIZE,
            distance=Distance.COSINE,
        )

        embedder = GrpcEmbeddClient(
            address=embedding.EMBEDDING_HOST,
            is_secure=False,
            config=EmbeddingClientConfig(
                normalize=True,
                truncate=True,
                truncate_direction="right",
                prompt_name_doc=None,
                prompt_name_query=None,
            ),
        )

        self.store = QdrantEmbeddingStore(cfg, embedder=embedder)

    async def teardown_method_async(self, test_name: str):
        # Close clients/sessions created during tests
        try:
            if hasattr(self, "_probe_client"):
                await self._probe_client.close()
        except Exception as e:
            logger.warning(f"[{test_name}] Probe client close warning: {e}")

        try:
            # Close vector store session singleton if initialized
            sess = HippoRAGVectorStoreSession.Instance()
            await sess.close()
        except Exception:
            pass

    def teardown_method_sync(self, test_name: str):
        # Stop container and clear global singletons
        try:
            self.container.stop()
        finally:
            BaseSingleton.clear_all()
            logger.info(
                f"[{test_name}] Qdrant container stopped and singletons cleared"
            )
