import ast
import difflib
import json
import logging
import re
from copy import deepcopy

from core.result import Result
from domain.hippo_rag.interfaces import LLMReranker
from domain.hippo_rag.model import ConfidenceCheck, Triple
from domain.llm.interface import AsyncLLM
from domain.llm.model import TextChatMessage
from opentelemetry import trace
from pydantic import BaseModel, Field, TypeAdapter

from hippo_rag.template.dspyfilter_default_prompts import (
    DSPY_DEFAULT_ONE_INPUT_TEMPLATE,
    DSPY_DEFAULT_ONE_OUTPUT_TEMPLATE,
    DSPY_DEMOS_DEFAULT,
    DSPY_SYSTEM_PROMPT_DEFAULT,
)

logger = logging.getLogger(__name__)


class _Fact(BaseModel):
    fact: list[list[str]] = Field(
        description="A list of facts, each fact is a list of 3 strings: [subject, predicate, object]"
    )


class DSPyFilterConfig(BaseModel):
    one_input_template: str = DSPY_DEFAULT_ONE_INPUT_TEMPLATE
    one_output_template: str = DSPY_DEFAULT_ONE_OUTPUT_TEMPLATE
    system_prompt: str = DSPY_SYSTEM_PROMPT_DEFAULT
    demos: list[dict[str, str | bool]] = DSPY_DEMOS_DEFAULT


class DSPyFilter(LLMReranker):
    def __init__(self, llm_model: AsyncLLM, config: DSPyFilterConfig):
        self._config = config
        self.message_template = self._make_template()
        self.llm = llm_model
        self.default_gen_kwargs = {}
        self.tracer = trace.get_tracer("DSPyFilter")

    def _make_template(self):
        system_prompt: str = self._config.system_prompt  # type: ignore
        assert isinstance(system_prompt, str)
        message_template: list[TextChatMessage] = [
            TextChatMessage(role="system", content=system_prompt)
        ]
        demos: list[dict[str, dict[str, str | bool]]] = self._config.demos  # type: ignore
        for demo in demos:
            assert isinstance(demo, dict)
            question = demo["question"]
            fact_before_filter = demo["fact_before_filter"]
            assert isinstance(question, str)
            assert isinstance(fact_before_filter, str)

            message_template.append(
                TextChatMessage(
                    role="user",
                    content=self._config.one_input_template.format(
                        question=question,
                        fact_before_filter=fact_before_filter,
                    ),
                )
            )
            message_template.append(
                TextChatMessage(
                    role="assistant",
                    content=self._config.one_output_template.format(
                        fact_after_filter=demo["fact_after_filter"]
                    ),
                )
            )

        return message_template

    def _parse_filter(self, response: str):
        with self.tracer.start_as_current_span("parse-filter"):
            sections: list[tuple[str | None, list[str]]] = [(None, [])]
            field_header_pattern = re.compile("\\[\\[ ## (\\w+) ## \\]\\]")
            for line in response.splitlines():
                match = field_header_pattern.match(line.strip())
                if match:
                    sections.append((match.group(1), []))
                else:
                    sections[-1][1].append(line)

            sections = [(k, "\n".join(v).strip()) for k, v in sections]  # type: ignore
            parsed = []
            for k, value in sections:
                if k == "fact_after_filter":
                    try:
                        try:
                            parsed_value = json.loads(value)  # type: ignore
                        except json.JSONDecodeError:
                            try:
                                parsed_value = ast.literal_eval(value)  # type: ignore
                            except (ValueError, SyntaxError):
                                parsed_value = value
                        parsed = TypeAdapter(_Fact).validate_python(parsed_value).fact
                    except Exception as e:
                        logger.error(
                            f"Error parsing field {k}: {e}.\n\n\t\tOn attempting to parse the value\n```\n{value}\n```",
                            exc_info=True,
                        )

            return parsed

    async def _llm_call(
        self, question: str, fact_before_filter: str, model: str | None = None
    ) -> Result[str]:
        with self.tracer.start_as_current_span("llm-call"):
            # make prompt
            messages = deepcopy(self.message_template)
            messages.append(
                TextChatMessage(
                    role="user",
                    content=self._config.one_input_template.format(
                        question=question, fact_before_filter=fact_before_filter
                    ),
                )
            )
            # call openai

            # self.default_gen_kwargs["max_completion_tokens"] = 512
            return await self.llm.chat(messages, llm_model=model)

    def __call__(
        self,
        query: str,
        candidate_items: list[Triple],
        candidate_indices: list[int],
        len_after_rerank: int | None = None,
    ):
        return self.rerank(
            query=query,
            candidate_items=candidate_items,
            candidate_indices=candidate_indices,
            len_after_rerank=len_after_rerank,
        )

    async def rerank(
        self,
        query: str,
        candidate_items: list[Triple],
        candidate_indices: list[int],
        len_after_rerank: int | None = None,
        model: str | None = None,
    ) -> Result[tuple[list[int], list[Triple], ConfidenceCheck]]:
        with self.tracer.start_as_current_span("llm-rerank"):
            fact_before_filter = {
                "fact": [list(candidate_item) for candidate_item in candidate_items]
            }
            try:
                # prediction = self.program(question=query, fact_before_filter=json.dumps(fact_before_filter))
                response = await self._llm_call(
                    query, json.dumps(fact_before_filter), model
                )
                if response.is_error():
                    return response.propagate_exception()

                generated_facts = self._parse_filter(response.get_ok())
            except Exception as e:
                logger.error(e, exc_info=True)
                generated_facts = []

            result_indices: list[int] = []

            for generated_fact in generated_facts:
                closest_matched_fact = difflib.get_close_matches(
                    str(generated_fact),
                    [str(i) for i in candidate_items],
                    n=1,
                    cutoff=0.0,
                )[0]
                try:
                    result_indices.append(
                        candidate_items.index(eval(closest_matched_fact))
                    )
                except Exception as e:
                    logger.error(e, exc_info=True)

            sorted_candidate_indices: list[int] = [
                candidate_indices[i] for i in result_indices
            ]
            sorted_candidate_items: list[Triple] = [
                candidate_items[i] for i in result_indices
            ]
            return Result.Ok(
                (
                    sorted_candidate_indices[:len_after_rerank],
                    sorted_candidate_items[:len_after_rerank],
                    ConfidenceCheck(confidence=None),
                )
            )
