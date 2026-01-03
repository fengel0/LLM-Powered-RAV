from pathlib import Path
from core.result import Result
from core.string_handler import str_to_bytes
import logging
import tempfile
from domain.file_converter.model import (
    FragementLite,
    FragementTypes,
    ImageFragment,
    Page,
    PageLite,
    TableFragement,
    TextFragement,
)
from core.model import NotFoundException
from core.singelton import BaseSingleton
from domain.storage.interface import FileStorage
from domain.storage import get_content_type
from domain.storage.model import FileStorageObject
from domain.file_converter.interface import FileConverter
from pydantic import RootModel
from opentelemetry import trace


class UploadedFiles(RootModel[list[PageLite]]): ...


logger = logging.getLogger(__name__)


class ConvertFileToMarkdown(BaseSingleton):
    file_storage: FileStorage
    file_converter: list[FileConverter]
    tracer: trace.Tracer

    def _init_once(
        self,
        file_storage: FileStorage,
        file_converter: list[FileConverter],
    ):
        logger.info("created ConvertFileToMarkdown Usecase")
        self.file_storage = file_storage
        self.file_converter = file_converter
        self.tracer = trace.get_tracer("ConvertFileToMarkdown")

    def convert_file(
        self, source_bucket: str, destination_bucket: str, filename: str
    ) -> Result[UploadedFiles]:
        load_file_result = self.file_storage.fetch_file(
            filename=filename, bucket=source_bucket
        )
        if load_file_result.is_error():
            return load_file_result.propagate_exception()

        load_file = load_file_result.get_ok()
        if load_file is None:
            return Result.Err(
                NotFoundException(
                    f"File {filename} not found in Bucket {source_bucket}"
                )
            )
        assert load_file

        suffixe = load_file.get_file_suffix()
        pages: list[Page] | None = None
        p = Path(load_file.filename)
        with self.tracer.start_as_current_span("write-file-to-tmp-file"):
            with tempfile.NamedTemporaryFile(
                prefix=f"{p.stem}_",
                suffix=p.suffix,
                delete=True,
            ) as tmp:
                tmp.write(load_file.content)
                tmp.flush()
                for converter in self.file_converter:
                    if converter.does_convert_filetype(suffixe):
                        convert_result = converter.convert_file(tmp.name)
                        if convert_result.is_error():
                            return convert_result.propagate_exception()
                        pages = convert_result.get_ok()
                        break

        if pages is None:
            return Result.Err(
                NotFoundException(
                    f"Did not find any file converter that could convert {suffixe}"
                )
            )

        base_filename = load_file.filename.replace(f".{suffixe}", "")
        uploaded_files: list[PageLite] = []

        with self.tracer.start_as_current_span("uploade-files"):
            for index_page, page in enumerate(pages):
                current_page = PageLite(page_number=index_page, fragments=[])
                for index_fragement, fragement in enumerate(page.document_fragements):
                    filename = f"{base_filename}_page_{index_page}_fragement_{index_fragement}.md"

                    data: bytes | None = None
                    fragement_type: FragementTypes | None = None
                    match fragement:
                        case TableFragement():
                            assert isinstance(fragement, TableFragement)
                            data = str_to_bytes(fragement.full_tabel)
                            fragement_type = FragementTypes.TABEL
                            logger.debug("TabelFragement")
                        case TextFragement():
                            assert isinstance(fragement, TextFragement)
                            fragement_type = FragementTypes.TEXT
                            data = str_to_bytes(fragement.text)
                            logger.debug("TextFragement")
                        case ImageFragment():
                            assert isinstance(fragement, ImageFragment)
                            fragement_type = FragementTypes.IMAGE
                            filename = f"{base_filename}_page_{index_page}_fragement_{index_fragement}_{fragement.filename}"
                            data = fragement.data
                            logger.debug("ImageFragment")
                        case _:
                            return Result.Err(
                                ValueError("Failed to find match for Fragement")
                            )
                    assert fragement_type
                    assert data
                    current_page.fragments.append(
                        FragementLite(
                            fragement_type=fragement_type,
                            fragement_number=index_fragement,
                            filename=filename,
                        )
                    )

                    filestorage = self._build_file_storage_object(
                        filename=filename,
                        data=data,
                        destination_bucket=destination_bucket,
                    )
                    result = self.file_storage.upload_file(file=filestorage)
                    if result.is_error():
                        return result.propagate_exception()

                uploaded_files.append(current_page)

        return Result.Ok(UploadedFiles(root=uploaded_files))

    def _build_file_storage_object(
        self, filename: str, data: bytes, destination_bucket: str
    ) -> FileStorageObject:
        return FileStorageObject(
            filetype=get_content_type(filetype=filename),
            content=data,
            bucket=destination_bucket,
            filename=filename,
        )
