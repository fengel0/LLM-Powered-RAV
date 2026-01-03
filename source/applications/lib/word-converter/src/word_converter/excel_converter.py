from core.result import Result
from pathlib import Path
from domain.file_converter.interface import FileConverter
from domain.file_converter.model import Page, TableFragement
import pandas as pd


class ExcelToMarkdownConverter(FileConverter):
    #: Recognised file extensions (lower‑case, with leading dot)
    SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({"xlsx", "xls"})

    # ------------------------------------------------------------------
    # *Interface* compliance helpers
    # ------------------------------------------------------------------

    def does_convert_filetype(self, filetype: str) -> bool:  # noqa: D401, ANN001
        return filetype.lower() in self.SUPPORTED_EXTENSIONS

    def convert_file(self, file: str) -> Result[list[Page]]:  # noqa: D401
        path = Path(file)

        if not path.exists():
            return Result.Err(FileNotFoundError(path))

        try:
            xls = pd.ExcelFile(path)  # pandas picks the correct engine automatically
            pages: list[Page] = []

            for sheet_name in xls.sheet_names:
                df = xls.parse(sheet_name)  # type: ignore

                # Markdown representation (GitHub‑flavoured) – requires ``tabulate``.
                markdown_table: str = df.to_markdown(index=False)  # type: ignore

                # Helper fields ------------------------------------------------
                header: str = ", ".join(map(str, df.columns))  # type: ignore
                column: str = str(df.columns[0]) if df.columns.size else ""  # type: ignore

                fragment = TableFragement(
                    full_tabel=markdown_table,
                    header=header,
                    column=[str(columns) for columns in df.columns],
                )

                page = Page(document_fragements=[fragment])
                pages.append(page)

            return Result(pages)

        # -------- Failure path -------------------------------------------------
        except Exception as exc:  # pylint: disable=broad-except
            return Result.Err(exc)
