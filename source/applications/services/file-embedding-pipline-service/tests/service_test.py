# tests/test_embedd_file_pipline_usecase.py
from unittest.mock import AsyncMock, Mock
from datetime import datetime
import logging

from core.singelton import SingletonMeta
from core.result import Result
from core.model import NotFoundException
from domain.database.config.model import RagEmbeddingConfig

from domain.database.file.model import (
    File,
    FileMetadata,
    FilePage,
    PageFragement,
    PageMetadata,
    FragementTypes as FragementTypesDB,
)
from domain.rag.indexer.model import Document
from domain.file_converter.model import Page, TableFragement, TextFragement
from domain.storage.interface import FileStorage
from domain.storage.model import FileStorageObject
from domain.rag.indexer.interface import AsyncDocumentIndexer
from domain.database.file.interface import FileDatabase

from file_embedding_pipline_service.usecase.embbeding_document import (
    EmbeddFilePiplineUsecase,
    EmbeddFilePiplineUsecaseConfig,
)

from domain_test import AsyncTestBase

logger = logging.getLogger(__name__)


class TestEmbeddFilePiplineUsecase(AsyncTestBase):
    __test__ = True

    def teardown_method_sync(self, test_name: str):
        SingletonMeta.clear_all()

    # ------------------------------------------------------------------ setup
    def setup_method_sync(self, test_name: str):
        # Storage is sync in your use case, so a plain Mock is correct
        self.mock_storage = Mock(spec=FileStorage)

        # Vector store: provide an object with an async create_document
        self.mock_vector = Mock(spec=AsyncDocumentIndexer)
        self.mock_vector.create_document = AsyncMock(return_value=Result.Ok(None))

        # Database: async API
        self.mock_db = AsyncMock(spec=FileDatabase)

        # Reset singleton and create fresh usecase
        self.usecase = EmbeddFilePiplineUsecase.create(
            file_storage=self.mock_storage,
            vectore_store=self.mock_vector,
            file_database=self.mock_db,
            config=EmbeddFilePiplineUsecaseConfig(),
            embed_config=RagEmbeddingConfig(
                id="", chunk_size=0, chunk_overlap=0, addition_information={}, models={}
            ),
        )

        self.now = datetime.now()
        self.metadata = FileMetadata(
            project_id="proj123",
            project_year=2024,
            version=1,
            file_creation=self.now,
            file_updated=self.now,
            other_metadata={},
        )

    # ------------------------------------------------------------- file missing
    async def test_file_not_found(self):
        self.mock_db.get.return_value = Result.Ok(None)

        result = await self.usecase.embedd_file("missing-id")

        assert result.is_error()
        assert isinstance(result.get_error(), NotFoundException)
        self.mock_vector.create_document.assert_not_called()

    # ------------------------------------------------------- storage fetch err
    async def test_storage_fetch_error(self):
        file = File(
            id="123",
            filepath="/fake/file",
            filename="myfile.pdf",
            bucket="bucket123",
            metadata=self.metadata,
            pages=[
                FilePage(
                    bucket="bucket123",
                    page_number=0,
                    metadata=PageMetadata(**self.metadata.model_dump()),
                    fragements=[
                        PageFragement(
                            fragement_type=FragementTypesDB.TEXT,
                            storage_filename="text_frag",
                            fragement_number=0,
                        )
                    ],
                )
            ],
        )

        self.mock_db.get.return_value = Result.Ok(file)
        self.mock_storage.fetch_file.return_value = Result.Err(
            NotFoundException("Storage error")
        )

        result = await self.usecase.embedd_file("123")

        assert result.is_error()
        assert isinstance(result.get_error(), NotFoundException)
        self.mock_vector.create_document.assert_not_called()

    # ------------------------------------------------------------- happy path
    async def test_successful_embedding(self):
        file = File(
            id="123",
            filepath="/fake/file",
            filename="myfile.pdf",
            bucket="bucket123",
            metadata=self.metadata,
            pages=[
                FilePage(
                    bucket="bucket123",
                    page_number=0,
                    metadata=PageMetadata(**self.metadata.model_dump()),
                    fragements=[
                        PageFragement(
                            fragement_type=FragementTypesDB.TEXT,
                            storage_filename="text_frag",
                            fragement_number=0,
                        ),
                        PageFragement(
                            fragement_type=FragementTypesDB.TABEL,
                            storage_filename="table_frag",
                            fragement_number=1,
                        ),
                        PageFragement(
                            fragement_type=FragementTypesDB.IMAGE,
                            storage_filename="img_frag",
                            fragement_number=2,
                        ),
                    ],
                )
            ],
        )

        self.mock_db.get.return_value = Result.Ok(file)

        def fetch_file_side_effect(filename: str, bucket: str):
            if filename == "text_frag":
                return Result.Ok(
                    FileStorageObject(
                        filetype="text/plain",
                        content=b"Some **text**",
                        bucket=bucket,
                        filename=filename,
                    )
                )
            elif filename == "table_frag":
                return Result.Ok(
                    FileStorageObject(
                        filetype="text/markdown",
                        content=b"| Header |\n|--------|\n| Row |",
                        bucket=bucket,
                        filename=filename,
                    )
                )
            elif filename == "img_frag.md":
                # if your pipeline appends '.md' for images before fetching,
                # this matches that behavior; otherwise change to "img_frag".
                return Result.Ok(
                    FileStorageObject(
                        filetype="image/png",
                        content=b"\x89PNG\r\n\x1a\n...",
                        bucket=bucket,
                        filename=filename,
                    )
                )
            return Result.Err(NotFoundException(f"Unknown file: {filename}"))

        self.mock_storage.fetch_file.side_effect = fetch_file_side_effect

        # Ensure the async call returns a real Result, not a Mock
        self.mock_vector.create_document.return_value = Result.Ok(None)

        result = await self.usecase.embedd_file("123")
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()

        # Verify the async dependency was awaited
        self.mock_vector.create_document.assert_called_once()
        assert self.mock_vector.create_document.await_count == 1

        # Inspect the Document passed to the vector store
        doc = self.mock_vector.create_document.call_args.kwargs["doc"]
        assert isinstance(doc, Document)
        assert doc.metadata["project_id"] == "proj123"
        assert len(doc.content) == 1

        page = doc.content[0]
        assert isinstance(page, Page)
        assert len(page.document_fragements) == 3
        assert isinstance(page.document_fragements[0], TextFragement)
        assert isinstance(page.document_fragements[1], TableFragement)
        # Third is image; depending on your use case it may be skipped or included.
