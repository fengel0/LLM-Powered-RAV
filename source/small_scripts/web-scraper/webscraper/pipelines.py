from urllib.parse import urlparse
from scrapy.pipelines.files import FilesPipeline
from webscraper.items import HtmlItem
import posixpath
import os


class DocFilesPipeline(FilesPipeline):
    def file_path(self, request, response=None, info=None, *, item=None):
        """
        Store as ./websides/<domain>/<full/original/path/filename.ext>
        e.g. websides/fh-erfurt.de/studium/ordnungen/abc.pdf
        """
        p = urlparse(request.url)
        # p.path always starts with "/" → strip it; keep query cleanly out
        rel_path = p.path.lstrip("/") or "index"
        return posixpath.join(p.netloc, rel_path)


class HtmlSavePipeline:
    def process_item(self, item, spider):
        if not isinstance(item, HtmlItem):
            return item

        p = urlparse(item["url"])
        rel_path = p.path.lstrip("/")
        # /      → index.html
        # /foo/  → foo/index.html
        # /bar   → bar.html
        if not rel_path or rel_path.endswith("/"):
            rel_path = posixpath.join(rel_path, "index.html")
        elif not rel_path.lower().endswith(".html"):
            rel_path += ".html"

        full_path = os.path.join(spider.settings.get("FILES_STORE"), p.netloc, rel_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "wb") as fh:
            fh.write(item["body"])
        return item
