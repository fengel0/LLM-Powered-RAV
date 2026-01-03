from io import BytesIO
import re
from opentelemetry import trace
import logging
from core.result import Result
from marker.config.parser import ConfigParser
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict  # type: ignore
from marker.output import text_from_rendered
from pydantic import BaseModel, Field
from domain.file_converter.interface import FileConverter
from domain.file_converter.model import (
    DocumentFragement,
    ImageFragment,
    Page,
    TableFragement,
    TextFragement,
)
import torch


logger = logging.getLogger(__name__)


class MarkerPDFConverterConfig(BaseModel):
    ollama_host: str | None
    model: str | None
    use_llm: bool = False
    device: str = Field(description="allowd values mps|cuda|cpu")


class MarkerPDFConverter(FileConverter):
    converter: PdfConverter
    config: MarkerPDFConverterConfig
    tracer: trace.Tracer
    PAGINATION_RE = r"\{\d{1,5}\}\-{48}"
    # PAGINATION_RE = r"\n\n(?P<page>\d+)-{48}\n\n"

    def does_convert_filetype(self, filetype: str) -> bool:
        supported_types = ["pdf", "epub"]
        return filetype.lower() in supported_types

    def convert_file(self, file: str) -> Result[list[Page]]:
        try:
            return Result.Ok(self._transform_file_to_markdown(file))
        except Exception as e:
            logger.error(e.with_traceback(None))
            return Result.Err(e)

    def __init__(self, config: MarkerPDFConverterConfig) -> None:
        super().__init__()
        self.config = config
        marker_config = {
            "output_format": "markdown",
            "use_llm": self.config.use_llm,
            "llm_service": "marker.services.ollama.OllamaService",
            "ollama_base_url": self.config.ollama_host,
            "ollama_model": self.config.model,
        }
        config_parser = ConfigParser(marker_config)
        self.tracer = trace.get_tracer("MarkerPDFConvert")
        with self.tracer.start_as_current_span("download-model"):
            self.converter = PdfConverter(
                config=config_parser.generate_config_dict(),  # type: ignore
                artifact_dict=create_model_dict(),  # type: ignore
                llm_service=config_parser.get_llm_service(),  # type: ignore
            )

    def _merge_consecutive_text_fragments(
        self,
        fragments: list[DocumentFragement],
    ) -> list[DocumentFragement]:
        if not fragments:
            return []

        merged: list[DocumentFragement] = []
        buffer: TextFragement | None = None

        for fragment in fragments:
            if isinstance(fragment, TextFragement):
                if buffer is None:
                    buffer = fragment
                else:
                    buffer.text += "\n" + fragment.text
            else:
                if buffer:
                    merged.append(buffer)
                    buffer = None
                merged.append(fragment)

        if buffer:
            merged.append(buffer)

        return merged

    def _transform_file_to_markdown(self, file: str) -> list[Page]:
        pages: list[Page] = []
        with self.tracer.start_as_current_span(f"convert-page"):
            marker_config = {
                "output_format": "markdown",  # <- switch from "html" to "markdown"
                "use_llm": False,
                "llm_service": "marker.services.ollama.OllamaService",
                "ollama_base_url": self.config.ollama_host,
                "ollama_model": self.config.model,
                "paginate_output": True,
            }

            config_parser = ConfigParser(marker_config)
            converter = PdfConverter(
                config=config_parser.generate_config_dict(),  # type: ignore
                artifact_dict=create_model_dict(),  # type: ignore
                renderer=config_parser.get_renderer(),  # will be MarkdownRenderer
                llm_service=config_parser.get_llm_service(),  # type: ignore
            )

            rendered_md = converter(file)  # <- now returns Markdown #type: ignore
            md_text, _, images = text_from_rendered(rendered_md)  # type: ignore

            assert isinstance(md_text, str)
            pages_md = re.split(self.PAGINATION_RE, md_text)
            logger.error(len(pages_md))

            for page_md in pages_md:
                # Paragraphs in Markdown are separated by blank lines
                fragments: list[DocumentFragement] = []
                for block in page_md.split("\n\n"):
                    block = block.strip()
                    if not block:
                        continue

                    # handle Markdown image syntax ![alt](name.ext)
                    if block.startswith("!["):
                        # crude extraction of filename between (...)
                        img_key = block.split("(", 1)[-1].rstrip(")")
                        image_obj = images.get(img_key)  # type: ignore
                        if image_obj:
                            buf = BytesIO()
                            image_obj.save(buf, format=image_obj.format or "jpeg")  # type: ignore
                            fragments.append(
                                ImageFragment(filename=img_key, data=buf.getvalue())
                            )
                    # tables in gfm start with | or have \n|  (very basic)
                    elif block.lstrip().startswith("|"):
                        fragments.append(
                            TableFragement(full_tabel=block, header="", column=[])
                        )
                    else:
                        fragments.append(TextFragement(text=block))

                pages.append(
                    Page(
                        document_fragements=self._merge_consecutive_text_fragments(
                            fragments
                        )
                    )
                )

        return pages
