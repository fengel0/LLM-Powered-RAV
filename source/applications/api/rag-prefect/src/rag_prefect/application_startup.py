import logging
from typing import Callable

from deployment_base.enviroment import text_embedding
from deployment_base.startup_sequence.startup_naive import init_naive
from deployment_base.startup_sequence.startup_sub import init_sub
from deployment_base.startup_sequence.startup_hippo import init_hipp_rag
import config_database.model as config_models
from core.model import NotFoundException
import fact_store_database.model as fact_models
import hippo_rag_database.model as hippo_rag_models
import project_database.model as project_models
import validation_database.model as validation_models
from config_database.db_implementation import (
    PostgresRAGConfigDatabase,
    PostgresRAGEmbeddingConfigDatabase,
    PostgresRAGRetrievalConfigDatabase,
)
from config_service.usecase.config_storage import ConfigLoaderUsecase
from core.config_loader import (
    ConfigLoader,
)
from core.result import Result
from deployment_base.application import Application
from deployment_base.startup_sequence.hippo_rag import HippoRAGQdrantStartupSequence
from deployment_base.startup_sequence.llama_index import (
    LlamaIndexQdrantStartupSequence,
    LlamaIndexStartupSequence,
)
from deployment_base.startup_sequence.log import LoggerStartupSequence
from deployment_base.startup_sequence.neo4j import Neo4jStartupSequence
from deployment_base.startup_sequence.postgres import PostgresStartupSequence
from domain.database.config.model import (
    RAGConfig,
    RAGConfigTypeE,
    RagEmbeddingConfig,
    RagRetrievalConfig,
)
from domain.rag.interface import RAGLLM
from project_database.project_db_implementation import PostgresDBProjectDatbase
from rag_pipline_service.usecase.rag import RAGUsecase, RagUsecaseConfig
from validation_database.validation_db_implementation import (
    PostgresDBEvaluation,
)

from deployment_base.enviroment.hippo_rag import SETTINGS as HIPPO_RAG_SETTINGS
from deployment_base.enviroment.text_embedding import (
    SETTINGS_MODEL as TEXT_EMBEDDING_SETTINGS,
)

from rag_prefect.settings import (
    API_NAME,
    API_VERSION,
    EMBEDD_CONFIG_TO_USE,
    RAG_CONFIG,
    RAG_CONFIG_NAME,
    RAG_TYPE,
    RETRIVAL_CONFIG,
    SETTINGS,
)
from rag_prefect.update_configs import update_graph, update_naive, update_sub

logger = logging.getLogger(__name__)


class RAGConfigLoaderApplication(Application):
    _config_embedd_usecase: ConfigLoaderUsecase[RagEmbeddingConfig]
    _config_rag_usecase: ConfigLoaderUsecase[RAGConfig]
    _config_retrieval_usecase: ConfigLoaderUsecase[RagRetrievalConfig]

    def get_application_name(self) -> str:
        rag_type = self._config_loader.get_str(RAG_TYPE)
        return f"{API_NAME}-{rag_type}-{API_VERSION}"

    def _add_components(self):
        self._config_loader.load_values(SETTINGS)
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
        self._config_retrieval_usecase = (  # type: ignore
            ConfigLoaderUsecase(
                model=RagRetrievalConfig,
                db=PostgresRAGRetrievalConfigDatabase(),
                config_loader=self._config_loader,
            )
        )
        self._config_embedd_usecase = ConfigLoaderUsecase(
            model=RagEmbeddingConfig,
            db=PostgresRAGEmbeddingConfigDatabase(),
            config_loader=self._config_loader,
        )
        self._config_rag_usecase = ConfigLoaderUsecase(
            model=RAGConfig,
            db=PostgresRAGConfigDatabase(),
            config_loader=self._config_loader,
        )

    async def get_rag_config(self) -> Result[RAGConfig]:
        assert self._config_embedd_usecase
        assert self._config_rag_usecase
        assert self._config_retrieval_usecase
        update_function: (
            None | Callable[[RagRetrievalConfig, ConfigLoader], RagRetrievalConfig]
        ) = None
        if self._config_loader.get_str(RAG_TYPE) == RAGConfigTypeE.SUBQUESTION:
            update_function = update_sub
        if self._config_loader.get_str(RAG_TYPE) == RAGConfigTypeE.HYBRID:
            update_function = update_naive
        if self._config_loader.get_str(RAG_TYPE) == RAGConfigTypeE.HIPPO_RAG:
            update_function = update_graph

        assert update_function

        result = self._config_loader.load_values(SETTINGS)
        if result.is_error():
            return result.propagate_exception()

        rag_retrival_config_result = (
            await self._config_retrieval_usecase.load_config_update_config(
                key=RETRIVAL_CONFIG, update_lamda=update_function
            )
        )
        if rag_retrival_config_result.is_error():
            return rag_retrival_config_result.propagate_exception()
        rag_retrival_config = rag_retrival_config_result.get_ok()

        embedding_result = await self._config_embedd_usecase.load_from_id(
            self._config_loader.get_str(EMBEDD_CONFIG_TO_USE)
        )
        if embedding_result.is_error():
            return embedding_result.propagate_exception()
        embedding = embedding_result.get_ok()
        if embedding is None:
            return Result.Err(
                NotFoundException(
                    f"Embedding Config with id: {self._config_loader.get_str(EMBEDD_CONFIG_TO_USE)} does not exist"
                )
            )

        rag_config = RAGConfig(
            id="",
            name=self._config_loader.get_str(RAG_CONFIG_NAME),
            hash="",
            embedding=embedding,
            config_type=self._config_loader.get_str(RAG_TYPE),
            retrieval_config=rag_retrival_config,
        )

        return await self._config_rag_usecase.write_config_attribut(
            RAG_CONFIG, rag_config
        )


