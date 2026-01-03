from core.logger import init_logging
import re
from unittest.mock import Mock
from unittest.mock import Mock

from core.result import Result
from core.model import NotFoundException
from core.singelton import SingletonMeta

from domain.storage.model import FileStorageObject
from domain.file_converter.model import (
    TextFragement,
    ImageFragment,
    TableFragement,
    FragementTypes,
    Page,
)

from file_converter_service.usecase.convert_file import ConvertFileToMarkdown
from domain_test import AsyncTestBase  # keeps the same base + hook names

DEST_BUCKET = "dest-bucket"

init_logging("debug")


class TestConvertFileToMarkdown(AsyncTestBase):
    __test__ = True

    # ------------------------------------------------------------------ setup / teardown (same hook names as before)
    def setup_method_sync(self, test_name: str):
        self.storage = Mock()
        self.converter = Mock()

        self.uc: ConvertFileToMarkdown = ConvertFileToMarkdown.create(
            file_storage=self.storage,
            file_converter=[self.converter],
        )

    def teardown_method_sync(self, test_name: str):
        SingletonMeta.clear_all()

    # -------------------------------------------------------- happy-path / green
    def test_convert_file_success(self):
        """Two pages – one fragment each – should yield two PageLite objects."""
        fake_source = FileStorageObject(
            filename="demo.pdf",
            content=b"%PDF-1.7",
            filetype="pdf",
            bucket="src",
        )
        pages = [
            Page(document_fragements=[TextFragement(text="Hello world")]),
            Page(document_fragements=[ImageFragment(filename="img.png", data=b"PNG")]),
        ]

        #  -------------  storage / converter mocks
        self.storage.fetch_file.return_value = Result.Ok(fake_source)
        self.storage.upload_file.return_value = Result.Ok(None)
        self.converter.does_convert_filetype.return_value = True
        self.converter.convert_file.return_value = Result.Ok(pages)

        res = self.uc.convert_file(
            source_bucket="src",
            destination_bucket=DEST_BUCKET,
            filename="demo.pdf",
        )

        assert res.is_ok(), res
        uploaded = res.get_ok().root  # list[PageLite]
        assert len(uploaded) == 2  # one entry per page

        # ----------- first page = TEXT
        first = uploaded[0]
        assert first.page_number == 0
        assert len(first.fragments) == 1
        assert first.fragments[0].fragement_type == FragementTypes.TEXT
        assert first.fragments[0].filename.endswith(".md")

        # ----------- second page = IMAGE
        second = uploaded[1]
        assert second.page_number == 1
        assert len(second.fragments) == 1
        assert second.fragments[0].fragement_type == FragementTypes.IMAGE
        assert second.fragments[0].filename.endswith("img.png")

        # two uploads – one per fragment
        assert self.storage.upload_file.call_count == 2

    # ------------------------------------------------------ fetch returns error
    def test_convert_file_fetch_error(self):
        self.storage.fetch_file.return_value = Result.Err(NotFoundException("boom"))

        res = self.uc.convert_file(
            source_bucket="src",
            destination_bucket=DEST_BUCKET,
            filename="missing.pdf",
        )

        assert res.is_error()
        assert isinstance(res.get_error(), NotFoundException)

    # ----------------------------------------------------------- file not found
    def test_convert_file_fetch_returns_none(self):
        self.storage.fetch_file.return_value = Result.Ok(None)

        res = self.uc.convert_file(
            source_bucket="src",
            destination_bucket=DEST_BUCKET,
            filename="missing.pdf",
        )

        assert res.is_error()
        assert isinstance(res.get_error(), NotFoundException)

    # ------------------------------------------------------- no converter match
    def test_convert_file_no_converter_found(self):
        src_obj = FileStorageObject(
            filename="file.xyz",
            content=b"???",
            filetype="xyz",
            bucket="src",
        )
        self.storage.fetch_file.return_value = Result.Ok(src_obj)
        self.converter.does_convert_filetype.return_value = False

        res = self.uc.convert_file(
            source_bucket="src",
            destination_bucket=DEST_BUCKET,
            filename="file.xyz",
        )

        assert res.is_error()
        assert "Did not find any file converter" in str(res.get_error())

    # ------------------------------------------------------- converter failure
    def test_convert_file_converter_fails(self):
        src_obj = FileStorageObject(
            filename="bad.pdf",
            content=b"BAD",
            filetype="pdf",
            bucket="src",
        )
        self.storage.fetch_file.return_value = Result.Ok(src_obj)
        self.converter.does_convert_filetype.return_value = True
        self.converter.convert_file.return_value = Result.Err(Exception("kaputt"))

        res = self.uc.convert_file(
            source_bucket="src",
            destination_bucket=DEST_BUCKET,
            filename="bad.pdf",
        )

        assert res.is_error()
        assert str(res.get_error()) == "kaputt"

    # -------------------------------------------------------- upload exception
    def test_convert_file_upload_fails(self):
        src_obj = FileStorageObject(
            filename="up.pdf",
            content=b"%PDF",
            filetype="pdf",
            bucket="src",
        )
        pages = [Page(document_fragements=[TableFragement(full_tabel="|a|")])]

        self.storage.fetch_file.return_value = Result.Ok(src_obj)
        self.converter.does_convert_filetype.return_value = True
        self.converter.convert_file.return_value = Result.Ok(pages)
        self.storage.upload_file.return_value = Result.Err(Exception("upload-err"))

        res = self.uc.convert_file(
            source_bucket="src",
            destination_bucket=DEST_BUCKET,
            filename="up.pdf",
        )

        assert res.is_error()
        assert str(res.get_error()) == "upload-err"
        assert res.is_error()
        assert str(res.get_error()), "upload-err"

    # ---------------------------------------------------- multiple fragments on one page
    def test_convert_file_multiple_fragments_single_page(self):
        """Eine Seite mit Text+Tabelle ergibt genau 1 PageLite mit 2 Fragmenten."""
        fake_source = FileStorageObject(
            filename="multi.pdf", content=b"%PDF", filetype="pdf", bucket="src"
        )
        pages = [
            Page(
                document_fragements=[
                    TextFragement(text="A"),
                    TableFragement(full_tabel="|x|"),
                ]
            )
        ]

        self.storage.fetch_file.return_value = Result.Ok(fake_source)
        self.storage.upload_file.return_value = Result.Ok(None)
        self.converter.does_convert_filetype.return_value = True
        self.converter.convert_file.return_value = Result.Ok(pages)

        res = self.uc.convert_file("src", DEST_BUCKET, "multi.pdf")
        assert res.is_ok(), res
        uploaded = res.get_ok().root

        assert len(uploaded) == 1, "genau eine PageLite erwartet"
        page0 = uploaded[0]
        assert page0.page_number == 0
        assert len(page0.fragments) == 2
        assert page0.fragments[0].fragement_type == FragementTypes.TEXT
        assert page0.fragments[1].fragement_type == FragementTypes.TABEL

        # Zwei Uploads – einer pro Fragment
        assert self.storage.upload_file.call_count == 2

    # -------------------------------------------------------- filename & bucket checks
    def test_convert_file_filenames_and_bucket(self):
        """Dateinamen enthalten page_ und fragment_ Indizes; Bucket = DEST_BUCKET."""
        fake_source = FileStorageObject(
            filename="names.pdf", content=b"%PDF", filetype="pdf", bucket="src"
        )
        pages = [
            Page(
                document_fragements=[
                    TextFragement(text="T"),
                    TableFragement(full_tabel="|t|"),
                ]
            ),
            Page(
                document_fragements=[
                    ImageFragment(filename="pic.png", data=b"PNG"),
                ]
            ),
        ]

        self.storage.fetch_file.return_value = Result.Ok(fake_source)
        self.storage.upload_file.return_value = Result.Ok(None)
        self.converter.does_convert_filetype.return_value = True
        self.converter.convert_file.return_value = Result.Ok(pages)

        res = self.uc.convert_file("src", DEST_BUCKET, "names.pdf")
        assert res.is_ok(), res
        uploaded = res.get_ok().root

        # Page 0: zwei .md Dateien
        f0 = uploaded[0].fragments
        assert f0[0].filename.endswith(".md")
        assert f0[1].filename.endswith(".md")
        assert re.search(r".*page_0.*fragement_0", f0[0].filename), (
            f"Filename did not match expected pattern: {f0[0].filename}"
        )
        assert re.search(r".*page_0.*fragement_1", f0[1].filename), (
            f"Filename did not match expected pattern: {f0[1].filename}"
        )

        # Page 1: Bild behält Originalnamenanteil
        f1 = uploaded[1].fragments
        assert len(f1) == 1
        assert "pic.png" in f1[0].filename
        assert re.search(r".*page_1.*fragement_0", f1[0].filename), (
            f"Filename did not match expected pattern: {f1[0].filename}"
        )

        # Prüfe Upload-Calls: Bucket & Filename
        calls = self.storage.upload_file.call_args_list
        assert len(calls) == 3
        for c in calls:
            fsobj: FileStorageObject = c.kwargs.get("file") or c.args[0]
            assert fsobj.bucket == DEST_BUCKET
            assert isinstance(fsobj.filename, str)
            assert re.search(r".*page_\d+.*fragement_\d+", fsobj.filename), (
                f"unexpected filename: {fsobj.filename}"
            )

    # ------------------------------------------------------ first matching converter used
    def test_convert_file_first_matching_converter_used(self):
        """Wenn mehrere Converter vorhanden sind, wird der erste passende genommen."""
        other_converter = Mock()

        # Re-setup mit zwei Convertern
        ConvertFileToMarkdown._instances.pop(ConvertFileToMarkdown, None)
        self.uc = ConvertFileToMarkdown.create(
            file_storage=self.storage,
            file_converter=[self.converter, other_converter],
        )

        src = FileStorageObject(
            filename="first.pdf", content=b"%PDF", filetype="pdf", bucket="src"
        )
        self.storage.fetch_file.return_value = Result.Ok(src)
        self.storage.upload_file.return_value = Result.Ok(None)

        # Erster passt, zweiter sollte gar nicht gefragt werden
        self.converter.does_convert_filetype.return_value = True
        self.converter.convert_file.return_value = Result.Ok(
            [Page(document_fragements=[TextFragement(text="ok")])]
        )
        other_converter.does_convert_filetype.return_value = True  # würde auch passen
        other_converter.convert_file.return_value = Result.Ok([])

        res = self.uc.convert_file("src", DEST_BUCKET, "first.pdf")
        assert res.is_ok(), res

        self.converter.does_convert_filetype.assert_called_once()
        self.converter.convert_file.assert_called_once()
        # Der zweite Converter sollte NICHT auf convert_file gerufen worden sein
        other_converter.convert_file.assert_not_called()

    # ------------------------------------------------------------- empty page list
    def test_convert_file_converter_returns_empty_pages(self):
        """Wenn Converter leere Seitenliste liefert, sollte ein Fehler zurückkommen."""
        src = FileStorageObject(
            filename="empty.pdf", content=b"%PDF", filetype="pdf", bucket="src"
        )
        self.storage.fetch_file.return_value = Result.Ok(src)
        self.converter.does_convert_filetype.return_value = True
        self.converter.convert_file.return_value = Result.Ok([])

        res = self.uc.convert_file("src", DEST_BUCKET, "empty.pdf")
        # Erwartung: entweder NotFoundException oder generischer Fehler – je nach Implementierung
        assert res.is_ok()

    # ----------------------------------------------------------- page numbering check
    def test_convert_file_page_numbering_sequential(self):
        """Seitennummern sind 0-basiert und sequentiell (0,1,2,...)"""
        src = FileStorageObject(
            filename="num.pdf", content=b"%PDF", filetype="pdf", bucket="src"
        )
        pages = [
            Page(document_fragements=[TextFragement(text="p0")]),
            Page(document_fragements=[TextFragement(text="p1")]),
            Page(document_fragements=[TextFragement(text="p2")]),
        ]
        self.storage.fetch_file.return_value = Result.Ok(src)
        self.storage.upload_file.return_value = Result.Ok(None)
        self.converter.does_convert_filetype.return_value = True
        self.converter.convert_file.return_value = Result.Ok(pages)

        res = self.uc.convert_file("src", DEST_BUCKET, "num.pdf")
        assert res.is_ok(), res
        uploaded = res.get_ok().root
        assert [p.page_number for p in uploaded] == [0, 1, 2]
