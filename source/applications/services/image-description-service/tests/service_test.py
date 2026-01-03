# tests/test_describe_image_usecase.py
from unittest.mock import AsyncMock, MagicMock

from core.result import Result
from core.model import NotFoundException
from core.singelton import SingletonMeta

from domain.storage.model import FileStorageObject
from domain.llm.interface import AsyncLLM
from domain.storage.interface import FileStorage

from image_description_service.usecase.image_description import (
    DescribeImageUsecase,
    DescribeImageUsecaseConfig,
)

from domain_test import AsyncTestBase


class TestDescribeImageUsecase(AsyncTestBase):
    __test__ = True

    def setup_method_sync(self, _name: str):
        self.mock_llm = AsyncMock(spec=AsyncLLM)
        self.mock_storage = MagicMock(spec=FileStorage)

        self.config = DescribeImageUsecaseConfig(
            system_prompt="You are an assistant", prompt="Describe the image"
        )

        self.usecase = DescribeImageUsecase.create(
            async_ollama_client=self.mock_llm,
            config=self.config,
            file_storage=self.mock_storage,
        )

    def teardown_method_sync(self, _name: str):
        SingletonMeta.clear_all()

    async def test_describe_image_success(self):
        mock_image = FileStorageObject(
            filename="test.jpg",
            bucket="images",
            filetype="image/jpeg",
            content=b"binarydata",
        )
        mock_context_file_1 = FileStorageObject(
            filename="note.txt",
            bucket="images",
            filetype="text/plain",
            content=b"first file",
        )
        mock_context_file_2 = FileStorageObject(
            filename="summary.txt",
            bucket="images",
            filetype="text/plain",
            content=b"second file",
        )

        self.mock_storage.fetch_file.side_effect = [
            Result.Ok(mock_image),
            Result.Ok(mock_context_file_1),
            Result.Ok(mock_context_file_2),
        ]
        self.mock_llm.run_image_against_multimodal_model.return_value = Result.Ok(
            "A cat playing with a ball."
        )
        self.mock_storage.upload_file.return_value = Result.Ok()

        result = await self.usecase.describe_image(
            "test.jpg", "images", ["note.txt", "summary.txt"]
        )

        assert result.is_ok()
        assert self.mock_storage.fetch_file.call_count == 3
        self.mock_llm.run_image_against_multimodal_model.assert_awaited_once()
        self.mock_storage.upload_file.assert_called_once()

    async def test_context_file_missing(self):
        mock_image = FileStorageObject(
            filename="test.jpg",
            bucket="images",
            filetype="image/jpeg",
            content=b"binarydata",
        )

        self.mock_storage.fetch_file.side_effect = [
            Result.Ok(mock_image),
            Result.Ok(None),  # Simulate missing context file
        ]

        result = await self.usecase.describe_image(
            "test.jpg", "images", ["missing.txt"]
        )

        assert result.is_error()
        assert isinstance(result.get_error(), NotFoundException)
        self.mock_llm.run_image_against_multimodal_model.assert_not_called()
        self.mock_storage.upload_file.assert_not_called()

    async def test_context_file_fetch_fails(self):
        mock_image = FileStorageObject(
            filename="test.jpg",
            bucket="images",
            filetype="image/jpeg",
            content=b"binarydata",
        )

        self.mock_storage.fetch_file.side_effect = [
            Result.Ok(mock_image),
            Result.Err(IOError("failed to fetch context")),
        ]

        result = await self.usecase.describe_image(
            "test.jpg", "images", ["corrupt.txt"]
        )

        assert result.is_error()
        assert isinstance(result.get_error(), IOError)
        self.mock_llm.run_image_against_multimodal_model.assert_not_called()
        self.mock_storage.upload_file.assert_not_called()
