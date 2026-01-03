from core.result import Result
import time
import logging
from core.singelton import BaseSingleton
from domain.rag.model import BaseModel, Conversation, Message, RoleType
from domain.rag.interface import RAGLLM
from domain.database.validation.interface import EvaluationDatabase
from domain.database.project.interface import ProjectDatabase
from domain.database.config.model import RAGConfig
from domain.database.validation.model import (
    RAGSystemAnswer,
)
from opentelemetry import trace


logger = logging.getLogger(__name__)


class RagUsecaseConfig(BaseModel):
    retries: int = 3
    time_to_wait_in_secondes: int = 5


class RAGUsecase(BaseSingleton):

    """
    RAG usecase for System Evaluation
    generates a answer to a given questions and stores it's answer, context, retrieval and generation time
    """

    tracer: trace.Tracer
    rag_llm: RAGLLM
    _database: EvaluationDatabase
    _project_database: ProjectDatabase
    _config: RAGConfig
    _usecase_config: RagUsecaseConfig = RagUsecaseConfig()

    def _init_once(
        self,
        rag_llm: RAGLLM,
        database: EvaluationDatabase,
        config: RAGConfig,
        project_database: ProjectDatabase,
        usecase_config: RagUsecaseConfig,
    ):
        logger.info("created SimpleRAGUsecase Usecase")
        self.tracer = trace.get_tracer("SimpleRAGUsecase")
        self.rag_llm = rag_llm
        self._database = database
        self._config = config
        self._project_database = project_database
        self._usecase_config = usecase_config

    async def generate_reponse(self, test_sample_id: str) -> Result[str]:
        with self.tracer.start_as_current_span("simple-rag-request"):
            test_sample_result = await self._database.get(id=test_sample_id)
            if test_sample_result.is_error():
                return test_sample_result.propagate_exception()
            sample_result_optional = test_sample_result.get_ok()
            if sample_result_optional is None:
                return Result.Err(
                    ValueError(f"test_sample with id {test_sample_id} not found")
                )
            sample = sample_result_optional

            optional_answer_result = (
                await self._database.was_question_already_answered_by_config(
                    sample_id=test_sample_id, config_id=self._config.id
                )
            )
            if optional_answer_result.is_error():
                return optional_answer_result.propagate_exception()
            optional_answer = optional_answer_result.get_ok()
            if optional_answer:
                return Result.Ok(self._config.id)

            project_result = await self._project_database.fetch_by_name(
                name=sample.dataset_id
            )

            if project_result.is_error():
                return project_result.propagate_exception()

            optional_project = project_result.get_ok()
            if optional_project is None:
                return Result.Err(
                    ValueError(f"Project with Name {sample.dataset_id} not found")
                )

            project = optional_project
            response_message: str | None = None
            response_context: list[str] = []
            retries = 0
            retrival_ms = 0.0
            generation_ms = 0.0
            request_failed = True

            while retries <= self._usecase_config.retries and request_failed:
                try:
                    start_time = time.perf_counter()
                    response_result = await self.rag_llm.request(
                        conversation=Conversation(
                            messages=[
                                Message(message=sample.question, role=RoleType.User)
                            ],
                            model=self._config.retrieval_config.generator_model,
                        ),
                        # metadata_filters=sample.metatdata_filter,
                        collection=f"{project.id}-{self._config.embedding.id}",
                    )
                    if response_result.is_error():
                        raise response_result.get_error()

                    response = response_result.get_ok()
                    assert response.generator
                    response_message = ""
                    for node in response.nodes:
                        response_context.append(node.model_dump_json())

                    start_time_generation = time.perf_counter()
                    async for token in response.generator:
                        response_message = f"{response_message}{token}"
                    generation_ms = (
                        time.perf_counter() - start_time_generation
                    ) * 1_000
                    total_ms = (time.perf_counter() - start_time) * 1_000
                    retrival_ms = total_ms - generation_ms

                    request_failed = False
                except Exception as e:
                    logger.error(
                        f"an error appeared will generating response: {e}, will retry"
                    )
                    request_failed = True
                    retries = retries + 1
                    time.sleep(
                        pow(self._usecase_config.time_to_wait_in_secondes, retries)
                    )

            if response_message is None or len(response_context) == 0:
                logger.error(f"Response Context {response_context}")
                logger.error(f"Respons Message {response_message}")
                return Result.Err(Exception("Failed to generate Response"))

            result = await self._database.add_system_answer(
                sample_id=test_sample_id,
                system_answer=RAGSystemAnswer(
                    id="",
                    answer=response_message,
                    given_rag_context=response_context,
                    config_id=self._config.id,
                    retrieval_latency_ms=retrival_ms,
                    generation_latency_ms=generation_ms,
                    token_count_prompt=0,
                    token_count_completion=0,
                    facts=[],
                    number_of_facts_in_answer=0,
                    number_of_facts_in_context=0,
                    answer_confidence=None,
                ),
            )

            if result.is_error():
                return result.propagate_exception()

            return Result.Ok(self._config.id)
