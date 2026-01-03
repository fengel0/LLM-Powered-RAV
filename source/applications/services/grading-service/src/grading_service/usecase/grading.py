from core.result import Result
import asyncio
from core.hash import compute_mdhash_id
from core.que_runner import index_with_queue
from core.model import NotFoundException
from domain.database.validation.interface import (
    EvaluationDatabase,
    RatingLLM,
)
from domain.database.config.model import GradingServiceConfig
from domain.database.validation.model import RAGSystemAnswer, TestSample
from domain.hippo_rag.interfaces import OpenIEInterface
import logging
from core.singelton import BaseSingleton
from domain.llm.interface import AsyncLLM
from domain.database.config.model import (
    Config,
)
from domain.database.facts.interface import FactStore
from pydantic import BaseModel, Field
from opentelemetry import trace

logger = logging.getLogger(__name__)


class IsTheFactInTheResponse(BaseModel):
    is_fact_in_response: bool


class SmallRating(BaseModel):
    correctness: float = Field(ge=0, le=1)
    reasoning: str


class FactsHolder(BaseModel):
    anwers: list[bool]
    context: list[bool]
    relevant_chunks: list[int]


class GradingServiceUsecases(BaseSingleton):

    """
    Grading Usecases
    will evaluate RAG-Systems useing an LLM-Judge
    this usecase will
    - count facts in the answer and in the context
    - check what facts are present in the answer and in the context
    - will stored what chunks contain relevant informations
    """

    tracer: trace.Tracer
    _llm: AsyncLLM
    _fact_store: FactStore
    _database: EvaluationDatabase
    _openie: OpenIEInterface
    _worker_count: int

    def _init_once(
        self,
        llm: AsyncLLM,
        openie: OpenIEInterface,
        fact_store: FactStore,
        config: Config[GradingServiceConfig],
        database: EvaluationDatabase,
        worker_count: int = 1,
    ):
        logger.info("created GradingServiceUsecases Usecase")
        self.tracer = trace.get_tracer("GradingServiceUsecases")
        self._worker_count = worker_count
        self._fact_store = fact_store
        self._llm = llm
        self._openie = openie
        self._config = config
        self._database = database

    async def evaluate_answer(
        self, test_sample_id: str, candidate_to_evaluate: str
    ) -> Result[None]:
        with self.tracer.start_as_current_span("generate-response-question"):
            result, can_begin = await self._can_evaluation_begin(
                test_sample_id=test_sample_id,
                candidate_to_evaluate=candidate_to_evaluate,
            )
            if result.is_error():
                return result.propagate_exception()

            if not can_begin:
                return Result.Ok()

            answer_container, sample = result.get_ok()

            result = await self._extract_facts_from_answer(
                answer_container=answer_container
            )
            if result.is_error():
                return result.propagate_exception()

            result = await self._eval_facts(
                answer_container=answer_container, sample=sample
            )
            if result.is_error():
                return result.propagate_exception()
            facts_answer = result.get_ok().anwers
            facts_context = result.get_ok().context
            relevant_chunks = result.get_ok().relevant_chunks

            with self.tracer.start_as_current_span("evaluate answer"):
                provide_facts = ""
                for index, fact in enumerate(sample.expected_facts):
                    provide_facts = (
                        f"{provide_facts} {fact} |  is statet:{facts_answer[index]} \n"
                    )

                evaluated_result = await self._llm.get_structured_output(
                    self._config.data.system_prompt_correctnes,
                    prompt=(
                        f"Question: {sample.question}\n"
                        f"Fact check results: {provide_facts}\n"
                        f"Reference Answer: {sample.expected_answer}\n"
                        f"User Answer: {answer_container.answer} \n"
                    ),
                    model=SmallRating,
                )
                if evaluated_result.is_error():
                    return evaluated_result.propagate_exception()

                evaluated_optional = evaluated_result.get_ok()

            creator = self._config.id
            rating = RatingLLM(
                config_id=creator,
                rationale=evaluated_optional.reasoning,
                completeness=facts_answer,
                completeness_in_data=facts_context,
                relevant_chunks=relevant_chunks,
                correctness=evaluated_optional.correctness,
            )

            result = await self._database.add_llm_rating(
                answer_id=answer_container.id, rating=rating
            )
            if result.is_error():
                return result.propagate_exception()
            return Result.Ok()

    async def _can_evaluation_begin(
        self, test_sample_id: str, candidate_to_evaluate: str
    ) -> tuple[Result[tuple[RAGSystemAnswer, TestSample]], bool]:
        sample_result = await self._database.get(id=test_sample_id)
        if sample_result.is_error():
            return sample_result.propagate_exception(), False
        sample_optional = sample_result.get_ok()
        if sample_optional is None:
            return Result.Err(
                NotFoundException(f"Sample with id Not Found {test_sample_id}")
            ), False
        sample = sample_optional

        answer_result = await self._database.was_question_already_answered_by_config(
            sample_id=test_sample_id, config_id=candidate_to_evaluate
        )
        if answer_result.is_error():
            return answer_result.propagate_exception(), False
        answer_optional = answer_result.get_ok()
        if answer_optional is None:
            return Result.Err(
                NotFoundException(
                    f"Answer Not Found {candidate_to_evaluate} in {test_sample_id} not found"
                )
            ), False

        is_already_answered_result = (
            await self._database.was_answer_of_question_already_evaled_by_system(
                sample_id=sample.id,
                config_eval_id=self._config.id,
                config_rag=candidate_to_evaluate,
            )
        )
        if is_already_answered_result.is_error():
            return is_already_answered_result.propagate_exception(), False

        if is_already_answered_result.get_ok():
            return Result.Ok((answer_optional, sample)), False

        return Result.Ok((answer_optional, sample)), True

    async def _extract_facts_from_answer(self, answer_container: RAGSystemAnswer):
        facts_count_in_context: int = 0

        logger.info("extract facts form answer")
        with self.tracer.start_as_current_span("extract-facts-from-answer"):
            facts_answer_result = await self._extract_facts(answer_container.answer)
            if facts_answer_result.is_error():
                return facts_answer_result.propagate_exception()
            facts_in_answer = facts_answer_result.get_ok()

        logger.info("extract facts form context")
        with self.tracer.start_as_current_span("extract-facts-from-context"):
            counter_lock = asyncio.Lock()

            async def _worker_function(context: str) -> Result[None]:
                nonlocal facts_count_in_context
                facts_context_result = await self._extract_facts(context)
                if facts_context_result.is_error():
                    return facts_context_result.propagate_exception()

                async with counter_lock:
                    facts_in_context = facts_context_result.get_ok()
                    facts_count_in_context = facts_count_in_context + len(
                        facts_in_context
                    )
                return Result.Ok()

            # spawn N workers
            result = await index_with_queue(
                objects=answer_container.given_rag_context,
                workers=self._worker_count,
                index_one=_worker_function,
            )

        result = await self._database.add_fact_counts_to_system_id(
            answer_id=answer_container.id,
            facts=facts_in_answer,
            number_of_facts_in_anwer=len(facts_in_answer),
            number_of_facts_in_context=facts_count_in_context,
        )
        if result.is_error():
            return result.propagate_exception()
        return Result.Ok()

    async def _eval_facts(
        self, answer_container: RAGSystemAnswer, sample: TestSample
    ) -> Result[FactsHolder]:
        context = answer_container.given_rag_context

        counter_lock = asyncio.Lock()
        facts_answer: list[bool] = [False] * len(sample.expected_facts)
        facts_context: list[bool] = [False] * len(sample.expected_facts)
        relevant_chunks: set[int] = set()

        objs = [(index, fact) for index, fact in enumerate(sample.expected_facts)]

        with self.tracer.start_as_current_span("check if answer contains facts"):

            async def _worker_function_answer(
                index_fact: tuple[int, str],
            ) -> Result[None]:
                nonlocal facts_answer
                index = index_fact[0]
                fact = index_fact[1]
                with self.tracer.start_as_current_span(
                    f"check for fact {index} answer"
                ):
                    fact_check_result = await self._llm.get_structured_output(
                        self._config.data.system_prompt_completness,
                        prompt=f"Fact: {fact}\nContext: {answer_container.answer}",
                        model=IsTheFactInTheResponse,
                    )
                    if fact_check_result.is_error():
                        return fact_check_result.propagate_exception()

                    async with counter_lock:
                        fact_check_optional = fact_check_result.get_ok()
                        facts_answer[index] = fact_check_optional.is_fact_in_response
                        logger.info(f"searched fact {index} in answer")
                    return Result.Ok()

            result = await index_with_queue(
                objects=objs,
                workers=self._worker_count,
                index_one=_worker_function_answer,
            )
            if result.is_error():
                return result.propagate_exception()
            logger.info("finished answer processing")

        with self.tracer.start_as_current_span("check if context contains facts"):

            async def _worker_function_context(
                index_fact: tuple[int, str],
            ) -> Result[None]:
                nonlocal facts_context
                nonlocal context
                index = index_fact[0]
                fact = index_fact[1]
                with self.tracer.start_as_current_span(
                    f"check for fact {index} in context"
                ):
                    for index_context, context_entry in enumerate(context):
                        fact_check_context_result = (
                            await self._llm.get_structured_output(
                                self._config.data.system_prompt_completness_context,
                                prompt=f"Fact: {fact}\nContext: {context_entry}",
                                model=IsTheFactInTheResponse,
                            )
                        )
                        if fact_check_context_result.is_error():
                            return fact_check_context_result.propagate_exception()

                        fact_check_context_optional = fact_check_context_result.get_ok()
                        async with counter_lock:
                            facts_context[index] = (
                                fact_check_context_optional.is_fact_in_response
                            )
                            if fact_check_context_optional.is_fact_in_response:
                                relevant_chunks.add(index)

                            percent = (index_context + 1) / len(context)
                            logger.info(
                                f"search fact index {index} in context {percent:.2f}"
                            )
                            if facts_context[index]:
                                return Result.Ok()
                    return Result.Ok()

            result = await index_with_queue(
                objects=objs,
                workers=self._worker_count,
                index_one=_worker_function_context,
            )
            if result.is_error():
                return result.propagate_exception()
            logger.info("finished context processing")

        return Result.Ok(
            FactsHolder(
                anwers=facts_answer,
                context=facts_context,
                relevant_chunks=list(relevant_chunks),
            )
        )

    async def _extract_facts(self, passage: str) -> Result[list[str]]:
        hash = compute_mdhash_id(passage)
        result = await self._fact_store.get_facts_to_hash(hash=hash)
        if result.is_error():
            return result.propagate_exception()

        facts = result.get_ok()
        if facts is None:
            result = await self._openie.openie(chunk_key=hash, passage=passage)
            if result.is_error():
                return result.propagate_exception()
            facts = [str(triple) for triple in result.get_ok().triplets.triples]
            result = await self._fact_store.store_facts(hash=hash, facts=facts)
            if result.is_error():
                return result.propagate_exception()
        else:
            logger.info("used chached")
        return Result.Ok(facts)
