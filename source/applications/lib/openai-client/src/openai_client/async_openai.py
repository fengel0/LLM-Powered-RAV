from __future__ import annotations

import tiktoken
import asyncio
import logging
from typing import Any, AsyncGenerator, Callable, Iterable, Type, TypeVar

from domain.llm.model import TextChatMessage
from opentelemetry import trace
from pydantic import BaseModel

from core.result import Result
from domain.llm.interface import AsyncLLM, T
from openai import (
    AsyncOpenAI,
    BadRequestError,
    RateLimitError,
    APIError,  # type: ignore
)
from openai.types.chat import ChatCompletion, ChatCompletionMessageParam

logger = logging.getLogger(__name__)

R = TypeVar("R")


# ---------------------------------------------------------------------------
# Public configuration -------------------------------------------------------
# ---------------------------------------------------------------------------


class ConfigOpenAI(BaseModel):
    """Runtime configuration for :class:`OpenAIAsyncLLM`."""

    api_key: str | None = None
    model: str = "gpt-4o"
    max_tokens: int = 4_096
    temperature: float = 0.7
    timeout: float = 60.0
    context_cutoff: int = 128_000
    tokinzer_model: str = "cl100k_base"
    base_url: str | None = None  # for self-hosted / Azure endpoints
    retries: int = 3  # attempts = initial try + (retries-1) retries
    does_support_structured_output: bool = True


# ---------------------------------------------------------------------------
# Wrapper class --------------------------------------------------------------
# ---------------------------------------------------------------------------


