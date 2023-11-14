from scrapy import Request

from .base import CourtSpiderBase


class ChancerySpider(CourtSpiderBase):
    name = "chancery"
    url = "https://casesearch.cookcountyclerkofcourt.org/CivilCaseSearchAPI.aspx"

    def __init__(self, year=2022, **kwargs):
        self.case_type = CASE_FORMAT
        super().__init__(**kwargs)

    def get_case_numbers(self, year):
        base_case_num = "{year}CH{serial_format}".format(year=year, **self.case_type)

        for serial in range(self.case_type["start"], self.case_type["end"] + 1):
            case_number = base_case_num % serial
            yield case_number

    def start_requests(self):
        for case_number in self.case_numbers(self.year):
            yield Request(
                ChancerySpider.url,
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
                                "source": f"""$('#MainContent_ddlDatabase').val('3');
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


CASE_FORMAT = {
    "start": 0,
    "end": 999999,
    "serial_format": "%05d",
}
