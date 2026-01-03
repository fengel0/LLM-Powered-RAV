# domain_test/vector/vector_store.py
import logging
import uuid
from domain_test import AsyncTestBase
from domain.rag.indexer.model import Document
from domain.rag.indexer.interface import AsyncDocumentIndexer

logger = logging.getLogger(__name__)


class TestDBVectorStore(AsyncTestBase):
    """
    Storage-agnostic tests for a vector store.
    Subclasses must assign `self.vector_store` in setup_method_async.
    """

    vector_store: AsyncDocumentIndexer

    # ------------------------------------------------------------------ tests
    async def test_multi_lin(self):
        assert self.vector_store, "Vector store has not been setup"

        # insert 3 small docs across languages / phrasing
        result = await self.vector_store.create_document(
            Document(
                id=str(uuid.uuid4()),
                content="Jörg Sahm teaches at fachhochschule",
                metadata={},
            )
        )
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()

        result = await self.vector_store.create_document(
            Document(
                id=str(uuid.uuid4()),
                content="Jörg Sahm Unterrichtet an der Fachhochschule",
                metadata={},
            )
        )
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()

        result = await self.vector_store.create_document(
            Document(
                id=str(uuid.uuid4()),
                content="Jörg Sahm Dozent an der Fachhochschule",
                metadata={},
            )
        )
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()

        # queries
        result = await self.vector_store.find_similar_nodes("Dozent")
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()
        for node in result.get_ok():
            logger.info(
                f"[Dozent] {getattr(node, 'content', '')} {getattr(node, 'similarity', None)}"
            )

        result = await self.vector_store.find_similar_nodes("Unterrichtet")
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()
        for node in result.get_ok():
            logger.info(
                f"[Unterrichtet] {getattr(node, 'content', '')} {getattr(node, 'similarity', None)}"
            )

        result = await self.vector_store.find_similar_nodes("teaches")
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()
        for node in result.get_ok():
            logger.info(
                f"[teaches] {getattr(node, 'content', '')} {getattr(node, 'similarity', None)}"
            )

    async def test_add_document(self):
        assert self.vector_store, "Vector store has not been setup"

        result = await self.vector_store.create_document(
            Document(id=str(uuid.uuid4()), content="Kubernetes ist cool", metadata={})
        )
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()

    async def test_create_find_update_delete_document(self):
        assert self.vector_store, "Vector store must be initialized."

        doc_id = str(uuid.uuid4())
        metadata: dict[str, str | int | float] = {
            "file_id": doc_id,
            "tag": "test-tag",
            "count": 4,
        }
        metadata_search: dict[str, list[str] | list[int] | list[float]] = {
            "file_id": [doc_id],
            "tag": ["test-tag"],
            "count": [4],
        }
        original_content = "Dies ist ein Testinhalt für Metadatenfilterung."

        # Step 1: Create
        create_result = await self.vector_store.create_document(
            Document(id=doc_id, content=original_content, metadata=metadata)
        )
        if create_result.is_error():
            logger.error(create_result.get_error())
        assert create_result.is_ok()

        # Step 2: Find with metadata filter
        find_result = await self.vector_store.find_similar_nodes(
            query="Testinhalt", metadata=metadata_search
        )
        if find_result.is_error():
            logger.error(find_result.get_error())
        assert find_result.is_ok()
        assert len(find_result.get_ok()) == 1

        # Insert same id again (should upsert/ignore duplicates depending on impl, but succeed)
        create_result = await self.vector_store.create_document(
            Document(id=doc_id, content=original_content, metadata=metadata)
        )
        if create_result.is_error():
            logger.error(create_result.get_error())
        assert create_result.is_ok()

        # should still be one (idempotency)
        find_result = await self.vector_store.find_similar_nodes(
            query="Testinhalt", metadata=metadata_search
        )
        if find_result.is_error():
            logger.error(find_result.get_error())
        assert find_result.is_ok()
        assert len(find_result.get_ok()) == 1

        # Step 3: Update
        updated_content = "Dies ist ein aktualisierter Inhalt."
        update_result = await self.vector_store.update_document(
            Document(id=doc_id, content=updated_content, metadata=metadata)
        )
        if update_result.is_error():
            logger.error(update_result.get_error())
        assert update_result.is_ok()

        # Step 4: Validate updated content
        find_updated_result = await self.vector_store.find_similar_nodes(
            query="aktualisierter", metadata=metadata_search
        )
        if find_updated_result.is_error():
            logger.error(find_updated_result.get_error())
        assert find_updated_result.is_ok()
        assert len(find_updated_result.get_ok()) >= 1

        # Step 5: Delete
        delete_result = await self.vector_store.delete_document(doc_id=doc_id)
        if delete_result.is_error():
            logger.error(delete_result.get_error())
        assert delete_result.is_ok()

        # Step 6: Confirm deletion – expect an error (or empty) depending on impl.
        # Original test asserted error; keep consistent:
        find_after_delete = await self.vector_store.find_similar_nodes(
            query="aktualisierter", metadata=metadata_search
        )
        assert find_after_delete.is_error()