class OpenAIAsyncLLM(AsyncLLM):
    """Async wrapper for OpenAI Chat Completions with first-class **structured
    output** support.

    The wrapper exposes three helper methods:

    * :py:meth:`run_against_model` – simple text → text.
    * :py:meth:`run_image_against_multimodal_model` – text + image → text.
    * :py:meth:`get_structured_output` – text → *typed* JSON using either
      **JSON mode** or **tool-calling strict mode** (see *mode* arg).
    """

    def __init__(self, config: ConfigOpenAI):
        # Normalise retries value (at least 1 attempt).
        config.retries = max(config.retries, 1)
        self.config = config

        # Lazily-initialized OpenAI client (keeps httpx Client under the hood).
        self.client = AsyncOpenAI(
            api_key=config.api_key,
            timeout=config.timeout,
            base_url=config.base_url,
        )
        self.tracer = trace.get_tracer("OpenAIAsyncLLM")
        self._enc = tiktoken.get_encoding(self.config.tokinzer_model)

    async def aclose(self) -> None:
        """
        Close underlying HTTP resources. MUST be awaited before the loop ends.
        Safe to call multiple times.
        """
        try:
            await self.client.close()
        except Exception:
            logger.debug("Ignoring error during OpenAIAsyncLLM.aclose()", exc_info=True)

    def _count_tokens_str(self, s: str) -> int:
        return len(self._enc.encode(s))

    def _shrink_to_fit(self, text: str) -> tuple[str, int]:
        original_tokens = self._count_tokens_str(text)
        tokens_cut = 0

        if original_tokens <= self.config.context_cutoff:
            return text, 0

        current_tokens = original_tokens
        # 1) Drop oldest turns from 'rest' (i.e., from the beginning of 'rest')
        while current_tokens > self.config.context_cutoff:
            current_tokens = self._count_tokens_str(text)
            ids = self._enc.encode(text)
            keep = ids[-self.config.context_cutoff :]
            text = self._enc.decode(keep)

            tokens_cut = original_tokens - len(keep)
            if tokens_cut > 0:
                logger.warning(
                    "[openai] text trimmed: cut %d tokens (from %d → %d).",
                    tokens_cut,
                    original_tokens,
                    len(keep),
                )
        return text, tokens_cut

    # ------------------------------------------------------------------
    # Public helpers ----------------------------------------------------
    # ------------------------------------------------------------------

    async def run_against_model(
        self, system_prompt: str, prompt: str, llm_model: str | None = None
    ) -> Result[str]:
        """Single-turn helper: **plain** text in –> text out."""
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]
        return await self._chat_with_retries(
            messages,
            parser=lambda r: r.choices[0].message.content or "",
            llm_model=llm_model,
        )

    async def run_image_against_multimodal_model(
        self,
        system_prompt: str,
        prompt: str,
        base64_image: str,
        llm_model: str | None = None,
    ) -> Result[str]:
        """Single-turn helper: text + **base64 image** –> text out.

        ``base64_image`` can be either a bare Base-64 string or a data URI (the
        latter is what the Vision models expect). We normalise automatically.
        """

        if not base64_image.startswith("data:image/"):
            base64_image = f"data:image/jpeg;base64,{base64_image}"

        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": base64_image}},
                ],
            },
        ]
        return await self._chat_with_retries(
            messages,
            parser=lambda r: r.choices[0].message.content or "",
            llm_model=llm_model,
        )

    # ------------------------------------------------------------------
    # Structured output -------------------------------------------------
    # ------------------------------------------------------------------

    async def get_structured_output(
        self,
        system_prompt: str,
        prompt: str,
        model: Type[T],
        llm_model: str | None = None,
    ) -> Result[T]:
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": self._shrink_to_fit(prompt)[0]},
        ]

        response_format: Type[T] | None = None
        if self.config.does_support_structured_output:
            response_format = model
        else:
            logger.warning(
                "called structured output on model that according to the configuration does not support"
            )

        return await self._chat_with_retries(
            messages,
            parser=lambda r: model.model_validate_json(
                r.choices[0].message.content or ""
            ),
            response_format=response_format,
            llm_model=llm_model,
        )

    # ------------------------------------------------------------------
    # Internal machinery ------------------------------------------------
    # ------------------------------------------------------------------

    async def _chat_with_retries(
        self,
        messages: Iterable[ChatCompletionMessageParam],
        parser: Callable[[ChatCompletion], R],
        response_format: Type[BaseModel] | None = None,
        llm_model: str | None = None,
        **create_kwargs: Any,
    ) -> Result[R]:
        """Centralised retry loop with exponential back-off.

        ``create_kwargs`` are forwarded verbatim to
        :py:meth:`openai.AsyncOpenAI.chat.completions.create` – this is how we
        pass *response_format*, *tools*, etc. from the public helpers above.
        """
        backoff = 1.0
        attempted = 0
        last_err: Exception | Result[Any] | None = None

        while attempted < self.config.retries:
            attempted += 1
            try:
                with self.tracer.start_as_current_span("openai-chat"):
                    if response_format:
                        response = await self.client.chat.completions.parse(
                            model=llm_model if llm_model else self.config.model,
                            messages=list(messages),  # convert iterable once per retry
                            max_tokens=self.config.max_tokens,
                            temperature=self.config.temperature,
                            response_format=response_format,
                            **create_kwargs,
                        )

                    else:
                        response = await self.client.chat.completions.create(  # type: ignore
                            model=llm_model if llm_model else self.config.model,
                            messages=list(messages),  # convert iterable once per retry
                            max_tokens=self.config.max_tokens,
                            temperature=self.config.temperature,
                            **create_kwargs,
                        )

                    parsed = parser(response)  # type: ignore
                    if parsed is None or (
                        isinstance(parsed, str) and not parsed.strip()
                    ):
                        raise ValueError("Empty response from LLM")
                    return Result.Ok(parsed)

            # ------------------------------------------------------------
            # Error handling & retry policy ------------------------------
            # ------------------------------------------------------------
            except (RateLimitError, APIError) as exc:
                # *Recoverable* errors → back-off & retry.
                logger.warning(
                    "[openai] recoverable error on attempt %d/%d: %s",
                    attempted,
                    self.config.retries,
                    exc,
                )
                last_err = exc
            except BadRequestError as exc:
                # 4xx schema/param errors – do *not* retry.
                return Result.Err(exc)
            except Exception as exc:  # catch network hiccups etc.
                logger.warning(
                    "[openai] transport error on attempt %d/%d: %s",
                    attempted,
                    self.config.retries,
                    exc,
                )
                last_err = exc

            if attempted < self.config.retries:
                await asyncio.sleep(backoff)
                backoff *= 2  # exponential back-off

        # Exhausted all retries → bubble last error out via Result.Err.
        return Result.Err(last_err or RuntimeError("Unknown OpenAI error"))

    async def chat(
        self, chat: list["TextChatMessage"], llm_model: str | None = None
    ) -> Result[str]:
        """Multi-turn chat → raw text."""
        messages = _to_openai_messages(chat)
        return await self._chat_with_retries(
            messages,
            parser=lambda r: r.choices[0].message.content or "",
            llm_model=llm_model,
        )

    async def chat_structured_output(
        self,
        chat: list["TextChatMessage"],
        model: Type[T],
        llm_model: str | None = None,
    ) -> Result[T]:
        """Multi-turn chat → validated pydantic model."""
        messages = _to_openai_messages(chat)
        response_format: Type[T] | None = None
        if self.config.does_support_structured_output:
            response_format = model
        else:
            logger.warning(
                "called structured output on model that according to the configuration does not support"
            )

        return await self._chat_with_retries(
            messages,
            parser=lambda r: model.model_validate_json(
                r.choices[0].message.content or ""
            ),
            response_format=response_format,
            llm_model=llm_model,
        )

    async def batch_chat(
        self, batch_chat: list[list[TextChatMessage]], llm_model: str | None = None
    ) -> Result[list[dict[str, Any]]]:
        """Run multiple chats concurrently, return list of {'response': str}."""

        async def _single(seq: list["TextChatMessage"]) -> Result[dict[str, Any]]:
            res = await self.chat(
                seq, llm_model=llm_model if llm_model else self.config.model
            )
            if res.is_error():
                return Result.Err(res.get_error())
            return Result.Ok({"response": res.get_ok()})

        results = await asyncio.gather(*[_single(seq) for seq in batch_chat])
        for r in results:
            if r.is_error():
                return Result.Err(r.get_error())
        return Result.Ok([r.get_ok() for r in results])

    async def stream_chat(
        self, chat: list[TextChatMessage], llm_model: str | None = None
    ) -> Result[AsyncGenerator[str, None]]:
        """
        Multi-turn chat → async token stream (yields str chunks).

        Retry policy:
        - If the stream fails *before* any bytes are emitted, we back off and retry.
        - If it fails *after* emitting something, we stop and propagate the error
          (restarting would duplicate partial output).
        """

        messages: list[ChatCompletionMessageParam] = _to_openai_messages(chat)

        async def _generator() -> AsyncGenerator[str, None]:
            backoff = 1.0
            attempted = 0
            emitted_any = False

            while attempted < self.config.retries:
                attempted += 1
                stream = None
                try:
                    with self.tracer.start_as_current_span("openai-chat-stream"):
                        stream = await self.client.chat.completions.create(
                            model=llm_model if llm_model else self.config.model,
                            messages=messages,
                            temperature=self.config.temperature,
                            max_tokens=self.config.max_tokens,
                            stream=True,
                        )

                    async for chunk in stream:
                        # Each chunk is a ChatCompletionChunk; collect deltas.
                        for choice in chunk.choices:
                            delta = getattr(choice, "delta", None)
                            if delta and getattr(delta, "content", None):
                                emitted_any = True
                                yield delta.content

                    # Completed normally
                    return

                except (RateLimitError, APIError) as exc:
                    logger.warning(
                        "[openai] recoverable stream error on attempt %d/%d: %s",
                        attempted,
                        self.config.retries,
                        exc,
                    )
                    if emitted_any or attempted >= self.config.retries:
                        # Don't retry mid-stream; surface the error
                        raise
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue

                except Exception as exc:
                    logger.warning(
                        "[openai] transport stream error on attempt %d/%d: %s",
                        attempted,
                        self.config.retries,
                        exc,
                    )
                    if emitted_any or attempted >= self.config.retries:
                        raise
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue

                finally:
                    # Make a best-effort to close the stream
                    try:
                        if stream is not None:
                            await stream.aclose()  # type: ignore
                    except Exception:
                        pass

        try:
            gen = _generator()
            return Result.Ok(gen)
        except Exception as exc:
            return Result.Err(exc)


# Optional tiny helper to convert your domain messages to OpenAI params
def _to_openai_messages(
    chat: list[TextChatMessage],
) -> list[ChatCompletionMessageParam]:
    msgs: list[ChatCompletionMessageParam] = []
    for m in chat:
        msgs.append({"role": m.role, "content": m.content})  # type: ignore
    return msgs
