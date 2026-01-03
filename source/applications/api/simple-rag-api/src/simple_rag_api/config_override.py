from rest_client.async_client import OTELAsyncHTTPClient
from text_embedding.async_client import (
    CohereRerankerConfig,
    CohereHttpRerankerClient,
)
from core.config_loader import ConfigLoader
from domain.database.config.model import RAGConfig
from domain.rag.interface import RAGConfigOverride
from text_embedding.proto import (
    EmbeddingClientConfig,
    GrpcEmbeddClient,
)
from domain.rag.model import (
    HippoRAGRetrivalConfigOverride,
    HippoRAGEmbeddingConfigOverride,
    SimpleEmbeddingConfig,
    SimpleRetrivalConfig,
    SubQuestionRetrivalConfig,
)
from deployment_base.enviroment.hippo_rag import (
    CHUNKS_TO_RETRIEVE_PPR_SEED,
    DAMPING,
    PASSAGE_NODE_WEIGHT,
    PPR_DIRECTED,
    QA_TOP_N,
    TOP_N_HIPPO_RAG,
    TOP_N_LINKINIG,
)
from deployment_base.enviroment.sub_question_rag import (
    CONDENSE_QUESTON_PROMPT,
    QA_PROMPT,
    QUERY_WRAPPER_PROMPT,
    SUB_QUER_PROMPT,
    SUB_SYSTEM_PROMPT,
)
from deployment_base.enviroment import text_embedding, vllm_reranker
from deployment_base.enviroment.simple_rag import (
    SYSTEM_PROMPT_SIMPLE,
    TOP_N_COUNT_DENSE,
    TOP_N_COUNT_SPARSE,
    TOP_N_COUNT_RERANKER,
)


def create_simple_rag_override(
    config: RAGConfig, config_loader: ConfigLoader
) -> RAGConfigOverride:
    """Create a Simple RAG override config from a base RAGConfig."""
    embedder = GrpcEmbeddClient(
        address=config_loader.get_str(text_embedding.EMBEDDING_HOST),
        is_secure=config_loader.get_bool(text_embedding.IS_EMBEDDING_HOST_SECURE),
        config=EmbeddingClientConfig(
            normalize=config.embedding.addition_information[
                text_embedding.EMEDDING_NORMALIZE
            ],
            truncate=config.embedding.addition_information[text_embedding.TRUNCATE],
            truncate_direction=config.embedding.addition_information[
                text_embedding.TRUNCATE_DIRECTION
            ],
            prompt_name_doc=config.embedding.addition_information[
                text_embedding.EMBEDDING_DOC_PROMPT_NAME
            ],
            prompt_name_query=config.embedding.addition_information[
                text_embedding.EMBEDDING_QUERY_PROMPT_NAME
            ],
        ),
    )

    reranker = CohereHttpRerankerClient(
        base_url=config_loader.get_str(vllm_reranker.RERANK_HOST),
        api_key=config_loader.get_str(vllm_reranker.RERANK_API_KEY),
        config=CohereRerankerConfig(
            model=config.embedding.addition_information[vllm_reranker.RERANK_MODEL]
        ),
        http=OTELAsyncHTTPClient(),
    )

    embedding_cfg = SimpleEmbeddingConfig(
        embedding=embedder,
    )

    retrieval_cfg = SimpleRetrivalConfig(
        llm_model=config.retrieval_config.generator_model,
        system_prompt=config.retrieval_config.prompts[SYSTEM_PROMPT_SIMPLE],
        rerank_client=reranker,
        top_n_count_reranker=config.retrieval_config.addition_information[
            TOP_N_COUNT_RERANKER
        ],
        top_n_count_dens=config.retrieval_config.addition_information[
            TOP_N_COUNT_DENSE
        ],
        top_n_count_sparse=config.retrieval_config.addition_information[
            TOP_N_COUNT_SPARSE
        ],
        temperatur=config.retrieval_config.temp,
    )

    return RAGConfigOverride(
        retrival_config=retrieval_cfg,
        embedding_config=embedding_cfg,
    )


