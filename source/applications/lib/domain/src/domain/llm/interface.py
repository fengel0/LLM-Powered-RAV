from typing import Any, AsyncGenerator, Protocol, Type, TypeVar, runtime_checkable
from pydantic import BaseModel
from core.result import Result
from domain.llm.model import TextChatMessage

T = TypeVar("T", bound=BaseModel)



class AsyncLLM(Protocol):
    """Protocol defining the asynchronous operations a Large Language Model (LLM)
    client must provide.

    Implementations wrap a concrete LLM service (e.g., OpenAI, Ollama, a local
    inference server) and expose a consistent, async API used throughout the
    code‑base. The methods are deliberately generic – they accept prompts,
    optional system messages, and optional model identifiers, and they always
    return a :class:`core.result.Result` wrapping either a concrete value or an
    async generator. This allows callers to handle success/failure uniformly
    without dealing with exceptions directly.

    The required behaviours are:
    All methods return a :class:`core.result.Result` to provide a uniform error
    handling interface.
    """

    async def run_image_against_multimodal_model(
        self,
        system_prompt: str,
        prompt: str,
        base64_image: str,
        llm_model: str | None = None,
    ) -> Result[str]:
        """Perform a multimodal inference (image + text).

        The ``base64_image`` argument supplies an image as a base64‑encoded string.
        ``system_prompt`` and ``prompt`` are combined according to the model's
        conventions. ``llm_model`` can optionally select a specific model variant.
        Returns a :class:`Result` containing the generated text response.
        """
        ...

    async def run_against_model(
        self, system_prompt: str, prompt: str
    ) -> Result[str]:
        """Simple text‑only completion.

        Sends ``system_prompt`` and ``prompt`` to the LLM and returns the generated
        response wrapped in a :class:`Result`.
        """
        ...

    async def chat(
        self, chat: list[TextChatMessage], llm_model: str | None = None
    ) -> Result[str]:
        """Synchronous chat completion.

        ``chat`` is a list of :class:`TextChatMessage` objects representing the
        conversation history. Returns the full LLM response as a string wrapped in a
        :class:`Result`.
        """
        ...

    async def stream_chat(
        self, chat: list[TextChatMessage], llm_model: str | None = None
    ) -> Result[AsyncGenerator[str, None]]:
        """Streaming chat completion.

        Yields partial responses from the LLM as they become available via an
        async generator. The overall result is wrapped in a :class:`Result`.
        """
        ...

    async def chat_structured_output(
        self, chat: list[TextChatMessage], model: Type[T], llm_model: str | None = None
    ) -> Result[T]:
        """Chat completion with structured (pydantic) output.

        The LLM response is parsed into an instance of the provided pydantic
        ``model`` type. Returns the parsed model wrapped in a :class:`Result`.
        """
        ...

    async def batch_chat(
        self, batch_chat: list[list[TextChatMessage]], llm_model: str | None = None
    ) -> Result[list[dict[str, Any]]]:
        """Run multiple chat sessions in a single request.

        ``batch_chat`` is a list where each element is a separate chat history.
        Returns a list of dictionaries containing the raw LLM responses for each
        session, all wrapped in a :class:`Result`.
        """
        ...

    async def get_structured_output(
        self,
        system_prompt: str,
        prompt: str,
        model: Type[T],
        llm_model: str | None = None,
    ) -> Result[T]:
        """Single‑prompt request returning a structured pydantic model.

        Combines ``system_prompt`` and ``prompt`` and parses the LLM's response
        into the provided pydantic ``model`` type. The parsed model is returned in
        a :class:`Result`.
        """
        ...
