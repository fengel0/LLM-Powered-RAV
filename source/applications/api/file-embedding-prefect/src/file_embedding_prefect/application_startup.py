import logging
from typing import Callable

import config_database.model as config_models
import file_database.model as file_models
import hippo_rag_database.model as hippo_rag_models
from config_database.db_implementation import PostgresRAGEmbeddingConfigDatabase
from config_service.usecase.config_storage import ConfigLoaderUsecase
from core.config_loader import ConfigLoader
from core.result import Result
from deployment_base.application import Application
from deployment_base.enviroment import (
    advanced_chunker as advanced_chunker_env,
)
from deployment_base.enviroment import hippo_rag as hippo_rag_env
from deployment_base.enviroment import (
    minio_env,
    openai_env,
    qdrant_env,
    text_embedding,
    vllm_reranker,
)
from deployment_base.startup_sequence.hippo_rag import HippoRAGQdrantStartupSequence
from deployment_base.startup_sequence.llama_index import (
    LlamaIndexQdrantStartupSequence,
    LlamaIndexStartupSequence,
)
from deployment_base.startup_sequence.log import LoggerStartupSequence
from deployment_base.startup_sequence.neo4j import Neo4jStartupSequence
from deployment_base.startup_sequence.postgres import PostgresStartupSequence
from deployment_base.startup_sequence.s3 import MinioStartupSequence
from domain.database.config.model import RagEmbeddingConfig
from file_database.file_db_implementation import PostgresFileDatabase
from file_embedding_pipline_service.usecase.embbeding_document import (
    EmbeddFilePiplineUsecase,
    EmbeddFilePiplineUsecaseConfig,
)
from hippo_rag.indexer import AsyncDocumentIndexer, HippoRAGIndexer, IndexerConfig
from hippo_rag.openie import AsyncOpenIE, OpenIEConfig
from hippo_rag_database.state_holder import (  # contains PostgresDBStateStore
    PostgresDBStateStore,
)
from hippo_rag_graph.graph_implementation import (
    Neo4jConfig,
    Neo4jGraphDB,
)
from hippo_rag_vectore_store.vector_store import (
    QdrantEmbeddingStore,
    QdrantEmbeddingStoreConfig,
)
from openai_client.async_openai import ConfigOpenAI, OpenAIAsyncLLM
from qdrant_client.models import (
    Distance,
)
from rest_client.async_client import OTELAsyncHTTPClient
from s3.minio import MinioConnection, MinioFileStorage
from text_embedding.async_client import (
    CohereHttpRerankerClient,
    CohereRerankerConfig,
)
from text_embedding.proto import (
    EmbeddingClientConfig,
    GrpcEmbeddClient,
)
from text_splitter.node_splitter import (
    AdvancedSentenceSplitter,
    NodeSplitterConfig,
)
from vector_db.qdrant_vector_store import (
    LlamaIndexVectorStore,
    LlamaIndexVectorStoreConfig,
)

from file_embedding_prefect.settings import (
    API_NAME,
    API_VERSION,
    CONSIDER_IMAGES,
    DOCUMENT_LANGUAGE,
    EMBEDDING_CONFIG,
    EMBEDDING_IMPLEMENTATION,
    QUED_TASKS,
    SETTINGS,
)
from file_embedding_prefect.update_hippo_rag_settings import update_graph
from file_embedding_prefect.update_simple_rag_settings import update_simple

logger = logging.getLogger(__name__)


class RAGEmbeddingConfigLoaderApplication(Application):
    _config_usecase: ConfigLoaderUsecase[RagEmbeddingConfig] | None = None

    def get_application_name(self) -> str:
        embedding_type = self._config_loader.get_str(EMBEDDING_IMPLEMENTATION)
        return f"{API_NAME}-{embedding_type}-{API_VERSION}"

    def _add_components(self):
        result = self._config_loader.load_values(
            [
                *SETTINGS,
                *advanced_chunker_env.SETTINGS,
                *text_embedding.SETTINGS_MODEL,
                *openai_env.SETTINGS,
                *hippo_rag_env.SETTINGS,
            ]
        )
        if result.is_error():
            raise result.get_error()
        self._with_component(
            component=LoggerStartupSequence(
                application_name=self.get_application_name(),
                application_version=API_VERSION,
            )
        )._with_acomponent(
            component=PostgresStartupSequence(
                models=[
                    config_models,
                ]
            )
        )

    async def _create_usecase(self):
        self._config_usecase = (  # type: ignore
            ConfigLoaderUsecase(  # type: ignore
                model=RagEmbeddingConfig,
                db=PostgresRAGEmbeddingConfigDatabase(),
                config_loader=self._config_loader,
            )
        )

    async def get_rag_config(self) -> Result[RagEmbeddingConfig]:
        assert self._config_usecase
        update_function: (
            None | Callable[[RagEmbeddingConfig, ConfigLoader], RagEmbeddingConfig]
        ) = None
        if self._config_loader.get_str(EMBEDDING_IMPLEMENTATION) == "vector":
            update_function = update_simple
        if self._config_loader.get_str(EMBEDDING_IMPLEMENTATION) == "hippo_rag":
            update_function = update_graph

        assert update_function

        rag_config_result = await self._config_usecase.load_config_update_config(
            key=EMBEDDING_CONFIG, update_lamda=update_function
        )
        return rag_config_result


