from core.config_loader import ConfigLoader, str_to_bool
from deployment_base.enviroment import openai_env
from deployment_base.enviroment import text_embedding
from deployment_base.enviroment import hippo_rag
from deployment_base.enviroment.hippo_rag import (
    CHUNKS_TO_RETRIEVE_PPR_SEED,
    DAMPING,
    PASSAGE_NODE_WEIGHT,
    PPR_DIRECTED,
    QA_TOP_N,
    TOP_N_HIPPO_RAG,
    TOP_N_LINKINIG,
)
from deployment_base.enviroment.openai_env import (
    LLM_REQUEST_TIMEOUT,
    OPENAI_HOST,
    OPENAI_KEY,
)
from domain.database.config.model import RAGConfig
from domain.rag.interface import RAGLLM


def init_hipp_rag(config_loader: ConfigLoader, rag_config: RAGConfig) -> RAGLLM:
    from hippo_rag.dspyfilter import DSPyFilter, DSPyFilterConfig
    from hippo_rag.implementation import HippoRAG, HippoRAGConfig
    from hippo_rag_database.state_holder import PostgresDBStateStore
    from hippo_rag_graph.graph_implementation import (
        Neo4jConfig,
        Neo4jGraphDB,
    )
    from hippo_rag_vectore_store.vector_store import (
        QdrantEmbeddingStore,
        QdrantEmbeddingStoreConfig,
    )
    from openai_client.async_openai import ConfigOpenAI, OpenAIAsyncLLM
    from qdrant_client.models import Distance
    from text_embedding.proto import (
        EmbeddingClientConfig,
        GrpcEmbeddClient,
    )

    result = config_loader.load_values([*openai_env.SETTINGS])
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
    cfg_ent = QdrantEmbeddingStoreConfig(
        collection=rag_config.embedding.id,
        dim=rag_config.embedding.addition_information[hippo_rag.EMBEDDING_SIZE],
        distance=Distance.COSINE,  # or Distance.COSINE
        namespace="entity",
    )
    cfg_chunk = QdrantEmbeddingStoreConfig(
        collection=rag_config.embedding.id,
        dim=rag_config.embedding.addition_information[hippo_rag.EMBEDDING_SIZE],
        distance=Distance.COSINE,  # or Distance.COSINE
        namespace="chunk",
    )
    cfg_link = QdrantEmbeddingStoreConfig(
        collection=rag_config.embedding.id,
        dim=rag_config.embedding.addition_information[hippo_rag.EMBEDDING_SIZE],
        distance=Distance.COSINE,  # or Distance.COSINE
        namespace="facts",
    )
    db = Neo4jGraphDB(
        Neo4jConfig(
            database="neo4j",  # normal version does not allow diffrent databases so it is hard coded
            node_label="Node",
            rel_type="LINKS",
            ppr_implementation="neo4j-gds",
        )
    )

    client = OpenAIAsyncLLM(
        ConfigOpenAI(
            model=rag_config.retrieval_config.generator_model,
            api_key=config_loader.get_str(OPENAI_KEY),
            timeout=config_loader.get_int(LLM_REQUEST_TIMEOUT),
            temperature=rag_config.retrieval_config.temp,
            context_cutoff=int(128_000 * 0.90),
            base_url=config_loader.get_str(OPENAI_HOST),
        )
    )
    return HippoRAG(
        vector_store_entity=QdrantEmbeddingStore(cfg_ent, embedder=embedder),
        vector_store_fact=QdrantEmbeddingStore(cfg_link, embedder=embedder),
        vector_store_chunk=QdrantEmbeddingStore(cfg_chunk, embedder=embedder),
        llm=client,
        config=HippoRAGConfig(
            retrieval_top_k=int(
                rag_config.retrieval_config.addition_information[TOP_N_HIPPO_RAG]
            ),  # max docs to return
            linking_top_k=int(
                rag_config.retrieval_config.addition_information[TOP_N_LINKINIG]
            ),
            chunks_to_retrieve_ppr_seed=rag_config.retrieval_config.addition_information[
                CHUNKS_TO_RETRIEVE_PPR_SEED
            ],
            # facts to rerank / link
            passage_node_weight=float(
                rag_config.retrieval_config.addition_information[PASSAGE_NODE_WEIGHT]
            ),  # graph edge weighting factor
            qa_top_k=int(
                rag_config.retrieval_config.addition_information[QA_TOP_N]
            ),  # number of docs passed to QA
            damping=float(rag_config.retrieval_config.addition_information[DAMPING]),
            directional_ppr=str_to_bool(
                rag_config.retrieval_config.addition_information[PPR_DIRECTED]  # type: ignore
            ),
        ),
        graph=db,
        filter=DSPyFilter(llm_model=client, config=DSPyFilterConfig()),
        state_store=PostgresDBStateStore(),
    )
