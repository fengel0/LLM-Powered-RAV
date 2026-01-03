from core.logger import init_logging
from openai_client.async_openai import ConfigOpenAI, OpenAIAsyncLLM
from domain_test.llm.llm_test import TestLLMClient
from domain_test.enviroment import llm


init_logging("info")


class TestOpenAICompatibleClientIntegration(TestLLMClient):
    __test__ = True

    def setup_method_sync(self, test_name: str):
        config = ConfigOpenAI(
            model=llm.OPENAI_MODEL,
            base_url=llm.OPENAI_HOST,
            max_tokens=2048,
            api_key=llm.OPENAI_HOST_KEY,
        )
        self.client = OpenAIAsyncLLM(
            config,
        )
