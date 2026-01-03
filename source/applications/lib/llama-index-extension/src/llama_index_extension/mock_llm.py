from typing import Any, AsyncGenerator, Optional, Sequence
from llama_index.core.base.llms.types import (
    ChatMessage,
    ChatResponseGen,
    CompletionResponse,
    CompletionResponseAsyncGen,
    CompletionResponseGen,
    LLMMetadata,
)
from llama_index.core.callbacks import CallbackManager
from llama_index.core.constants import DEFAULT_CONTEXT_WINDOW
from llama_index.core.llms.callbacks import llm_chat_callback, llm_completion_callback
from llama_index.core.llms.custom import CustomLLM
from llama_index.core.llms.llm import MessagesToPromptType, CompletionToPromptType
from llama_index.core.types import PydanticProgramMode
from pydantic import Field


class MockLLM(CustomLLM):
    max_tokens: Optional[int]
    context_window: int = Field(
        default=-1,
        description="The maximum number of context tokens for the model.",
    )

    def __init__(
        self,
        max_tokens: Optional[int] = None,
        callback_manager: Optional[CallbackManager] = None,
        system_prompt: Optional[str] = None,
        messages_to_prompt: Optional[MessagesToPromptType] = None,
        completion_to_prompt: Optional[CompletionToPromptType] = None,
        pydantic_program_mode: PydanticProgramMode = PydanticProgramMode.DEFAULT,
        context_window: int = DEFAULT_CONTEXT_WINDOW,
    ) -> None:
        super().__init__(
            max_tokens=max_tokens,
            callback_manager=callback_manager or CallbackManager([]),
            system_prompt=system_prompt,
            messages_to_prompt=messages_to_prompt,
            completion_to_prompt=completion_to_prompt,
            pydantic_program_mode=pydantic_program_mode,
            context_window=context_window,
        )

    @classmethod
    def class_name(cls) -> str:
        return "MockLLM"

    @property
    def metadata(self) -> LLMMetadata:
        return LLMMetadata(
            num_output=self.max_tokens or -1, context_window=self.context_window
        )

    def _generate_text(self, length: int) -> str:
        return " ".join(["text" for _ in range(length)])

    @llm_completion_callback()
    def complete(
        self, prompt: str, formatted: bool = False, **kwargs: Any
    ) -> CompletionResponse:
        response_text = (
            self._generate_text(self.max_tokens) if self.max_tokens else prompt
        )

        return CompletionResponse(
            text=response_text,
        )

    # @llm_completion_callback()
    # async def acomplete(
    # self, prompt: str, formatted: bool = False, **kwargs: Any
    # ) -> CompletionResponse:
    # return self.complete(prompt, formatted=formatted, **kwargs)

    # @llm_completion_callback()
    # async def astream_complete(
    # self, prompt: str, formatted: bool = False, **kwargs: Any
    # ) -> CompletionResponseAsyncGen:
    # async def gen() -> CompletionResponseAsyncGen:
    # for message in self.stream_complete(prompt, formatted=formatted, **kwargs):
    # yield message

    # # NOTE: convert generator to async generator
    # return gen()

    @llm_completion_callback()
    def stream_complete(
        self, prompt: str, formatted: bool = False, **kwargs: Any
    ) -> CompletionResponseGen:
        def gen_prompt() -> CompletionResponseGen:
            for ch in prompt:
                yield CompletionResponse(
                    text=prompt,
                    delta=ch,
                )

        def gen_response(max_tokens: int) -> CompletionResponseGen:
            for i in range(max_tokens):
                response_text = self._generate_text(i)
                yield CompletionResponse(
                    text=response_text,
                    delta="text ",
                )

        return gen_response(self.max_tokens) if self.max_tokens else gen_prompt()