class FileEmbeddingPrefectApplication(Application):
    embedding_config: RagEmbeddingConfig | None = None

    def get_application_name(self) -> str:
        assert self.embedding_config, "need to be set before creating the usecase"
        result = self._config_loader.load_values(SETTINGS)
        if result.is_error():
            raise result.get_error()
        return f"{API_NAME}-{API_VERSION}-{self._config_loader.get_str(EMBEDDING_IMPLEMENTATION)}-{self.embedding_config.id}"

    def set_embedding_config(self, config: RagEmbeddingConfig):
        self.embedding_config = config

    def _add_components(self):
        assert self.embedding_config, "need to be set before creating the usecase"
        result = self._config_loader.load_values(SETTINGS)
        if result.is_error():
            raise result.get_error()
        self._with_component(
            component=LoggerStartupSequence(
                application_name=self.get_application_name(),
                application_version=API_VERSION,
            )
        )

        self._config_loader.load_values(
            [
                *advanced_chunker_env.SETTINGS,
                *text_embedding.SETTINGS_HOST,
            ]
        )
        if self._config_loader.get_str(EMBEDDING_IMPLEMENTATION) == "vector":
            self._with_acomponent(
                component=PostgresStartupSequence(models=[file_models, config_models])
            )._with_acomponent(component=MinioStartupSequence())._with_acomponent(
                component=LlamaIndexQdrantStartupSequence()
            )._with_acomponent(component=LlamaIndexStartupSequence())
            # ._with_acomponent(component=LlamaIndexStartupSequence())
        elif self._config_loader.get_str(EMBEDDING_IMPLEMENTATION) == "hippo_rag":
            result = self._config_loader.load_values(
                [
                    *openai_env.SETTINGS,
                    *hippo_rag_env.SETTINGS,
                ]
            )
            if result.is_error():
                raise result.get_error()
            self._with_acomponent(
                component=PostgresStartupSequence(
                    models=[file_models, hippo_rag_models, config_models]
                )
            )._with_acomponent(component=MinioStartupSequence())._with_acomponent(
                component=Neo4jStartupSequence()
            )._with_acomponent(component=HippoRAGQdrantStartupSequence())
        else:
            assert False, "should not happen"

    async def _create_usecase(self):
        assert self.embedding_config, "need to be set before creating the usecase"

        file_database = PostgresFileDatabase()

        connection = MinioConnection.get_instance(
            self._config_loader.get_str(minio_env.S3_HOST)
        )

        text_splitter = AdvancedSentenceSplitter(
            config=NodeSplitterConfig(
                chunk_size=self.embedding_config.chunk_size,
                chunk_overlap=self.embedding_config.chunk_overlap,
                default_language=self._config_loader.get_str(DOCUMENT_LANGUAGE),
            )
        )

        indexer: AsyncDocumentIndexer | None = None

        embedder = GrpcEmbeddClient(
            address=self._config_loader.get_str(text_embedding.EMBEDDING_HOST),
            is_secure=self._config_loader.get_bool(
                text_embedding.IS_EMBEDDING_HOST_SECURE
            ),
            config=EmbeddingClientConfig(
                normalize=self.embedding_config.addition_information[
                    text_embedding.EMEDDING_NORMALIZE
                ],
                truncate=self.embedding_config.addition_information[
                    text_embedding.TRUNCATE
                ],
                truncate_direction=self.embedding_config.addition_information[
                    text_embedding.TRUNCATE_DIRECTION
                ],
                prompt_name_doc=self.embedding_config.addition_information[
                    text_embedding.EMBEDDING_DOC_PROMPT_NAME
                ],
                prompt_name_query=self.embedding_config.addition_information[
                    text_embedding.EMBEDDING_QUERY_PROMPT_NAME
                ],
            ),
        )
        if self._config_loader.get_str(EMBEDDING_IMPLEMENTATION) == "vector":
            reranker = CohereHttpRerankerClient(
                base_url=self._config_loader.get_str(vllm_reranker.RERANK_HOST),
                api_key=self._config_loader.get_str(vllm_reranker.RERANK_API_KEY),
                http=OTELAsyncHTTPClient(),
                config=CohereRerankerConfig(
                    model=self._config_loader.get_str(vllm_reranker.RERANK_MODEL)
                ),
            )

            indexer = LlamaIndexVectorStore(
                note_splitter=text_splitter,
                config=LlamaIndexVectorStoreConfig(
                    top_n_count_sparse=5,
                    top_n_count_dens=5,
                    top_n_count_reranker=5,
                    embedding=embedder,
                    reranker=reranker,
                    sparse_model=self.embedding_config.models[qdrant_env.SPARSE_MODEL],
                ),
            )
        elif self._config_loader.get_str(EMBEDDING_IMPLEMENTATION) == "hippo_rag":
            cfg_ent = QdrantEmbeddingStoreConfig(
                collection=self.embedding_config.id,
                dim=self.embedding_config.addition_information[
                    hippo_rag_env.EMBEDDING_SIZE
                ],
                distance=Distance.COSINE,  # or Distance.COSINE
                namespace="entity",
            )
            cfg_chunk = QdrantEmbeddingStoreConfig(
                collection=self.embedding_config.id,
                dim=self.embedding_config.addition_information[
                    hippo_rag_env.EMBEDDING_SIZE
                ],
                distance=Distance.COSINE,  # or Distance.COSINE
                namespace="chunk",
            )
            cfg_link = QdrantEmbeddingStoreConfig(
                collection=self.embedding_config.id,
                dim=self.embedding_config.addition_information[
                    hippo_rag_env.EMBEDDING_SIZE
                ],
                distance=Distance.COSINE,  # or Distance.COSINE
                namespace="facts",
            )
            client = OpenAIAsyncLLM(
                ConfigOpenAI(
                    model=self.embedding_config.models[openai_env.OPENAI_MODEL],
                    base_url=self._config_loader.get_str(openai_env.OPENAI_HOST),
                    max_tokens=self._config_loader.get_int(openai_env.MAX_TOKENS),
                    api_key=self._config_loader.get_str(openai_env.OPENAI_KEY),
                    timeout=self._config_loader.get_int(openai_env.LLM_REQUEST_TIMEOUT),
                    temperature=self.embedding_config.addition_information[
                        openai_env.TEMPERATUR
                    ],
                    context_cutoff=int(128_000 * 0.90),
                    does_support_structured_output=self._config_loader.get_bool(
                        openai_env.DOES_SUPPORT_STRUCTURED_OUTPUT
                    ),
                )
            )

            indexer = HippoRAGIndexer(
                text_splitter=text_splitter,
                vector_store_entity=QdrantEmbeddingStore(cfg_ent, embedder=embedder),
                vector_store_fact=QdrantEmbeddingStore(cfg_link, embedder=embedder),
                vector_store_chunk=QdrantEmbeddingStore(cfg_chunk, embedder=embedder),
                graph=Neo4jGraphDB(config=Neo4jConfig()),
                openie=AsyncOpenIE(llm=client, config=OpenIEConfig(retries=3)),
                state_store=PostgresDBStateStore(),
                config=IndexerConfig(
                    number_of_parallel_requests=self._config_loader.get_int(QUED_TASKS),
                    synonymy_edge_topk=self.embedding_config.addition_information[
                        hippo_rag_env.SYNONYME_EDEGE_TOP_N
                    ],
                    synonymy_edge_sim_threshold=self.embedding_config.addition_information[
                        hippo_rag_env.SYNONYMY_EDGE_SIM_THRESHOLD
                    ],
                ),
            )
        else:
            raise Exception("Not valid implementation")

        assert indexer, "This should not happen"

        EmbeddFilePiplineUsecase.create(  # type: ignore
            file_storage=MinioFileStorage(minio=connection),
            vectore_store=indexer,
            file_database=file_database,
            config=EmbeddFilePiplineUsecaseConfig(
                consider_images=self._config_loader.get_bool(CONSIDER_IMAGES)
            ),
            embed_config=self.embedding_config,
        )
