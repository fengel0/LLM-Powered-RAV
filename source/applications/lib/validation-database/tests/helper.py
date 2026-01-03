import logging
from core.hash import compute_mdhash_id
import uuid
from typing import Any, Callable, Coroutine

from testcontainers.postgres import PostgresContainer


import validation_database.model as validation_models
from database.session import DatabaseConfig, PostgresSession
from domain.database.validation.model import (
    TestSample,
    RAGSystemAnswer,
    Evaluator,
)

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
#                        tiny helpers to keep tests clean                     #
# --------------------------------------------------------------------------- #
def uid() -> str:
    return uuid.uuid4().hex


def make_evaluator(username: str = "alice") -> Evaluator:
    return Evaluator(id=uid(), username=username)


def make_answer(config_id: str = "answer-1") -> RAGSystemAnswer:
    return RAGSystemAnswer(
        id="",
        answer="42",
        given_rag_context=["context"],
        config_id=config_id,
        retrieval_latency_ms=1.0,
        generation_latency_ms=2.0,
        token_count_prompt=10,
        facts=["fact_one", "fact_tow"],
        token_count_completion=20,
        number_of_facts_in_answer=20,
        number_of_facts_in_context=20,
        answer_confidence=None,
    )


def make_sample(dataset_id: str = "dataset_id") -> TestSample:
    return TestSample(
        id=uid(),
        dataset_id=dataset_id,
        retrival_complexity=0.5,
        question_hash=compute_mdhash_id(str(uuid.uuid4())),
        question="What is the answer to life?",
        expected_answer="42",
        expected_facts=["42"],
        expected_context="42",
        question_type="numeric",
        metatdata={"lol": "i"},
        metatdata_filter={"tmp": ["lol", "lol"]},
    )


# --------------------------------------------------------------------------- #
#                       container / session initialisation                    #
# --------------------------------------------------------------------------- #
class PostgresTestMixin:
    async def _run_with_postgres(
        self,
        coro: Callable[[], Coroutine[Any, Any, None]],
    ) -> None:
        with PostgresContainer(
            image="postgres:16-alpine",
            username="test",
            password="test",
            dbname="test_db",
        ) as pg:
            cfg = DatabaseConfig(
                host=pg.get_container_host_ip(),
                port=str(pg.get_exposed_port(pg.port)),
                database_name="test_db",
                username="test",
                password="test",
            )

            await self._create_database(cfg)
            try:
                await coro()
            finally:
                await self.session.shutdown()

        logger.info("PostgreSQL container stopped")

    async def _create_database(self, cfg: DatabaseConfig) -> None:
        # reset singleton so every test starts clean
        PostgresSession._instances = {}  # type: ignore
        self.session = PostgresSession.create(  # type: ignore
            config=cfg,
            models=[validation_models],  # <-- register FileDB model
        )
        await self.session.start()
        await self.session.migrations()
