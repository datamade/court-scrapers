from scrapy import signals


class CourtscraperDownloaderMiddleware:
    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_response(self, request, response, spider):
        adjusted_response = None

        if api_response := getattr(response, "raw_api_response", None):
            if not any(("error" in act) for act in api_response.get("actions", [])):
                adjusted_response = response
            elif response.xpath("//span[@id='MainContent_lblCaseNumber']/text()"):
                adjusted_response = response
            elif response.xpath("//span[@id='MainContent_lblErr']/p/strong/text()"):
                adjusted_response = response.replace(status=404)
            else:
                adjusted_response = response.replace(status=500)
        else:
            adjusted_response = response

        return adjusted_response

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)
