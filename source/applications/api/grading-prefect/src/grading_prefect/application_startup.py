from deployment_base.enviroment import openai_env
from deployment_base.startup_sequence.log import LoggerStartupSequence
from deployment_base.startup_sequence.postgres import PostgresStartupSequence
from domain.database.config.model import Config, GradingServiceConfig
from config_service.usecase.config_storage import ConfigLoaderUsecase
from domain.database.config.interface import SystemConfigDatabase
from openai_client.async_openai import ConfigOpenAI, OpenAIAsyncLLM
from hippo_rag.openie import AsyncOpenIE, OpenIEConfig
from fact_store_database.state_holder import PostgresDBFactStore
from domain.llm.interface import AsyncLLM
import logging
from deployment_base.application import Application


from grading_service.usecase.grading import (  # adjust the import to where the class lives
    GradingServiceUsecases,
)


from core.config_loader import (
    ConfigLoader,
)


from validation_database.validation_db_implementation import (
    PostgresDBEvaluation,
)

import validation_database.model as validation_model
import config_database.model as config_model
import fact_store_database.model as fact_model

from config_database.db_implementation import (
    PostgresSystemConfigDatabase,
)


from deployment_base.enviroment.openai_env import (
    MAX_TOKENS,
    OPENAI_KEY,
    OPENAI_HOST,
    TEMPERATUR,
    LLM_REQUEST_TIMEOUT,
    SETTINGS as OPENAI_SETTINGS,
)

from grading_prefect.settings import (
    API_NAME,
    API_VERSION,
    EVAL_TYPE,
    FACT_MODEL,
    GRADING_CONFIG,
    PARALLEL_LLM_CALLS,
    SETTINGS,
    SYSTEM_PROMPT_COMPLETENESS_CONTEXT,
    SYSTEM_PROMPT_COMPLETENESS,
    SYSTEM_PROMPT_CORRECTNESS,
)

logger = logging.getLogger(__name__)


class GradingConfigLoaderApplication(Application):
    usecase: ConfigLoaderUsecase[Config[GradingServiceConfig]] | None = None

    def get_application_name(self) -> str:
        self._config_loader.load_values([*SETTINGS, *OPENAI_SETTINGS])
        grading_type = "local"
        if self._config_loader.get_str(EVAL_TYPE) == "openai":
            grading_type = self._config_loader.get_str(EVAL_TYPE)
            return f"{API_NAME}-{grading_type}-{API_VERSION}"
        if self._config_loader.get_str(EVAL_TYPE) == "local":
            grading_type = self._config_loader.get_str(EVAL_TYPE)
            return f"{API_NAME}-{grading_type}-{API_VERSION}"
        assert False, "invalid Eval Type"

    def _add_components(self):
        self._with_component(
            component=LoggerStartupSequence(
                application_name=self.get_application_name(),
                application_version=API_VERSION,
            )
        )._with_acomponent(component=PostgresStartupSequence(models=[config_model]))

    async def get_config(self) -> Config[GradingServiceConfig]:
        assert self.usecase, "usecase needs to be intizialized"
        config_result = await self.usecase.load_config_update_config(
            key=GRADING_CONFIG, update_lamda=update_config
        )
        if config_result.is_error():
            raise config_result.get_error()
        grading_config = config_result.get_ok()
        return grading_config

    async def _create_usecase(self):
        self._config_loader.load_values([*SETTINGS, *OPENAI_SETTINGS])

        grading_cfg_database: SystemConfigDatabase[GradingServiceConfig] = (
            PostgresSystemConfigDatabase(model=GradingServiceConfig)
        )
        self.usecase = (  # type: ignore
            ConfigLoaderUsecase(  # type: ignore
                model=Config[GradingServiceConfig],
                db=grading_cfg_database,
                config_loader=self._config_loader,
            )
        )


