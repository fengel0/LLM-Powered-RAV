import scrapy


class DocItem(scrapy.Item):  # (unchanged)
    file_urls = scrapy.Field()
    files = scrapy.Field()


class HtmlItem(scrapy.Item):  # NEW
    url = scrapy.Field()
    body = scrapy.Field()  # raw bytes of the page
