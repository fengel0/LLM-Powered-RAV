import logging
import pytest
import pytest_asyncio

logger = logging.getLogger(__name__)


class AsyncTestBase:
    __test__ = False  # don't collect this base as a test class

    # ---------- class-level hooks (once per class) ----------
    @classmethod
    def setup_class_sync(cls):
        pass

    @classmethod
    async def setup_class_async(cls):
        pass

    @classmethod
    def teardown_class_sync(cls):
        pass

    @classmethod
    async def teardown_class_async(cls):
        pass

    # ---------- method-level hooks (per test) ----------
    # Now receive the function name being tested
    def setup_method_sync(self, test_name: str):
        pass

    async def setup_method_async(self, test_name: str):
        pass

    def teardown_method_sync(self, test_name: str):
        pass

    async def teardown_method_async(self, test_name: str):
        pass

    # ---------- fixtures that drive the hooks ----------
    @pytest.fixture(scope="class", autouse=True)
    def _class_hooks(self, request):
        cls = request.cls
        logger.info("sync setup test")
        cls.setup_class_sync()
        yield
        logger.info("sync shutdown test")
        cls.teardown_class_sync()

    @pytest_asyncio.fixture(scope="class", autouse=True)
    async def _class_hooks_async(self, request):
        cls = request.cls
        logger.info("async setup test")
        await cls.setup_class_async()
        yield
        logger.info("async shutdown test")
        await cls.teardown_class_async()

    @pytest.fixture(autouse=True)
    def _method_hooks(self, request):
        inst = request.instance
        # function name without parametrization suffixes if available
        test_name = getattr(request.node, "originalname", request.node.name)
        logger.info(f"sync setup method {test_name}")
        inst.setup_method_sync(test_name)
        yield
        logger.info(f"sync shutdown method {test_name}")
        inst.teardown_method_sync(test_name)

    @pytest_asyncio.fixture(autouse=True)
    async def _method_hooks_async(self, request):
        inst = request.instance
        test_name = getattr(request.node, "originalname", request.node.name)
        logger.info(f"async setup method {test_name}")
        await inst.setup_method_async(test_name)
        yield
        logger.info(f"async shutdown method {test_name}")
        await inst.teardown_method_async(test_name)

