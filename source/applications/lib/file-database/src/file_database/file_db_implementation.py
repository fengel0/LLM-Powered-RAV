import logging
from typing import List
from uuid import UUID, uuid4

from opentelemetry import trace
from tortoise import transactions

from core.result import Result
from database.session import BaseDatabase
from domain.database.file.interface import FileDatabase
from domain.database.file.model import (
    File as DomainFile,
    FileMetadata as DomainFileMetadata,
    FilePage as DomainFilePage,
    PageFragement as DomainFragment,
    PageMetadata as DomainPageMetadata,
)
from file_database.model import (
    File as FileDB,
    FilePage as FilePageDB,
    PageFragement as FragmentDB,
)

logger = logging.getLogger(__name__)

__all__ = ["PostgresFileDatabase"]


# ---------------------------------------------------------------------------
# Internal lightweight DAL wrapper
# ---------------------------------------------------------------------------
class _PostgresDBFile(BaseDatabase[FileDB]):
    def __init__(self) -> None:
        super().__init__(FileDB)


class _PostgresDBPage(BaseDatabase[FilePageDB]):
    def __init__(self) -> None:
        super().__init__(FilePageDB)


class _PostgresDBFragment(BaseDatabase[FragmentDB]):
    def __init__(self) -> None:
        super().__init__(FragmentDB)


# ---------------------------------------------------------------------------
# Public adapter
# ---------------------------------------------------------------------------
class PostgresFileDatabase(FileDatabase):
    """PostgreSQL implementation of the :class:`FileDatabase` port.

    All public methods return :class:`core.result.Result` to propagate domain-level
    errors while keeping the async API surface identical across database back-ends.
    """

    _pg_db_file: _PostgresDBFile
    _pg_db_page: _PostgresDBPage
    _pg_db_page_fragement: _PostgresDBFragment
    _tracer: trace.Tracer

    def __init__(self) -> None:
        super().__init__()
        self._pg_db_file = _PostgresDBFile()
        self._pg_db_page = _PostgresDBPage()
        self._pg_db_page_fragement = _PostgresDBFragment()
        self._tracer = trace.get_tracer(__name__)

    # ---------------------------------------------------------------------
    # CRUD
    # ---------------------------------------------------------------------
    async def create(self, obj: DomainFile) -> Result[str]:
        """Persist a new *File* (including pages & fragments)."""
        try:
            db_obj = _domain_to_db(obj)
            async with transactions.in_transaction():  # type: ignore
                result = await self._pg_db_file.create(db_obj)
                if result.is_error():
                    raise result.get_error()
                pages: list[FilePageDB] = [
                    _domain_page_to_db(p, db_obj) for p in obj.pages
                ]
                for page in pages:
                    result = await self._pg_db_page.create(page)
                    if result.is_error():
                        raise result.get_error()
                for index, page in enumerate(obj.pages):
                    page_db: FilePageDB = pages[index]
                    fragments: list[FragmentDB] = [
                        _domain_fragment_to_db(fragement, page_db)
                        for fragement in page.fragements
                    ]
                    result = await self._pg_db_page_fragement.create_list(fragments)
                    if result.is_error():
                        raise result.get_error()
            return Result.Ok(str(db_obj.id))
        except Exception as exc:  # pragma: no cover – defensive
            logger.exception("create-file failed")
            return Result.Err(exc)

    async def update(self, obj: DomainFile) -> Result[None]:
        """Full upsert – deletes existing related entities before re-inserting."""
        try:
            # Purge & re-insert instead of patching nested relations – simpler & safe
            async with transactions.in_transaction():  # type: ignore
                purge = await self._pg_db_file.delete(obj.id)
                if purge.is_error():
                    return purge.propagate_exception()
                result = await self.create(obj)
                if result.is_error():
                    raise result.get_error()
                return Result.Ok()
        except Exception as exc:  # pragma: no cover
            logger.exception("update-file failed")
            return Result.Err(exc)

    async def delete(self, id: str) -> Result[None]:
        return await self._pg_db_file.delete(id)

    async def get(self, id: str) -> Result[DomainFile | None]:
        file = await FileDB.filter(id=id).prefetch_related("pages__fragments").first()
        if file is None:
            return Result.Ok(None)

        file_domain = _db_to_domain(file)
        for page in file.pages:
            domain_page = _db_page_to_domain(page)
            domain_page.fragements = [
                _db_fragement_to_domain(f) for f in page.fragments
            ]
            file_domain.pages.append(domain_page)

        return Result.Ok(file_domain)

    async def get_all(self) -> Result[List[DomainFile]]:
        res = await self._pg_db_file.get_all()
        if res.is_error():
            return res.propagate_exception()
        return Result.Ok([_db_to_domain(o) for o in res.get_ok()])

    # ---------------------------------------------------------------------
    # Specialised fetch/search helpers
    # ---------------------------------------------------------------------
    async def fetch_by_path(self, path: str) -> Result[DomainFile | None]:
        with self._tracer.start_as_current_span("fetch-by-path"):
            return await self._fetch_first({"filepath": path})

    async def search_by_path(self, path: str) -> Result[List[DomainFile]]:
        with self._tracer.start_as_current_span("search-by-path"):
            return await self._fetch_many({"filepath__icontains": path})

    async def fetch_by_name(self, name: str) -> Result[DomainFile | None]:
        with self._tracer.start_as_current_span("fetch-by-name"):
            return await self._fetch_first({"filename": name})

    async def search_by_name(self, name: str) -> Result[List[DomainFile]]:
        with self._tracer.start_as_current_span("search-by-name"):
            return await self._fetch_many({"filename__icontains": name})

    async def fetch_by_project(self, project_id: str) -> Result[List[DomainFile]]:
        with self._tracer.start_as_current_span("fetch-by-project"):
            return await self._fetch_many({"metadata_project_id": project_id})

    # ------------------------------------------------------------------
    # Versioned selections
    # ------------------------------------------------------------------
    async def fetch_files_blow_a_certain_version(
        self, version: int
    ) -> Result[List[DomainFile]]:  # noqa: D401,E501 – public API
        with self._tracer.start_as_current_span("fetch-files-below-version"):
            return await self._fetch_many({"metadata_version__lt": version})

    async def fetch_file_pages_blow_a_certain_version(
        self, version: int
    ) -> Result[List[DomainFilePage]]:  # noqa: D401,E501
        """Return *all* pages of *all* files whose *page* version is < *version*."""
        try:
            with self._tracer.start_as_current_span("fetch-pages-below-version"):
                pages = await FilePageDB.filter(
                    metadata__version__lt=version
                ).prefetch_related("fragments")
                domain_pages: list[DomainFilePage] = []
                for page in pages:
                    domain_page = _db_page_to_domain(page)
                    domain_page.fragements = [
                        _db_fragement_to_domain(f) for f in page.fragments
                    ]
                    domain_pages.append(domain_page)

                return Result.Ok(domain_pages)
        except Exception as exc:  # pragma: no cover
            logger.exception("fetch-file-pages-below-version failed")
            return Result.Err(exc)

    async def _fetch_first(self, query: dict[str, object]) -> Result[DomainFile | None]:
        """Return *exactly one* record (or ``None``) for *query* wrapped in Result."""
        file_result = await self._pg_db_file.run_query_first(
            query=query, relation=["pages__fragments"]
        )
        if file_result.is_error():
            return file_result.propagate_exception()
        file_option = file_result.get_ok()
        if file_option is None:
            return Result.Ok(None)
        file = file_option

        file_domain = _db_to_domain(file)
        for page in file.pages:
            domain_page = _db_page_to_domain(page)
            domain_page.fragements = [
                _db_fragement_to_domain(f) for f in page.fragments
            ]
            file_domain.pages.append(domain_page)

        return Result.Ok(file_domain)

    async def _fetch_many(self, query: dict[str, object]):
        files_result = await self._pg_db_file.run_query(
            query=query, relation=["pages__fragments"]
        )
        if files_result.is_error():
            return files_result.propagate_exception()
        files = files_result.get_ok()
        domain_files: list[DomainFile] = []
        for file in files:
            file_domain = _db_to_domain(file)
            for page in file.pages:
                domain_page = _db_page_to_domain(page)
                domain_page.fragements = [
                    _db_fragement_to_domain(f) for f in page.fragments
                ]
                file_domain.pages.append(domain_page)
            domain_files.append(file_domain)
        return Result.Ok(domain_files)


