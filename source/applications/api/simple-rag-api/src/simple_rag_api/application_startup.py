import logging
from typing import Any

import config_database.model as config_models

# import fact_store_database.model as fact_models
import hippo_rag_database.model as hippo_rag_models

import project_database.model as project_models

# import validation_database.model as validation_models
from config_database.db_implementation import PostgresRAGConfigDatabase
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
from deployment_base.startup_sequence.startup_hippo import init_hipp_rag
from deployment_base.startup_sequence.startup_naive import init_naive
from deployment_base.startup_sequence.startup_sub import init_sub
from deployment_base.enviroment import text_embedding, vllm_reranker
from domain.database.config.interface import RAGConfigDatabase
from domain.database.config.model import (
    RAGConfig,
    RAGConfigTypeE,
    RagEmbeddingConfig,
    RagRetrievalConfig,
)
from domain.database.project.model import Project
from domain.rag.interface import RAGLLM
from hippo_rag.implementation import HippoRAG
from project_database.project_db_implementation import (
    PostgresDBProjectDatbase,
    ProjectDatabase,
)
from simple_rag.llama_index_rag import LlamaIndexRAG, LlamaIndexSubRAG

from simple_rag_api.api.context_store import ContextStore
from simple_rag_api.settings import (
    API_NAME,
    API_VERSION,
    CONTEXT_MAX_ITEMS,
    CONTEXT_TTL_SECONDS,
    DEFAULT_HIP_CONFIG,
    DEFAULT_SIMPLE_CONFIG,
    DEFAULT_SUB_CONFIG,
    SETTINGS,
)


logger = logging.getLogger(__name__)


class RAGCofigApplication(Application):
    config_database: RAGConfigDatabase | None = None

    async def get_configs(self) -> Result[list[RAGConfig]]:
        assert self.config_database, "call create_usecase first"

        self._config_loader.load_values(SETTINGS)
        simple_config_id = self._config_loader.get_str(DEFAULT_SIMPLE_CONFIG)
        sub_config_id = self._config_loader.get_str(DEFAULT_SUB_CONFIG)
        hip_config_id = self._config_loader.get_str(DEFAULT_HIP_CONFIG)

        configs: list[RAGConfig] = []

        for config in [simple_config_id, sub_config_id, hip_config_id]:
            config_result = await self.config_database.get_config_by_id(config)
            if config_result.is_error():
                raise config_result.get_error()
            found_config = config_result.get_ok()
            if found_config:
                configs.append(found_config)
            else:
                logger.warning(f"config {config} not found")
        if len(configs) == 0:
            raise Exception("no configs loaded")

        return Result.Ok(configs)

    def get_application_name(self) -> str:
        return f"{API_NAME}-{API_VERSION}"

    def _add_components(self):
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
        result = self._config_loader.load_values(SETTINGS)
        if result.is_error():
            raise result.get_error()
        self.config_database = PostgresRAGConfigDatabase()


