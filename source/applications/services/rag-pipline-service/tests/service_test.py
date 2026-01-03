# tests/test_rag_usecase.py
import logging
from unittest.mock import AsyncMock, MagicMock, patch

from core.result import Result
from core.singelton import SingletonMeta

from domain.database.config.model import (
    RAGConfig,
    RagEmbeddingConfig,
    RagRetrievalConfig,
)
from domain.rag.model import Node, RAGResponse, Conversation, RoleType

from rag_pipline_service.usecase.rag import (
    RAGUsecase,
    RagUsecaseConfig,
)

from domain_test import AsyncTestBase

logger = logging.getLogger(__name__)


# ----------------------------- helpers ---------------------------------
async def _agen(tokens):  # type: ignore
    """Async generator that yields given tokens in order."""
    for t in tokens:  # type: ignore
        yield t


class TestRAGUsecase(AsyncTestBase):
    """Covers code paths of RAGUsecase.generate_reponse with input assertions."""

    __test__ = True

    # ------------------------------------------------------------------
    # set-up / tear-down
    # ------------------------------------------------------------------
    def setup_method_sync(self, _name: str):
        # Reset singleton instance so each test starts clean
        SingletonMeta.clear_all()

        # Patch sleeps so retries/backoff don't slow the tests
        self._sleep_patch = patch("time.sleep", return_value=None)
        self._sleep_patch.start()

        # Interface mocks
        self.mock_llm = MagicMock()
        self.mock_llm.request = AsyncMock()
        self.mock_db = AsyncMock()
        self.mock_project_db = AsyncMock()

        # RAG system config
        self.config = RAGConfig(
            id="cfg-1",
            hash="",
            config_type="hybrid",
            name="",
            embedding=RagEmbeddingConfig(
                id="embed-config",
                chunk_size=9,
                chunk_overlap=9,
                models={},
                addition_information={},
            ),
            retrieval_config=RagRetrievalConfig(
                temp=0.0,
                id="",
                generator_model="llm-x",
                prompts={},
                addition_information={},
            ),
        )

        # Use-case specific cfg (no waits)
        self.usecase_cfg = RagUsecaseConfig(retries=3, time_to_wait_in_secondes=0)

        # Build singleton
        RAGUsecase.create(  # type: ignore
            rag_llm=self.mock_llm,
            database=self.mock_db,
            config=self.config,
            project_database=self.mock_project_db,
            usecase_config=self.usecase_cfg,
        )
        self.uc: RAGUsecase = RAGUsecase.Instance()

    def teardown_method_sync(self, _name: str):  # type: ignore
        self._sleep_patch.stop()
        SingletonMeta.clear_all()

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _prime_db_no_prior_answer(self):
        self.mock_db.was_question_already_answered_by_config.return_value = Result.Ok(
            None
        )

    def _prime_db_with_prior_answer(self, txt: str = "cached"):
        self.mock_db.was_question_already_answered_by_config.return_value = Result.Ok(
            txt
        )

    # ============================== SUCCESS ============================ #
    async def test_generate_response_success(self):
        sample = MagicMock(question="What is AI?", dataset_id="ds-123")
        project = MagicMock(id="proj-123")

        self.mock_db.get.return_value = Result.Ok(sample)
        self._prime_db_no_prior_answer()
        self.mock_project_db.fetch_by_name.return_value = Result.Ok(project)

        gen = _agen(["AI", " is", " powerful."])  # async generator
        nodes = [Node(id="n1", content="src", similarity=1.0, metadata={})]

        self.mock_llm.request.return_value = Result.Ok(
            RAGResponse.create_stream_response(generator=gen, nodes=nodes)
        )
        self.mock_db.add_system_answer.return_value = Result.Ok(None)

        res = await self.uc.generate_reponse("s-1")
        assert res.is_ok()
        assert res.get_ok() == self.config.id

        # ---------- Assert DB inputs ----------
        self.mock_db.get.assert_called_once_with(id="s-1")
        self.mock_db.was_question_already_answered_by_config.assert_called_once_with(
            sample_id="s-1", config_id=self.config.id
        )
        self.mock_project_db.fetch_by_name.assert_called_once_with(name="ds-123")

        # ---------- Assert LLM request inputs ----------
        self.mock_llm.request.assert_called_once()
        call_kwargs = self.mock_llm.request.call_args.kwargs
        assert call_kwargs["collection"] == "proj-123-embed-config"

        conv: Conversation = call_kwargs["conversation"]
        assert isinstance(conv, Conversation)
        assert conv.model == "llm-x"
        assert len(conv.messages) == 1
        assert conv.messages[0].message == "What is AI?"
        assert conv.messages[0].role == RoleType.User

        # ---------- Assert saved DB payload ----------
        saved = self.mock_db.add_system_answer.call_args.kwargs["system_answer"]
        assert saved.answer == "AI is powerful."
        # response_context contains JSON, so inner content is present
        assert "src" in saved.given_rag_context[0]
        assert saved.config_id == self.config.id
        # Latencies should be non-negative numbers
        assert saved.retrieval_latency_ms >= 0.0
        assert saved.generation_latency_ms >= 0.0
        # No fact extraction in new implementation
        assert saved.facts == []
        assert saved.number_of_facts_in_answer == 0
        assert saved.number_of_facts_in_context == 0
        assert saved.answer_confidence is None

    # ============================== EARLY-EXIT ========================= #
    async def test_generate_response_already_answered(self):
        sample = MagicMock(question="dup?", dataset_id="ds-dup")
        self.mock_db.get.return_value = Result.Ok(sample)
        self._prime_db_with_prior_answer("Paris")

        res = await self.uc.generate_reponse("dup-id")
        assert res.is_ok()
        assert res.get_ok() == self.config.id

        # Inputs asserted
        self.mock_db.get.assert_called_once_with(id="dup-id")
        self.mock_db.was_question_already_answered_by_config.assert_called_once_with(
            sample_id="dup-id", config_id="cfg-1"
        )
        # Should not proceed further
        self.mock_project_db.fetch_by_name.assert_not_called()
        self.mock_llm.request.assert_not_called()
        self.mock_db.add_system_answer.assert_not_called()

    # ============================== ERROR PATHS ======================== #
    async def test_generate_response_answer_fetch_error(self):
        sample = MagicMock(question="Q", dataset_id="ds")
        self.mock_db.get.return_value = Result.Ok(sample)
        self.mock_db.was_question_already_answered_by_config.return_value = Result.Err(
            Exception("fetch-err")
        )

        res = await self.uc.generate_reponse("e-ans-fetch")
        assert res.is_error()
        assert str(res.get_error()) == "fetch-err"

        # Inputs
        self.mock_db.get.assert_called_once_with(id="e-ans-fetch")
        self.mock_db.was_question_already_answered_by_config.assert_called_once_with(
            sample_id="e-ans-fetch", config_id="cfg-1"
        )
        self.mock_project_db.fetch_by_name.assert_not_called()
        self.mock_llm.request.assert_not_called()

    async def test_generate_response_project_not_found(self):
        sample = MagicMock(question="Q", dataset_id="unknown-ds")
        self.mock_db.get.return_value = Result.Ok(sample)
        self._prime_db_no_prior_answer()
        self.mock_project_db.fetch_by_name.return_value = Result.Ok(None)

        res = await self.uc.generate_reponse("e-proj-missing")
        assert res.is_error()
        assert isinstance(res.get_error(), ValueError)

        self.mock_db.get.assert_called_once_with(id="e-proj-missing")
        self.mock_project_db.fetch_by_name.assert_called_once_with(name="unknown-ds")
        self.mock_llm.request.assert_not_called()

    async def test_generate_response_project_fetch_fail(self):
        sample = MagicMock(question="Q", dataset_id="ds-err")
        self.mock_db.get.return_value = Result.Ok(sample)
        self._prime_db_no_prior_answer()
        self.mock_project_db.fetch_by_name.return_value = Result.Err(
            Exception("proj-fail")
        )

        res = await self.uc.generate_reponse("e-proj-fetch")
        assert res.is_error()
        assert str(res.get_error()) == "proj-fail"

        self.mock_project_db.fetch_by_name.assert_called_once_with(name="ds-err")
        self.mock_llm.request.assert_not_called()

    async def test_generate_response_sample_not_found(self):
        self.mock_db.get.return_value = Result.Ok(None)
        res = await self.uc.generate_reponse("missing")
        assert res.is_error()
        assert isinstance(res.get_error(), ValueError)

        self.mock_db.was_question_already_answered_by_config.assert_not_called()
        self.mock_project_db.fetch_by_name.assert_not_called()

    async def test_generate_response_db_failure(self):
        self.mock_db.get.return_value = Result.Err(Exception("db-err"))
        res = await self.uc.generate_reponse("db-fail")
        assert res.is_error()
        assert str(res.get_error()) == "db-err"

        self.mock_db.get.assert_called_once_with(id="db-fail")
        self.mock_db.was_question_already_answered_by_config.assert_not_called()

    async def test_generate_response_llm_error(self):
        """After exhausting all retries, a generic failure is returned."""
        sample = MagicMock(question="fail LLM", dataset_id="ds")
        project = MagicMock(id="proj")
        self.mock_db.get.return_value = Result.Ok(sample)
        self._prime_db_no_prior_answer()
        self.mock_project_db.fetch_by_name.return_value = Result.Ok(project)

        async def _err(*_, **__):
            return Result.Err(Exception("LLM fail"))

        self.mock_llm.request.side_effect = _err

        res = await self.uc.generate_reponse("llm-fail")
        assert res.is_error()
        assert str(res.get_error()) == "Failed to generate Response"
        assert self.mock_llm.request.call_count == self.usecase_cfg.retries + 1

        # Inputs to request were consistent across retries
        for c in self.mock_llm.request.call_args_list:
            kwargs = c.kwargs
            assert kwargs["collection"] == "proj-embed-config"
            conv: Conversation = kwargs["conversation"]
            assert conv.model == "llm-x"
            assert conv.messages[0].message == "fail LLM"
            assert conv.messages[0].role == RoleType.User

        # Downstream save not reached
        self.mock_db.add_system_answer.assert_not_called()

    async def test_generate_response_empty_llm_output(self):
        """Empty token stream is allowed as long as we have context nodes."""
        sample = MagicMock(question="Silence?", dataset_id="ds-quiet")
        project = MagicMock(id="proj-quiet")

        self.mock_db.get.return_value = Result.Ok(sample)
        self._prime_db_no_prior_answer()
        self.mock_project_db.fetch_by_name.return_value = Result.Ok(project)

        gen = _agen([])  # async generator with no tokens
        nodes = [Node(id="n1", content="ctx A", similarity=0.9, metadata={})]
        self.mock_llm.request.return_value = Result.Ok(
            RAGResponse.create_stream_response(generator=gen, nodes=nodes)
        )
        self.mock_db.add_system_answer.return_value = Result.Ok(None)

        res = await self.uc.generate_reponse("empty-out")
        assert res.is_ok()

        saved = self.mock_db.add_system_answer.call_args.kwargs["system_answer"]
        assert saved.answer == ""
        assert "ctx A" in saved.given_rag_context[0]
        assert saved.number_of_facts_in_context == 0  # always zero now
        assert saved.number_of_facts_in_answer == 0
        assert saved.facts == []

    async def test_generate_response_multiple_context_nodes(self):
        sample = MagicMock(question="Tell me", dataset_id="ds-multi")
        project = MagicMock(id="proj-multi")
        self.mock_db.get.return_value = Result.Ok(sample)
        self._prime_db_no_prior_answer()
        self.mock_project_db.fetch_by_name.return_value = Result.Ok(project)

        gen = _agen(["More", " info", " here."])
        nodes = [
            Node(id="n1", content="node1", similarity=0.8, metadata={}),
            Node(id="n2", content="node2", similarity=0.7, metadata={}),
        ]
        self.mock_llm.request.return_value = Result.Ok(
            RAGResponse.create_stream_response(generator=gen, nodes=nodes)
        )
        self.mock_db.add_system_answer.return_value = Result.Ok(None)

        res = await self.uc.generate_reponse("multi-ctx")
        assert res.is_ok()

        saved = self.mock_db.add_system_answer.call_args.kwargs["system_answer"]
        assert saved.answer == "More info here."
        # JSON body contains original content
        assert "node1" in saved.given_rag_context[0]
        assert "node2" in saved.given_rag_context[1]
        assert saved.number_of_facts_in_context == 0  # no context fact counting

    async def test_generate_response_add_system_answer_failure(self):
        sample = MagicMock(question="Save?", dataset_id="ds-save")
        project = MagicMock(id="proj-save")
        self.mock_db.get.return_value = Result.Ok(sample)
        self._prime_db_no_prior_answer()
        self.mock_project_db.fetch_by_name.return_value = Result.Ok(project)

        gen = _agen(["Saving", " issue"])
        nodes = [Node(id="n1", content="ctx", similarity=1.0, metadata={})]
        self.mock_llm.request.return_value = Result.Ok(
            RAGResponse.create_stream_response(generator=gen, nodes=nodes)
        )
        self.mock_db.add_system_answer.return_value = Result.Err(
            Exception("Insert failed")
        )

        res = await self.uc.generate_reponse("fail-insert")
        assert res.is_error()
        assert str(res.get_error()) == "Insert failed"

        # Ensure save attempted
        self.mock_db.add_system_answer.assert_called_once()