def _domain_to_db(domain: DomainFile) -> FileDB:
    try:
        file_id = UUID(domain.id)
    except (ValueError, TypeError):
        file_id = uuid4()

    db_file = FileDB(
        id=file_id,  # type: ignore[arg-type] – Tortoise expects UUID | str
        filepath=domain.filepath,
        filename=domain.filename,
        bucket=domain.bucket,
        metadata_project_id=domain.metadata.project_id,
        metadata_project_year=domain.metadata.project_year,
        metadata_file_creation=domain.metadata.file_creation,
        metadata_file_updated=domain.metadata.file_updated,
        metadata_version=domain.metadata.version,
        metatdata_other=domain.metadata.other_metadata,
    )

    return db_file


def _domain_fragment_to_db(f: DomainFragment, parent_page: FilePageDB) -> FragmentDB:
    return FragmentDB(
        page=parent_page,
        fragement_type=f.fragement_type.value,
        storage_filename=f.storage_filename,
        fragement_number=f.fragement_number,
    )


def _domain_page_to_db(page: DomainFilePage, parent_file: FileDB) -> FilePageDB:
    db_page = FilePageDB(
        file=parent_file,
        bucket=page.bucket,
        page_number=page.page_number,
        metadata__project_id=page.metadata.project_id,
        metadata__project_year=page.metadata.project_year,
        metadata__file_creation=page.metadata.file_creation,
        metadata__file_updated=page.metadata.file_updated,
        metadata__version=page.metadata.version,
    )
    return db_page


def _db_to_domain(db_obj: FileDB) -> DomainFile:
    return DomainFile(
        id=str(db_obj.id),
        filepath=db_obj.filepath,
        filename=db_obj.filename,
        bucket=db_obj.bucket,
        metadata=DomainFileMetadata(
            project_id=db_obj.metadata_project_id,
            project_year=db_obj.metadata_project_year,
            version=db_obj.metadata_version,
            file_creation=db_obj.metadata_file_creation,
            file_updated=db_obj.metadata_file_updated,
            other_metadata=db_obj.metatdata_other,
        ),
        pages=[
            # _db_page_to_domain(p) for p in db_obj.pages
        ],
    )


def _db_page_to_domain(db_page: FilePageDB) -> DomainFilePage:
    return DomainFilePage(
        bucket=db_page.bucket,
        page_number=db_page.page_number,
        metadata=DomainPageMetadata(
            project_id=db_page.metadata__project_id,
            project_year=db_page.metadata__project_year,
            version=db_page.metadata__version,
            file_creation=db_page.metadata__file_creation,
            file_updated=db_page.metadata__file_updated,
        ),
        fragements=[],
    )


def _db_fragement_to_domain(db_fragement: FragmentDB) -> DomainFragment:
    return DomainFragment(
        fragement_type=db_fragement.fragement_type,  # type: ignore[arg-type]
        storage_filename=db_fragement.storage_filename,
        fragement_number=db_fragement.fragement_number,
    )
