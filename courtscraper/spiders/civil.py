from scrapy import Request

from .base import CourtSpiderBase


class CivilSpider(CourtSpiderBase):
    name = "civil"
    url = "https://casesearch.cookcountyclerkofcourt.org/CivilCaseSearchAPI.aspx"

    def __init__(self, division="2", year=2022, **kwargs):
        self.case_type = DIVISIONS[division]
        self.year = year
        self.misses = set()
        self.failures = set()
        self.last_successful_case_number = None
        super().__init__(**kwargs)

    def start_requests(self):
        for case_number in self.case_numbers(self.year):
            yield Request(
                CivilSpider.url,
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
                                "source": f"""$('#MainContent_ddlDatabase').val('1');
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

    def parse(self, response):
        case_info = self.get_case_info(response)
        case_info["events"] = self.get_activities(response)

        self._success(response)

        return case_info

    def case_numbers(self, year):
        base_case_num = "{year}{district}{type}{serial_format}".format(
            year=year, **self.case_type
        )

        for serial in range(self.case_type["start"], self.case_type["end"] + 1):
            case_number = base_case_num % serial
            yield case_number


DIVISIONS = {
    "2": {
        "district": "2",
        "type": "",
        "start": 0,
        "end": 999999,
        "serial_format": "%06d",
    },
    "3": {
        "district": "3",
        "type": "",
        "start": 0,
        "end": 999999,
        "serial_format": "%06d",
    },
    "4": {
        "district": "4",
        "type": "",
        "start": 0,
        "end": 999999,
        "serial_format": "%06d",
    },
    "5": {
        "district": "5",
        "type": "",
        "start": 0,
        "end": 999999,
        "serial_format": "%06d",
    },
    "6": {
        "district": "6",
        "type": "",
        "start": 0,
        "end": 999999,
        "serial_format": "%06d",
    },
    "101": {
        "district": "1",
        "type": "01",
        "start": 0,
        "end": 9999,
        "serial_format": "%04d",
    },
    "104": {
        "district": "1",
        "type": "04",
        "start": 0,
        "end": 9999,
        "serial_format": "%04d",
    },
    "11": {
        "district": "1",
        "type": "1",
        "start": 0,
        "end": 99999,
        "serial_format": "%05d",
    },
    "13": {
        "district": "1",
        "type": "3",
        "start": 0,
        "end": 99999,
        "serial_format": "%05d",
    },
    "14": {
        "district": "1",
        "type": "4",
        "start": 0,
        "end": 99999,
        "serial_format": "%05d",
    },
    "15": {
        "district": "1",
        "type": "5",
        "start": 0,
        "end": 99999,
        "serial_format": "%05d",
    },
    "17": {
        "district": "1",
        "type": "7",
        "start": 12430,
        # "start": 4750,  # most eviction cases are sealed from March 9,
        #                # 2020, to March 31, 2022
        "end": 99999,
        "serial_format": "%05d",
    },
}