class RAGAPIApplication(Application):
    project_database: ProjectDatabase | None = None
    config_database: RAGConfigDatabase | None = None
    context_store: ContextStore | None = None

    hippo_rag_llm: HippoRAG | None = None
    sub_question: LlamaIndexSubRAG | None = None
    simple_question: LlamaIndexRAG | None = None
    configs: list[RAGConfig] = []

    def set_default_configs(self, configs: list[RAGConfig]):
        self.configs = configs

    def get_llm_based_on_config_type(self, config: RAGConfig) -> RAGLLM:
        if config.config_type == RAGConfigTypeE.HYBRID:
            return init_naive(config, self._config_loader)  # type: ignore
        if config.config_type == RAGConfigTypeE.SUBQUESTION:
            return init_sub(config, self._config_loader)  # type: ignore
        if config.config_type == RAGConfigTypeE.HIPPO_RAG:
            return init_hipp_rag(self._config_loader, config)  # type: ignore

        logger.error("no valid configuration type")
        raise Exception("no valid configuration type")

    def store_context(self, context_id: str, context: list[dict[str, Any]]):
        assert self.context_store, (
            "context store must first be created through create_usecase"
        )
        self.context_store.put(context_id, context)

    def get_context(self, context_id: str) -> list[dict[str, Any]] | None:
        assert self.context_store, (
            "context store must first be created through create_usecase"
        )
        return self.context_store.get(context_id)

    async def get_all_project_names(self) -> Result[list[tuple[str, str]]]:
        assert self.project_database, (
            "project database must first be created through create_usecase"
        )
        projects_result = await self.project_database.get_all()
        if projects_result.is_error():
            return projects_result.propagate_exception()
        projects = [(p.id, p.name) for p in projects_result.get_ok()]
        return Result.Ok(projects)

    async def get_all_config(
        self, filter_for_type: str | None = None
    ) -> Result[list[dict[str, dict[str, Any]]]]:
        assert self.config_database, (
            "config database must first be created through create_usecase"
        )
        configs_result = await self.config_database.fetch_all()
        if configs_result.is_error():
            return configs_result.propagate_exception()
        if filter_for_type:
            configs = [
                {p.id: p.model_dump()}
                for p in configs_result.get_ok()
                if p.config_type == filter_for_type
            ]
        else:
            configs = [{p.id: p.model_dump()} for p in configs_result.get_ok()]
        return Result.Ok(configs)
        return Result.Ok(
            [
                {
                    "dummy": RAGConfig(
                        id="dummy",
                        hash="lol",
                        name="nice one",
                        embedding=RagEmbeddingConfig(
                            id="f",
                            chunk_size=0,
                            chunk_overlap=0,
                            models={},
                            addition_information={},
                        ),
                        retrieval_config=RagRetrievalConfig(
                            id="",
                            generator_model="",
                            temp=0.0,
                            prompts={},
                            addition_information={},
                        ),
                    ).model_dump()
                }
            ]
        )

    async def get_config_by_id(self, id: str) -> Result[RAGConfig | None]:
        assert self.config_database, (
            "config database must first be created through create_usecase"
        )
        return await self.config_database.get_config_by_id(id)

    async def get_project(self, id: str) -> Result[Project | None]:
        assert self.project_database, (
            "project database must first be created through create_usecase"
        )
        return await self.project_database.get(id)

    def get_application_name(self) -> str:
        return f"{API_NAME}-{API_VERSION}"

    def _add_components(self):
        result = self._config_loader.load_values(
            [*SETTINGS, *text_embedding.SETTINGS_HOST, *vllm_reranker.SETTINGS]
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
                    project_models,
                    hippo_rag_models,
                    config_models,
                ]
            )
        )._with_acomponent(
            component=LlamaIndexQdrantStartupSequence()
        )._with_acomponent(component=LlamaIndexStartupSequence())._with_acomponent(
            component=Neo4jStartupSequence()
        )._with_acomponent(component=HippoRAGQdrantStartupSequence())

    async def _create_usecase(self):
        result = self._config_loader.load_values(SETTINGS)
        if result.is_error():
            raise result.get_error()
        self.project_database = PostgresDBProjectDatbase()
        self.config_database = PostgresRAGConfigDatabase()
        self.context_store = ContextStore(
            max_items=self._config_loader.get_int(CONTEXT_MAX_ITEMS),
            ttl_seconds=self._config_loader.get_int(CONTEXT_TTL_SECONDS),
        )

        for config in self.configs:
            if config.config_type == RAGConfigTypeE.HYBRID:
                self.simple_question = init_naive(config, self._config_loader)  # type: ignore
            if config.config_type == RAGConfigTypeE.SUBQUESTION:
                self.sub_question = init_sub(config, self._config_loader)  # type: ignore
            if config.config_type == RAGConfigTypeE.HIPPO_RAG:
                self.hippo_rag_llm = init_hipp_rag(self._config_loader, config)  # type: ignore
