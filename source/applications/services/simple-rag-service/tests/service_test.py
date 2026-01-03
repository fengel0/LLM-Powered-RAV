from core.logger import init_logging

from domain_test import AsyncTestBase

init_logging("debug")

"""
Just a place holder at the moment is the usecase to simple as that it could be used in a meaning full way
"""


class TestEmbeddFileUsecase(AsyncTestBase):
    __test__ = True

    def test_sample_test(self):
        assert True