class GradingApplication(Application):
    _grading_config: Config[GradingServiceConfig] | None = None

    def set_grading_config(self, config: Config[GradingServiceConfig]):
        self._grading_config = config

    def get_application_name(self) -> str:
        assert self._grading_config, "You need to set grading config"
        self._config_loader.load_values([*SETTINGS, *OPENAI_SETTINGS])
        grading_type: str | None = None
        if self._config_loader.get_str(EVAL_TYPE) == "openai":
            grading_type = self._config_loader.get_str(EVAL_TYPE)
        if self._config_loader.get_str(EVAL_TYPE) == "local":
            grading_type = self._config_loader.get_str(EVAL_TYPE)
        assert grading_type, f"invalid Eval Type {grading_type}"
        return f"{API_NAME}-{grading_type}-{API_VERSION}-{self._grading_config.id}"

    def _add_components(self):
        self._with_component(
            component=LoggerStartupSequence(
                application_name=self.get_application_name(),
                application_version=API_VERSION,
            )
        )._with_acomponent(
            component=PostgresStartupSequence(models=[validation_model, fact_model])
        )

    async def _create_usecase(self):
        assert self._grading_config, "You need to set grading config"
        result = self._config_loader.load_values([*SETTINGS, *OPENAI_SETTINGS])
        if result.is_error():
            raise result.get_error()

        evaluation_database = PostgresDBEvaluation()
        # --- 5. prepare LLM client ----------------------------------------------------
        async_llm: AsyncLLM | None = None
        if self._config_loader.get_str(EVAL_TYPE) == "openai":
            # OpenAI backend
            async_llm = OpenAIAsyncLLM(
                ConfigOpenAI(
                    model=self._grading_config.data.model,
                    max_tokens=self._config_loader.get_int(MAX_TOKENS),
                    api_key=self._config_loader.get_str(OPENAI_KEY),
                    timeout=self._config_loader.get_int(LLM_REQUEST_TIMEOUT),
                    temperature=self._config_loader.get_float(TEMPERATUR),
                    context_cutoff=int(128_000 * 0.90),
                )
            )
        if self._config_loader.get_str(EVAL_TYPE) == "local":
            async_llm = OpenAIAsyncLLM(
                ConfigOpenAI(
                    model=self._grading_config.data.model,
                    max_tokens=self._config_loader.get_int(MAX_TOKENS),
                    api_key=self._config_loader.get_str(OPENAI_KEY),
                    timeout=self._config_loader.get_int(LLM_REQUEST_TIMEOUT),
                    temperature=self._grading_config.data.temp,
                    context_cutoff=int(128_000 * 0.90),
                    base_url=self._config_loader.get_str(OPENAI_HOST),
                )
            )
        assert async_llm, "Either OpenAI or Ollama credentials must be supplied"

        fact_llm = OpenAIAsyncLLM(
            ConfigOpenAI(
                model=self._config_loader.get_str(FACT_MODEL),
                max_tokens=self._config_loader.get_int(MAX_TOKENS),
                api_key=self._config_loader.get_str(OPENAI_KEY),
                timeout=self._config_loader.get_int(LLM_REQUEST_TIMEOUT),
                temperature=self._grading_config.data.temp,
                context_cutoff=int(128_000 * 0.90),
                base_url=self._config_loader.get_str(OPENAI_HOST),
            )
        )

        # --- 6. initialise grading use-cases -----------------------------------------
        GradingServiceUsecases.create(
            llm=async_llm,
            config=self._grading_config,  # ← always pass the DB-backed version
            database=evaluation_database,
            fact_store=PostgresDBFactStore(),
            openie=AsyncOpenIE(llm=fact_llm, config=OpenIEConfig()),
            worker_count=self._config_loader.get_int(PARALLEL_LLM_CALLS),
        )


def update_config(
    config: Config[GradingServiceConfig], config_loader: ConfigLoader
) -> Config[GradingServiceConfig]:
    # allow simple enviroment overrides just like the RAG bootstrap
    result = config_loader.load_values(openai_env.SETTINGS)
    if result.is_error():
        raise result.get_error()
    for _key, env_val in (
        (
            SYSTEM_PROMPT_COMPLETENESS,
            config_loader.get_str(SYSTEM_PROMPT_COMPLETENESS),
        ),
        (
            SYSTEM_PROMPT_COMPLETENESS_CONTEXT,
            config_loader.get_str(SYSTEM_PROMPT_COMPLETENESS_CONTEXT),
        ),
        (
            SYSTEM_PROMPT_CORRECTNESS,
            config_loader.get_str(SYSTEM_PROMPT_CORRECTNESS),
        ),
    ):
        if env_val:
            setattr(config.data, _key.lower(), env_val)  # names match attribute names

    config.data.temp = config_loader.get_float(TEMPERATUR)
    return config
