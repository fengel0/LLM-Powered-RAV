from core.config_loader import ConfigLoader
from core.result import Result
from deployment_base.enviroment import text_embedding, vllm_reranker
from deployment_base.startup_sequence.llama_index import openai_env
from deployment_base.startup_sequence.startup_naive import (
    RERANK_MODEL,
    SPARSE_MODEL,
    TOP_N_COUNT_DENSE,
    TOP_N_COUNT_RERANKER,
    TOP_N_COUNT_SPARSE,
)
from domain.database.config.interface import RAGConfig
from domain.rag.model import Node


async def search(
    query: str,
    rag_config: RAGConfig,
    config_loader: ConfigLoader,
    enable_reranker: bool,
    collection: str,
) -> Result[list[Node]]:
    from rest_client.async_client import OTELAsyncHTTPClient
    from llama_index_extension.search_engine_builder import (
        LlamaIndexSearchEngineConfig,
        LlamaIndexSearchEngine,
    )
    from text_embedding.async_client import (
        CohereHttpRerankerClient,
        CohereRerankerConfig,
    )
    from text_embedding.proto import EmbeddingClientConfig, GrpcEmbeddClient

    result = config_loader.load_values(
        [*openai_env.SETTINGS, *text_embedding.SETTINGS_HOST, *vllm_reranker.SETTINGS]
    )
    if result.is_error():
        raise result.get_error()
    embedder = GrpcEmbeddClient(
        address=config_loader.get_str(text_embedding.EMBEDDING_HOST),
        is_secure=config_loader.get_bool(text_embedding.IS_EMBEDDING_HOST_SECURE),
        config=EmbeddingClientConfig(
            normalize=rag_config.embedding.addition_information[
                text_embedding.EMEDDING_NORMALIZE
            ],
            truncate=rag_config.embedding.addition_information[text_embedding.TRUNCATE],
            truncate_direction=rag_config.embedding.addition_information[
                text_embedding.TRUNCATE_DIRECTION
            ],
            prompt_name_doc=rag_config.embedding.addition_information[
                text_embedding.EMBEDDING_DOC_PROMPT_NAME
            ],
            prompt_name_query=rag_config.embedding.addition_information[
                text_embedding.EMBEDDING_QUERY_PROMPT_NAME
            ],
        ),
    )
    reranker = CohereHttpRerankerClient(
        base_url=config_loader.get_str(vllm_reranker.RERANK_HOST),
        api_key=config_loader.get_str(vllm_reranker.RERANK_API_KEY),
        http=OTELAsyncHTTPClient(timeout=600),
        config=CohereRerankerConfig(
            model=rag_config.retrieval_config.addition_information[RERANK_MODEL]
        ),
    )

    cfg = LlamaIndexSearchEngineConfig(
        top_n_count_dens=rag_config.retrieval_config.addition_information[
            TOP_N_COUNT_DENSE
        ],
        top_n_count_sparse=rag_config.retrieval_config.addition_information[
            TOP_N_COUNT_SPARSE
        ],
        top_n_count_reranker=rag_config.retrieval_config.addition_information[
            TOP_N_COUNT_RERANKER
        ],
        sparse_model=rag_config.embedding.models[SPARSE_MODEL],
        embedding=embedder,
        reranker=reranker if enable_reranker else None,
    )

    return await LlamaIndexSearchEngine(config=cfg).query(
        query=query, metadata_filters={}, collection=collection
    )
