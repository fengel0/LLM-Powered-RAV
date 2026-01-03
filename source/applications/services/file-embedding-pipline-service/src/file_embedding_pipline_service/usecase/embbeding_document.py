from core.result import Result
from core.string_handler import to_str
from domain.database.config.model import RagEmbeddingConfig
import logging
from core.singelton import BaseSingleton
from core.model import NotFoundException
from domain.database import BaseModel
from domain.file_converter.model import (
    FragementLite,
    FragementTypes,
    Page,
    PageLite,
    TableFragement,
    TextFragement,
)
from domain.database.file.interface import FileDatabase
from domain.database.file.model import FragementTypes as FragementTypesDB
from domain.storage.interface import FileStorage
from domain.rag.indexer.interface import AsyncDocumentIndexer
from domain.rag.indexer.model import Document
from opentelemetry import trace


logger = logging.getLogger(__name__)


class EmbedDoc(BaseModel):
    content: str | list[str]
    metadata: dict[str, str]


class EmbeddFilePiplineUsecaseConfig(BaseModel):
    consider_images: bool = True


class EmbeddFilePiplineUsecase(BaseSingleton):
    """
    Usecase to converte files to markdown
    usecase for the api
    """
    _file_storage: FileStorage
    _vectore_store: AsyncDocumentIndexer
    _file_database: FileDatabase
    _config: EmbeddFilePiplineUsecaseConfig
    _embed_config: RagEmbeddingConfig
    tracer: trace.Tracer

    def _init_once(
        self,
        file_storage: FileStorage,
        vectore_store: AsyncDocumentIndexer,
        file_database: FileDatabase,
        config: EmbeddFilePiplineUsecaseConfig,
        embed_config: RagEmbeddingConfig,
    ):
        logger.info("created EmbeddFileUsecase Usecase")
        self._file_storage = file_storage
        self._vectore_store = vectore_store
        self._file_database = file_database
        self._config = config
        self._embed_config = embed_config
        self.tracer = trace.get_tracer("EmbeddFileUsecase")

    async def embedd_file(
        self,
        file_id: str,
    ) -> Result[None]:
        pages: list[PageLite] = []
        pages_document: list[Page] = []

        with self.tracer.start_as_current_span("fetch-fragements-from-database"):
            result = await self._file_database.get(id=file_id)
            if result.is_error():
                return result.propagate_exception()
            file = result.get_ok()
            if file is None:
                return Result.Err(NotFoundException(f"File with id:{id} not found"))
            for index_page, page in enumerate(file.pages):
                fragements: list[FragementLite] = []
                for index_fragement, fragement in enumerate(page.fragements):
                    if fragement.fragement_type == FragementTypesDB.IMAGE:
                        if self._config.consider_images:
                            fragements.append(
                                FragementLite(
                                    filename=fragement.get_image_description_filename(),
                                    fragement_number=index_fragement,
                                    fragement_type=FragementTypes.TEXT,
                                )
                            )
                    if fragement.fragement_type == FragementTypesDB.TABEL:
                        fragements.append(
                            FragementLite(
                                filename=fragement.storage_filename,
                                fragement_number=index_fragement,
                                fragement_type=FragementTypes.TABEL,
                            )
                        )
                    if fragement.fragement_type == FragementTypesDB.TEXT:
                        fragements.append(
                            FragementLite(
                                filename=fragement.storage_filename,
                                fragement_number=index_fragement,
                                fragement_type=FragementTypes.TEXT,
                            )
                        )
                pages.append(PageLite(fragments=fragements, page_number=index_page))

        tmp = file.metadata.model_dump(exclude={"other_metadata"})
        tmp["file_creation"] = str(tmp["file_creation"])
        tmp["file_updated"] = str(tmp["file_updated"])

        metadata: dict[str, str | int | float] = {
            **tmp,
            **file.metadata.other_metadata,
        }
        collection: str = f"{file.metadata.project_id}-{self._embed_config.id}"

        with self.tracer.start_as_current_span("fetch-fragements-from-storage"):
            for page in pages:
                page_document = Page(document_fragements=[])
                for fragement in page.fragments:
                    with self.tracer.start_as_current_span(
                        f"fetch-{fragement.filename}"
                    ):
                        if fragement.fragement_type == FragementTypes.IMAGE:
                            continue
                        fetched_page_result = self._file_storage.fetch_file(
                            filename=fragement.filename, bucket=file.metadata.project_id
                        )
                        if fetched_page_result.is_error():
                            return fetched_page_result.propagate_exception()
                        fetched_page = fetched_page_result.get_ok()
                        if fetched_page is None:
                            return Result.Err(
                                NotFoundException(
                                    f"Page with the name {page} not found in {file.metadata.project_id}"
                                )
                            )
                        if fragement.fragement_type == FragementTypes.TABEL:
                            page_document.document_fragements.append(
                                TableFragement(full_tabel=to_str(fetched_page.content))
                            )
                        if fragement.fragement_type == FragementTypes.TEXT:
                            page_document.document_fragements.append(
                                TextFragement(text=to_str(fetched_page.content))
                            )
                logger.debug(page_document)
                pages_document.append(page_document)

        with self.tracer.start_as_current_span("insert-document in indexer store"):
            return await self._vectore_store.create_document(
                doc=Document(id="", content=pages_document, metadata=metadata),
                collection=collection,
            )
