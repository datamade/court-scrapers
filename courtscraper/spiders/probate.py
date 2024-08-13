from scrapy import Request
from scrapy.exceptions import CloseSpider

from .base import CourtSpiderBase


class ProbateSpider(CourtSpiderBase):
    name = "probate"
    url = "https://casesearch.cookcountyclerkofcourt.org/ProbateDocketSearchAPI.aspx"

    def __init__(self, **kwargs):
        self.case_type = CASE_FORMAT
        super().__init__(**kwargs)

    def start_requests(self):
        for case_number in self.case_numbers:
            if self.out_of_time():
                raise CloseSpider("Hit scraping time limit.")
                return

            yield Request(
                ProbateSpider.url,
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
                                "source": f"""
                                    $('#MainContent_txtCaseNumber').val('{case_number}');
                                    $('#MainContent_btnSearch').click();
                                """,
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
        base_case_num = "{year}P{serial_format}".format(year=year, **self.case_type)

        start = self.start or self.case_type["start"]
        for serial in range(start + 1, self.case_type["end"] + 1):
            case_number = base_case_num % serial
            yield case_number


CASE_FORMAT = {
    "start": 0,
    "end": 999999,
    "serial_format": "%06d",
}