class RAGPrefectApplication(Application):
    _rag_systemconfig: RAGConfig | None = None

    def set_rag_config(self, rag_sytem_config: RAGConfig):
        self._rag_systemconfig = rag_sytem_config

    def get_application_name(self) -> str:
        assert self._rag_systemconfig, "rag_systemconfig needs to be set"
        result = self._config_loader.load_values([*SETTINGS])
        if result.is_error():
            raise result.get_error()
        rag_type = self._config_loader.get_str(RAG_TYPE)
        return f"{API_NAME}-{rag_type}-{API_VERSION}-{self._rag_systemconfig.id}"

    def _add_components(self):
        assert self._rag_systemconfig, "need to set rag_systemconfig"
        self._config_loader.load_values(
            [*HIPPO_RAG_SETTINGS, *TEXT_EMBEDDING_SETTINGS, *SETTINGS]
        )
        self._with_component(
            component=LoggerStartupSequence(
                application_name=self.get_application_name(),
                application_version=API_VERSION,
            )
        )._with_acomponent(
            component=PostgresStartupSequence(
                models=[
                    validation_models,
                    project_models,
                    hippo_rag_models,
                    fact_models,
                ]
            )
        )

        if self._config_loader.get_str(RAG_TYPE) == RAGConfigTypeE.HYBRID:
            self._with_acomponent(
                component=LlamaIndexQdrantStartupSequence()
            )._with_acomponent(component=LlamaIndexStartupSequence())
        elif self._config_loader.get_str(RAG_TYPE) == RAGConfigTypeE.SUBQUESTION:
            self._with_acomponent(
                component=LlamaIndexQdrantStartupSequence()
            )._with_acomponent(component=LlamaIndexStartupSequence())
        elif self._config_loader.get_str(RAG_TYPE) == RAGConfigTypeE.HIPPO_RAG:
            self._with_acomponent(component=Neo4jStartupSequence())._with_acomponent(
                component=HippoRAGQdrantStartupSequence()
            )
        else:
            assert False, f"invalid rag type {self._config_loader.get_str(RAG_TYPE)}"

    async def _create_usecase(self):
        assert self._rag_systemconfig

        result = self._config_loader.load_values(text_embedding.SETTINGS_HOST)
        if result.is_error():
            raise result.get_error()
        evaluation_database = PostgresDBEvaluation()
        project_database = PostgresDBProjectDatbase()

        rag_llm: None | RAGLLM = None
        if self._config_loader.get_str(RAG_TYPE) == RAGConfigTypeE.SUBQUESTION:
            rag_llm = init_sub(self._rag_systemconfig, self._config_loader)
        if self._config_loader.get_str(RAG_TYPE) == RAGConfigTypeE.HYBRID:
            rag_llm = init_naive(self._rag_systemconfig, self._config_loader)
        if self._config_loader.get_str(RAG_TYPE) == RAGConfigTypeE.HIPPO_RAG:
            rag_llm = init_hipp_rag(self._config_loader, self._rag_systemconfig)
        if rag_llm is None:
            raise Exception(
                f"No valid RAG_TYPE {self._config_loader.get_str(RAG_TYPE)}"
            )

        assert rag_llm
        RAGUsecase.create(  # type: ignore
            rag_llm=rag_llm,
            database=evaluation_database,
            config=self._rag_systemconfig,
            project_database=project_database,
            usecase_config=RagUsecaseConfig(),
        )
