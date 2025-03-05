from scrapy import Request
from scrapy.exceptions import CloseSpider

from .base import CourtSpiderBase


class LawSpider(CourtSpiderBase):
    name = "law"
    url = "https://casesearch.cookcountyclerkofcourt.org/CivilCaseSearchAPI.aspx"

    def __init__(self, division="2", **kwargs):
        super().__init__(**kwargs)

    def start_requests(self):
        for case_number in self.case_numbers:
            if self.out_of_time():
                raise CloseSpider("Hit scraping time limit.")
                return

            yield Request(
                LawSpider.url,
                meta={
                    "zyte_api_automap": {
                        "httpResponseHeaders": True,
                        "browserHtml": True,
                        "actions": [
                            {
                                "action": "waitForSelector",
                                "selector": {
                                    "type": "css",
                                    "value": "#MainContent_btnSearch",
                                },
                                "timeout": 5,
                                "onError": "return",
                            },
                            {
                                "action": "evaluate",
                                "source": f"""$('#MainContent_ddlDatabase').val('2');
                                              $('#MainContent_txtCaseNumber').val('{case_number}');
                                              $('#MainContent_btnSearch').click();""",
                            },
                            {
                                "action": "waitForSelector",
                                "selector": {
                                    "type": "css",
                                    "value": "#MainContent_lblDetailHeader",
                                },
                                "timeout": 5,
                                "onError": "return",
                            },
                        ],
                    },
                    "case_number": case_number,
                },
                errback=self.handle_error,
            )

    def get_case_numbers(self, year):
        # We're not scraping law division cases regularly yet.
        # Assume the law scraper will be passed an explicit list of
        # case numbers.
        return []
