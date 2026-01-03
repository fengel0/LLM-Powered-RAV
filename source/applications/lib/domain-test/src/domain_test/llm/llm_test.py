import os
from pydantic import BaseModel
from domain.llm.model import TextChatMessage
import logging
from core.logger import init_logging
from domain.llm.interface import AsyncLLM
from domain_test import AsyncTestBase

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "")
MODEL = os.environ.get("MODEL", "")

logger = logging.getLogger(__name__)

# a tiny 25x17 PNG (base64) so we don't blow up the request
image = "iVBORw0KGgoAAAANSUhEUgAAABkAAAARCAYAAAAougcOAAAABHNCSVQICAgIfAhkiAAAABl0RVh0U29mdHdhcmUAZ25vbWUtc2NyZWVuc2hvdO8Dvz4AAAAqdEVYdENyZWF0aW9uIFRpbWUAU28gMTMgQXByIDIwMjUgMTc6NDk6MDEgQ0VTVLSoNRAAAAAiSURBVDiNY7x169J/BhoDJlpbMGrJqCWjloxaMmrJiLAEAAwrA6fNX7FfAAAAAElFTkSuQmCC"


class DummySchemaModel(BaseModel):
    field: str


class TestLLMClient(AsyncTestBase):
    client: AsyncLLM

    async def _ensure_model_available(self):
        probe = await self.client.run_against_model(
            system_prompt="You are a health check.",
            prompt="Return exactly: OK",
        )
        if probe.is_error():
            logger.error(probe.get_error())
        assert probe.is_ok()
        text = probe.get_ok().strip().upper()
        if "OK" not in text:
            # Model loads but returns nonsense; still continue with a warning.
            logger.warning("Health check returned unexpected content: %r", text)

    # ----------------- completion API -----------------

    async def test_run_against_model(self):
        await self._ensure_model_available()

        result = await self.client.run_against_model(
            system_prompt="You are a helpful assistant.",
            prompt="hi",
        )
        if result.is_error():
            logger.error(result.get_error())

        assert result.is_ok()
        assert len(result.get_ok()) > 0

    # ----------------- image + text (multimodal) -----------------

    async def test_run_image_against_multimodal_model(self):
        await self._ensure_model_available()

        result = await self.client.run_image_against_multimodal_model(
            system_prompt="You are a visual tag recognizer.",
            prompt="Describe the image in 3 words.",
            base64_image=image,
        )

        if result.is_error():
            logger.error(result.get_error())

        assert result.is_ok()
        assert len(result.get_ok()) > 0

    # ----------------- structured output (completion) -----------------

    async def test_get_structured_output(self):
        await self._ensure_model_available()

        result = await self.client.get_structured_output(
            system_prompt="Respond ONLY as valid JSON matching the schema.",
            prompt='{"field": "test"}',
            model=DummySchemaModel,
        )

        if result.is_error():
            logger.error(result.get_error())

        assert result.is_ok()
        obj = result.get_ok()
        assert obj
        assert obj.field == "test"

    # ----------------- chat API -----------------

    async def test_chat_basic(self):
        await self._ensure_model_available()

        messages = [
            TextChatMessage(role="system", content="You are concise."),
            TextChatMessage(role="user", content="Say hello in one word."),
        ]
        res = await self.client.chat(messages)
        if res.is_error():
            logger.error(res.get_error())

        assert res.is_ok()
        out = res.get_ok()
        assert isinstance(out, str)
        assert len(out.strip()) > 0

    async def test_stream_chat_basic(self):
        await self._ensure_model_available()

        messages = [
            TextChatMessage(role="system", content="You are concise."),
            TextChatMessage(role="user", content="Say hello in one word."),
        ]
        res = await self.client.stream_chat(messages)
        if res.is_error():
            logger.error(res.get_error())

        assert res.is_ok()
        out = res.get_ok()
        chunk_count = 0
        async for chunk in out:
            logger.info(chunk)
            chunk_count = chunk_count + 1
        assert chunk_count > 0

    # ----------------- chat structured output -----------------

    async def test_chat_structured_output(self):
        await self._ensure_model_available()

        class ChatSchema(BaseModel):
            field: str

        messages = [
            TextChatMessage(role="system", content="Respond as JSON with key 'field'."),
            TextChatMessage(
                role="user", content='Return {"field": "chat-ok"} exactly.'
            ),
        ]
        res = await self.client.chat_structured_output(messages, ChatSchema)
        if res.is_error():
            logger.error(res.get_error())

        assert res.is_ok()
        obj = res.get_ok()
        assert isinstance(obj, ChatSchema)
        assert obj.field == "chat-ok"

    # ----------------- batch chat -----------------

    async def test_batch_chat(self):
        await self._ensure_model_available()

        batch = [
            [
                TextChatMessage(role="system", content="Be terse."),
                TextChatMessage(role="user", content="Reply with A."),
            ],
            [
                TextChatMessage(role="system", content="Be terse."),
                TextChatMessage(role="user", content="Reply with B."),
            ],
            [
                TextChatMessage(role="system", content="Be terse."),
                TextChatMessage(role="user", content="Reply with C."),
            ],
        ]
        res = await self.client.batch_chat(batch)
        if res.is_error():
            logger.error(res.get_error())

        assert res.is_ok()
        payloads = res.get_ok()
        assert isinstance(payloads, list)
        assert len(payloads) == 3
        # Each item is a dict like {"response": "..."} per our implementation
        for item in payloads:
            assert "response" in item
            assert isinstance(item["response"], str)
            assert len(item["response"].strip()) > 0