def create_subquestion_rag_override(
    config: RAGConfig, config_loader: ConfigLoader
) -> RAGConfigOverride:
    """Create a SubQuestion RAG override config from a base RAGConfig."""
    embedder = GrpcEmbeddClient(
        address=config_loader.get_str(text_embedding.EMBEDDING_HOST),
        is_secure=config_loader.get_bool(text_embedding.IS_EMBEDDING_HOST_SECURE),
        config=EmbeddingClientConfig(
            normalize=config.embedding.addition_information[
                text_embedding.EMEDDING_NORMALIZE
            ],
            truncate=config.embedding.addition_information[text_embedding.TRUNCATE],
            truncate_direction=config.embedding.addition_information[
                text_embedding.TRUNCATE_DIRECTION
            ],
            prompt_name_doc=config.embedding.addition_information[
                text_embedding.EMBEDDING_DOC_PROMPT_NAME
            ],
            prompt_name_query=config.embedding.addition_information[
                text_embedding.EMBEDDING_QUERY_PROMPT_NAME
            ],
        ),
    )

    reranker = CohereHttpRerankerClient(
        base_url=config_loader.get_str(vllm_reranker.RERANK_HOST),
        api_key=config_loader.get_str(vllm_reranker.RERANK_API_KEY),
        config=CohereRerankerConfig(
            model=config.embedding.addition_information[vllm_reranker.RERANK_MODEL]
        ),
        http=OTELAsyncHTTPClient(),
    )

    embedding_cfg = SimpleEmbeddingConfig(
        embedding=embedder,
    )

    retrieval_cfg = SubQuestionRetrivalConfig(
        llm_model=config.retrieval_config.generator_model,
        system_prompt=config.retrieval_config.prompts[SUB_SYSTEM_PROMPT],
        rerank_client=reranker,
        top_n_count_reranker=config.retrieval_config.addition_information[
            TOP_N_COUNT_RERANKER
        ],
        top_n_count_dens=config.retrieval_config.addition_information[
            TOP_N_COUNT_DENSE
        ],
        top_n_count_sparse=config.retrieval_config.addition_information[
            TOP_N_COUNT_SPARSE
        ],
        temperatur=config.retrieval_config.temp,
        sub_query_prompt=config.retrieval_config.prompts[SUB_QUER_PROMPT],
        condense_queston_prompt=config.retrieval_config.prompts[
            CONDENSE_QUESTON_PROMPT
        ],
        qa_prompt=config.retrieval_config.prompts[QA_PROMPT],
        query_wrapper_prompt=config.retrieval_config.prompts[QUERY_WRAPPER_PROMPT],
    )

    return RAGConfigOverride(
        retrival_config=retrieval_cfg,
        embedding_config=embedding_cfg,
    )


def create_hippo_rag_override(
    config: RAGConfig, config_loader: ConfigLoader
) -> RAGConfigOverride:
    """Create a Hippo RAG override config from a base RAGConfig."""
    embedder = GrpcEmbeddClient(
        address=config_loader.get_str(text_embedding.EMBEDDING_HOST),
        is_secure=config_loader.get_bool(text_embedding.IS_EMBEDDING_HOST_SECURE),
        config=EmbeddingClientConfig(
            normalize=config.embedding.addition_information[
                text_embedding.EMEDDING_NORMALIZE
            ],
            truncate=config.embedding.addition_information[text_embedding.TRUNCATE],
            truncate_direction=config.embedding.addition_information[
                text_embedding.TRUNCATE_DIRECTION
            ],
            prompt_name_doc=config.embedding.addition_information[
                text_embedding.EMBEDDING_DOC_PROMPT_NAME
            ],
            prompt_name_query=config.embedding.addition_information[
                text_embedding.EMBEDDING_QUERY_PROMPT_NAME
            ],
        ),
    )

    embedding_cfg = HippoRAGEmbeddingConfigOverride(
        embedding=embedder,
    )

    retrieval_cfg = HippoRAGRetrivalConfigOverride(
        llm_model=config.retrieval_config.generator_model,
        temperatur=config.retrieval_config.temp,
        retrieval_top_k=config.retrieval_config.addition_information[TOP_N_HIPPO_RAG],
        linking_top_k=config.retrieval_config.addition_information[TOP_N_LINKINIG],
        passage_node_weight=config.retrieval_config.addition_information[
            PASSAGE_NODE_WEIGHT
        ],
        chunks_to_retrieve_ppr_seed=config.retrieval_config.addition_information[
            CHUNKS_TO_RETRIEVE_PPR_SEED
        ],
        qa_top_k=config.retrieval_config.addition_information[QA_TOP_N],
        damping=config.retrieval_config.addition_information[DAMPING],
        directional_ppr=config.retrieval_config.addition_information[PPR_DIRECTED],
    )

    return RAGConfigOverride(
        retrival_config=retrieval_cfg,
        embedding_config=embedding_cfg,
    )
