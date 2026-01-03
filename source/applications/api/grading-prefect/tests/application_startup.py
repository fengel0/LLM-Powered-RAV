# tests/test_e2e_env_provisioning.py
from __future__ import annotations

from domain.database.config.model import Config, GradingServiceConfig
import json
import logging
import os
from unittest.mock import patch

from core.config_loader import ConfigLoaderImplementation, ConfigProvisioner
from core.logger import disable_local_logging
from core.singelton import SingletonMeta

from database.session import DatabaseConfig, PostgresSession
from testcontainers.postgres import PostgresContainer

import validation_database.model as validation_model
import config_database.model as config_model

from grading_prefect.application_startup import GradingApplication

from deployment_base.enviroment.postgres_env import (
    POSTGRES_PORT,
    POSTGRES_USER,
    POSTGRES_DATABASE,
    POSTGRES_HOST,
    POSTGRES_PASSWORD,
    SETTINGS as POSTGRES_SETTINGS,
)

from deployment_base.enviroment.openai_env import (
    MAX_TOKENS,
    OPENAI_KEY,
    OPENAI_HOST,
    OPENAI_MODEL,
    SETTINGS as OPENAI_SETTINGS,
)

# --- settings keys
from grading_prefect.settings import (
    EVAL_TYPE,
    FACT_MODEL,
    SETTINGS,
    SYSTEM_PROMPT_COMPLETENESS,
    SYSTEM_PROMPT_COMPLETENESS_CONTEXT,
    SYSTEM_PROMPT_CORRECTNESS,
    GRADING_CONFIG,
)

from domain_test import AsyncTestBase

grading_config = Config(
    id="dummy",
    data=GradingServiceConfig(
        system_name="qwen3.32b-eval",
        system_prompt_correctnes='You are a strict fact detector.\n\nINPUT FORMAT:\nFact: <text describing one fact>\nAnswer: <candidate answer text>\n\nTASK:\nDetermine whether the FACT is PRESENT in the ANSWER at the *semantic* level (not just verbatim).\nAccept paraphrases, synonymous phrasing, or logically equivalent statements.\nThe answer must *affirm* the fact; hedged or negated mentions ("not", "uncertain") count as NOT present.\nIgnore trivial grammar changes, casing, punctuation, and article usage.\n\nIf the answer partially mentions the fact but omits its essential claim (e.g., mentions the city but not that it is the capital when the fact is "X is the capital of Y"), return false.\n\nOUTPUT:\nReturn ONLY valid JSON: {"is_fact_in_response": <true|false>}  (lowercase booleans).\nNo extra keys, no commentary, no markdown.\n',
        system_prompt_completness='You are a strict fact detector.\n\nINPUT FORMAT:\nFact: <text describing one fact>\nAnswer: <candidate answer text>\n\nTASK:\nDetermine whether the FACT is PRESENT in the ANSWER at the *semantic* level (not just verbatim).\nAccept paraphrases, synonymous phrasing, or logically equivalent statements.\nThe answer must *affirm* the fact; hedged or negated mentions ("not", "uncertain") count as NOT present.\nIgnore trivial grammar changes, casing, punctuation, and article usage.\n\nIf the answer partially mentions the fact but omits its essential claim (e.g., mentions the city but not that it is the capital when the fact is "X is the capital of Y"), return false.\n\nOUTPUT:\nReturn ONLY valid JSON: {"is_fact_in_response": <true|false>}  (lowercase booleans).\nNo extra keys, no commentary, no markdown.\n',
        system_prompt_completness_context='You are a context fact detector.\n\nINPUT FORMAT:\nFact: <text describing one fact>\nContext: <reference/context text>\n\nTASK:\nDoes the CONTEXT *contain or state* the FACT?\nAccept paraphrase or logically implied statements.\nIf the context contradicts the fact, or is silent/insufficient to confirm it, return false.\nDo NOT infer from world knowledge—use ONLY the provided context.\n\nOUTPUT:\nReturn ONLY valid JSON: {"is_fact_in_response": <true|false>}  (lowercase booleans).\nNo extra keys, no commentary, no markdown.\n',
        temp=0.0,
        model="qwen3.32",
    ),
    hash="",
)

