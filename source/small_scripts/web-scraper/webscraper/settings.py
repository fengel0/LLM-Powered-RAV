BOT_NAME = "websides"

SPIDER_MODULES = ["webscraper.spiders"]
NEWSPIDER_MODULE = "webscraper.spiders"

FILES_STORE = "./websides"  # all docs land here
MEDIA_ALLOW_REDIRECTS = True  # follow 302/301 to files

ITEM_PIPELINES = {
    "webscraper.pipelines.DocFilesPipeline": 1,
    "webscraper.pipelines.HtmlSavePipeline": 2,
}

ROBOTSTXT_OBEY = True  # be polite
DOWNLOAD_DELAY = 0.5  # throttle so the servers stay happy
LOG_LEVEL = "INFO"
