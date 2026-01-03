from core.logger import init_logging
from rest_client.async_client import OTELAsyncHTTPClient
from text_embedding.async_client import CohereHttpRerankerClient, CohereRerankerConfig
from domain_test.text_embedding.test_rerank import TestRerankClientsIntegration
from domain_test.enviroment import rerank

init_logging("debug")


class TestGrpcClientsIntegration(TestRerankClientsIntegration):
    __test__ = True

    @classmethod
    def setup_class_sync(cls):
        # Reranker: keep your original signature assumption
        cls.rerank_client = CohereHttpRerankerClient(
            OTELAsyncHTTPClient(),
            config=CohereRerankerConfig(model=rerank.MODEL_RERANKER),
            base_url=rerank.RERANKER_HOST,
            api_key=rerank.RERANKER_API_KEY,
        )