logger = logging.getLogger(__name__)


class TestGradingServiceProvisioning(AsyncTestBase):
    __test__ = True

    # ------------------------ class-level (container) -------------------------
    @classmethod
    def setup_class_sync(cls):
        cls._pg = PostgresContainer(
            image="postgres:16-alpine",
            username="test",
            password="test",
            dbname="test_db",
        ).start()
        cls._pg_host = cls._pg.get_container_host_ip()
        cls._pg_port = str(cls._pg.get_exposed_port(5432))
        logger.info("Postgres started for grading e2e provisioning tests.")

    @classmethod
    def teardown_class_sync(cls):
        try:
            cls._pg.stop()
        except Exception as e:
            logger.warning("Failed to stop Postgres container: %s", e)

    # ------------------------ per-test setup/teardown -------------------------
    async def setup_method_async(self, test_name: str):
        # fresh schema each test
        cfg = DatabaseConfig(
            host=self._pg_host,
            port=self._pg_port,
            database_name="test_db",
            username="test",
            password="test",
        )
        try:
            PostgresSession._instances.clear()  # type: ignore[attr-defined]
        except Exception:
            pass

        PostgresSession.create(
            config=cfg,
            models=[config_model, validation_model],
        )
        sess = PostgresSession.Instance()
        await sess.start()
        await sess.migrations()
        await sess.shutdown()

        # Patch Prefect enviroment to prevent ephemeral server / noisy logging
        self._prefect_env = {
            "PREFECT_API_ENABLE_EPHEMERAL_SERVER": "false",
            "PREFECT_SERVER_EPHEMERAL_STARTUP_TIMEOUT_SECONDS": "90",
            "PREFECT_LOGGING_TO_API": "false",
            "PREFECT_LOGGING_TO_CONSOLE": "false",
            "PREFECT_LOGGING_LEVEL": "CRITICAL",
        }
        self._prefect_env_patcher = patch.dict(
            os.environ, self._prefect_env, clear=False
        )
        self._prefect_env_patcher.start()

        SingletonMeta.clear_all()

    async def teardown_method_async(self, test_name: str):
        try:
            await PostgresSession.Instance().shutdown()
        except Exception:
            pass
        try:
            PostgresSession._instances.clear()  # type: ignore[attr-defined]
        except Exception:
            pass

    def teardown_method_sync(self, test_name: str):
        # Unpatch prefect enviroment
        try:
            self._prefect_env_patcher.stop()
        except Exception:
            pass

        # Flush/close Prefect logging handlers to avoid "I/O on closed file"
        root = logging.getLogger()
        for h in list(root.handlers):
            if "prefect" in h.__class__.__name__.lower() or "prefect" in str(h).lower():
                try:
                    h.flush()
                except Exception:
                    pass
                try:
                    h.close()
                except Exception:
                    pass

        # Keep noisy libs quiet
        for name in (
            "prefect",
            "prefect.client",
            "prefect.server",
            "httpx",
            "httpcore",
        ):
            logging.getLogger(name).setLevel(logging.CRITICAL)

        try:
            SingletonMeta.clear_all()
        except Exception:
            pass
        disable_local_logging()

    # --------------------------------- test -----------------------------------
    async def test_app_runs_with_openai_and_with_ollama(self):
        # Pass 1: OpenAI backend
        openai_vals = self._compose_env_values_common() | self._compose_openai_values()
        file_vals = self._compose_file_values()
        self.provisioner = ConfigProvisioner(
            attributes=[*SETTINGS, *OPENAI_SETTINGS, *POSTGRES_SETTINGS],
            values={**openai_vals, **file_vals},
            create_missing_dirs=True,
        )
        self.provisioner.apply()

        # DB ping (already migrated, but ensures enviroment is wired)
        config_db = DatabaseConfig(
            host=os.environ.get(POSTGRES_HOST),  # type: ignore[arg-type]
            port=os.environ.get(POSTGRES_PORT),  # type: ignore[arg-type]
            database_name=os.environ.get(POSTGRES_DATABASE),  # type: ignore[arg-type]
            username=os.environ.get(POSTGRES_USER),  # type: ignore[arg-type]
            password=os.environ.get(POSTGRES_PASSWORD),  # type: ignore[arg-type]
        )
        PostgresSession.create(
            config=config_db, models=[config_model, validation_model]
        )
        await PostgresSession.Instance().start()
        await PostgresSession.Instance().migrations()
        await PostgresSession.Instance().shutdown()
        SingletonMeta.clear_all()

        # App lifecycle (OpenAI)
        GradingApplication.create(ConfigLoaderImplementation.create())
        GradingApplication.Instance().set_grading_config(config=grading_config)
        GradingApplication.Instance().start()
        await GradingApplication.Instance().astart()
        await GradingApplication.Instance().create_usecase()
        await GradingApplication.Instance().ashutdown()
        GradingApplication.Instance().shutdown()
        SingletonMeta.clear_all()
        disable_local_logging()

        # Pass 2: Ollama backend
        self.provisioner.restore()
        ollama_vals = self._compose_env_values_common() | self._compose_ollama_values()
        self.provisioner.values = {**ollama_vals, **file_vals}
        self.provisioner.apply()

        GradingApplication.create(ConfigLoaderImplementation.create())
        GradingApplication.Instance().set_grading_config(config=grading_config)
        GradingApplication.Instance().start()
        await GradingApplication.Instance().astart()
        await GradingApplication.Instance().create_usecase()
        await GradingApplication.Instance().ashutdown()
        GradingApplication.Instance().shutdown()
        SingletonMeta.clear_all()
        disable_local_logging()

    # ------------------------------- helpers ----------------------------------
    def _compose_env_values_common(self) -> dict[str, object]:
        """Infra knobs shared between OpenAI and Ollama runs."""
        vals: dict[str, object] = {}

        # Postgres (from container)
        vals[POSTGRES_HOST] = self._pg_host
        vals[POSTGRES_PORT] = int(self._pg_port)
        vals[POSTGRES_USER] = "test"
        vals[POSTGRES_PASSWORD] = "test"
        vals[POSTGRES_DATABASE] = "test_db"

        # Reasonable runtime knobs
        vals[MAX_TOKENS] = 2048

        # Keep OTEL disabled
        vals[FACT_MODEL] = ""

        return vals

    def _compose_openai_values(self) -> dict[str, object]:
        """Configure the app to use OpenAI."""
        vals: dict[str, object] = {}
        vals[OPENAI_KEY] = "sk-test-key-not-used"
        vals[OPENAI_MODEL] = "gpt-4o-mini"
        vals[EVAL_TYPE] = "openai"
        # Keep Ollama present-but-ignored (so selection is deterministic)
        vals[OPENAI_HOST] = "http://127.0.0.1:11434"
        vals[OPENAI_MODEL] = "llama3.1"
        return vals

    def _compose_ollama_values(self) -> dict[str, object]:
        """Configure the app to use Ollama."""
        vals: dict[str, object] = {}
        vals[OPENAI_MODEL] = "http://127.0.0.1:11434"
        vals[OPENAI_MODEL] = "llama3.1"
        vals[FACT_MODEL] = "llama3.1"
        vals[EVAL_TYPE] = "local"
        # Disable OpenAI so app picks local path
        vals[OPENAI_KEY] = ""
        vals[OPENAI_MODEL] = ""
        return vals

    def _compose_file_values(self) -> dict[str, object]:
        """Inline content for FileConfigAttribute-backed prompts/configs."""
        vals: dict[str, object] = {}
        vals[SYSTEM_PROMPT_COMPLETENESS] = (
            "You are a strict but fair grader. Assess completeness against the rubric. "
            "Return structured JSON with fields: rationale, score, rubric_breakdown."
        )
        vals[SYSTEM_PROMPT_COMPLETENESS_CONTEXT] = (
            "Context: The exam uses short answers with explicit steps. Prioritize "
            "evidence in the student response and penalize hallucinated claims."
        )
        vals[SYSTEM_PROMPT_CORRECTNESS] = (
            "Grade for mathematical correctness. Validate computations, logic, and final answers. "
            "Use a 0–100 scale and explain deductions briefly."
        )
        vals[GRADING_CONFIG] = json.dumps(
            {
                "id": "91e54238-43b3-4289-b180-4290b4f0601d",
                "stored_config": {
                    "system_name": "qwen3.32b-eval",
                    "system_prompt_completness": 'You are a strict fact detector.\n\nINPUT FORMAT:\nFact: <text describing one fact>\nAnswer: <candidate answer text>\n\nTASK:\nDetermine whether the FACT is PRESENT in the ANSWER at the *semantic* level (not just verbatim).\nAccept paraphrases, synonymous phrasing, or logically equivalent statements.\nThe answer must *affirm* the fact; hedged or negated mentions ("not", "uncertain") count as NOT present.\nIgnore trivial grammar changes, casing, punctuation, and article usage.\n\nIf the answer partially mentions the fact but omits its essential claim (e.g., mentions the city but not that it is the capital when the fact is "X is the capital of Y"), return false.\n\nOUTPUT:\nReturn ONLY valid JSON: {"is_fact_in_response": <true|false>}  (lowercase booleans).\nNo extra keys, no commentary, no markdown.\n',
                    "system_prompt_completness_context": 'You are a context fact detector.\n\nINPUT FORMAT:\nFact: <text describing one fact>\nContext: <reference/context text>\n\nTASK:\nDoes the CONTEXT *contain or state* the FACT?\nAccept paraphrase or logically implied statements.\nIf the context contradicts the fact, or is silent/insufficient to confirm it, return false.\nDo NOT infer from world knowledge—use ONLY the provided context.\n\nOUTPUT:\nReturn ONLY valid JSON: {"is_fact_in_response": <true|false>}  (lowercase booleans).\nNo extra keys, no commentary, no markdown.\n',
                    "system_prompt_correctnes": 'You are a helpful evaluator.\n\nTask Overview: You are tasked with evaluating user answers based on a given question, reference answer, and additional reference text. Your goal is to assess the correctness of the user answer using a specific metric.\nEvaluation Criteria: \n\n1. Yes/No Questions: Verify if the user’s answer aligns with the reference answer in terms of a "yes" or "no" response.\n2. Short Answers/Directives: Ensure key details such as numbers, specific nouns/verbs, and dates match those in the reference answer.\n3. Abstractive/Long Answers: The user’s answer can differ in wording but must convey the same meaning and contain the same key information as the reference answer to be considered correct.\n\nEvaluation Process: \n 1. Identify the type of question presented.\n 2. Apply the relevant criteria from the Evaluation Criteria.\n 3. Compare the user’s answer against the reference answer accordingly.\n 4. Consult the reference text for clarification when needed.\n 5. Score the answer with a binary label 0 or 1, where 0 denotes wrong and 1 denotes correct.\n\nNOTE that if the user answer is 0 or an empty string, it should get a 0 score.\n\nOUTPUT  \nReturn exactly: `{"correctness": <float>, "reasoning": "<sentence>"}` — lowercase keys, no markdown, no extra fields.\n',
                    "model": "qwen3:32b",
                    "temp": 0.0,
                },
            }
        )
        return vals
