import logging

from core.logger import init_logging
from domain_test.text_embedding.test_embedding import TestClientsIntegration
from text_embedding.proto import (
    GrpcEmbeddClient,
)
from text_embedding.proto import EmbeddingClientConfig  # adjust import if needed
from domain_test.enviroment import embedding

init_logging("debug")
logger = logging.getLogger(__name__)


class TestGrpcClientsIntegration(TestClientsIntegration):
    __test__ = True

    @classmethod
    def setup_class_sync(cls):
        # Reranker: keep your original signature assumption

        # Embedder: your class requires a config first
        cls.embed_config = EmbeddingClientConfig(
            normalize=False,
            prompt_name_query=None,
            prompt_name_doc=None,
            truncate=False,
            truncate_direction="right",
        )
        cls.embed_client = GrpcEmbeddClient(
            config=cls.embed_config,
            address=embedding.EMBEDDING_HOST,
            is_secure=False,
        )
