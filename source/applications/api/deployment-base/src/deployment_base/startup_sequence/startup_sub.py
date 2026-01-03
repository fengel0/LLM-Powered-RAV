from core.config_loader import ConfigLoader
from deployment_base.enviroment import openai_env, text_embedding
from deployment_base.enviroment import vllm_reranker
from deployment_base.enviroment.qdrant_env import SPARSE_MODEL
from deployment_base.enviroment.simple_rag import (
    TOP_N_COUNT_DENSE,
    TOP_N_COUNT_RERANKER,
    TOP_N_COUNT_SPARSE,
)
from deployment_base.enviroment.sub_question_rag import (
    CONDENSE_QUESTON_PROMPT,
    QA_PROMPT,
    QUERY_WRAPPER_PROMPT,
    SUB_QUER_PROMPT,
    SUB_SYSTEM_PROMPT,
)
from deployment_base.enviroment.vllm_reranker import RERANK_MODEL
from domain.database.config.model import (
    RAGConfig,
)
from domain.rag.interface import RAGLLM


def init_sub(rag_config: RAGConfig, config_loader: ConfigLoader) -> RAGLLM:
    from llama_index_extension.sub_question_builder import (
        LlamaIndexSubQuestionBuilder,
        LlamaIndexSubQuestionBuilderConfig,
    )
    from rest_client.async_client import OTELAsyncHTTPClient
    from simple_rag.llama_index_rag import LlamaIndexSubRAG
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

    cfg = LlamaIndexSubQuestionBuilderConfig(
        sub_query_prompt=rag_config.retrieval_config.prompts[SUB_QUER_PROMPT],
        condense_question_prompt=rag_config.retrieval_config.prompts[
            CONDENSE_QUESTON_PROMPT
        ],
        qa_prompt=rag_config.retrieval_config.prompts[QA_PROMPT],
        system_prompt=rag_config.retrieval_config.prompts[SUB_SYSTEM_PROMPT],
        query_wrapper_prompt=rag_config.retrieval_config.prompts[QUERY_WRAPPER_PROMPT],
        llm_model=rag_config.retrieval_config.generator_model,
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
        temperatur=rag_config.retrieval_config.temp,
        context_window=128000,
        embedding=embedder,
        reranker=reranker,
    )

    return LlamaIndexSubRAG(chat_builder=LlamaIndexSubQuestionBuilder(config=cfg))
