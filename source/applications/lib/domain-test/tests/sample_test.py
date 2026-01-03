import pytest
import asyncio
from core.logger import init_logging
from domain_test import AsyncTestBase

init_logging("debug")


class TestSomething(AsyncTestBase):
    @classmethod
    def setup_class_sync(cls):
        print("[SYNC] class setup")
        cls.shared = "sync-shared"

    @classmethod
    async def setup_class_async(cls):
        print("[ASYNC] class setup")
        cls.async_shared = await asyncio.sleep(0.01, result="async-shared")

    def setup_method_sync(self):
        print("[SYNC] method setup")

    async def setup_method_async(self):
        print("[ASYNC] method setup")
        self.temp = await asyncio.sleep(0.01, result=123)

    async def test_example(self):
        print("running test_example")
        assert self.shared == "sync-shared"
        assert self.async_shared == "async-shared"
        assert self.temp == 123

    def test_simple(self):
        assert self.shared == "sync-shared"
