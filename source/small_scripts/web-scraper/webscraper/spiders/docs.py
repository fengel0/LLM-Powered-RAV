# webscraper/spiders/docs.py
"""
DocsSpider
==========

• Crawls everything under fh-erfurt.de  (uncomment ai.fh-erfurt.de if needed)
• Saves every HTML page it encounters (handled by HtmlSavePipeline)
• Downloads every PDF / Word / Excel / PowerPoint – even when the URL has
  no file-name extension (e.g. TYPO3 dumpfile links)
• Ignores images and stays on the allowed domains
• Works with the DocFilesPipeline & HtmlSavePipeline already in your project
"""

from scrapy import Spider, Request
from scrapy.http import Response
from scrapy.linkextractors import LinkExtractor

from webscraper.items import DocItem, HtmlItem


class DocsSpider(Spider):
    name = "docs"

    # ------------------------------------------------------------------ #
    # Domains & entry points                                              #
    # ------------------------------------------------------------------ #
    allowed_domains = ["fh-erfurt.de"]
    start_urls = [
        "https://www.fh-erfurt.de/",
        # "https://ai.fh-erfurt.de/",
    ]

    # ------------------------------------------------------------------ #
    # Link extractor: follow every on-site HTTP/HTTPS link except images  #
    # ------------------------------------------------------------------ #
    link_extractor = LinkExtractor(
        allow_domains=allowed_domains,
        deny_extensions=[
            "jpg",
            "jpeg",
            "png",
            "gif",
            "webp",
            "svg",
            "ico",
            "bmp",
            "tiff",
        ],
        unique=True,
    )

    # ------------------------------------------------------------------ #
    # MIME prefixes treated as “documents”                               #
    # ------------------------------------------------------------------ #
    DOC_MIME_PREFIXES = (
        b"application/pdf",
        b"application/msword",
        b"application/vnd.openxmlformats-officedocument.wordprocessingml",
        b"application/vnd.ms-excel",
        b"application/vnd.openxmlformats-officedocument.spreadsheetml",
        b"application/vnd.ms-powerpoint",
        b"application/vnd.openxmlformats-officedocument.presentationml",
    )

    # ================================================================== #
    # Main callback                                                      #
    # ================================================================== #
    def parse(self, response: Response):
        # Detect the resource type from the HTTP Content-Type header
        ctype = response.headers.get(b"Content-Type", b"").split(b";", 1)[0].lower()

        # ------------ 1) Binary Office / PDF documents ------------------
        if any(ctype.startswith(pref) for pref in self.DOC_MIME_PREFIXES):
            yield DocItem(file_urls=[response.url])
            return  # nothing inside a binary file to crawl further

        # ------------ 2) HTML pages -------------------------------------
        if ctype == b"text/html":
            # Store the page (HtmlSavePipeline handles writing to disk)
            yield HtmlItem(url=response.url, body=response.body)

            # Extract and follow new links
            for link in self.link_extractor.extract_links(response):
                yield Request(link.url, callback=self.parse)

        # ------------ 3) Everything else (CSS, JS, JSON…) ---------------
        # Intentionally ignored

