from abc import ABC, abstractmethod

from scrapy import Request, Spider
from scrapy.exceptions import CloseSpider


from scrapy.spidermiddlewares.httperror import HttpError


class UnsuccessfulAutomation(Exception):
    ...


class CourtSpiderBase(ABC, Spider):
    def __init__(self, url, zyteMeta, division="2", year=2022, **kwargs):
        self.url = url
        self.zyteMeta = zyteMeta
        self.case_type = DIVISIONS[division]
        self.year = year
        self.misses = set()
        self.failures = set()
        self.last_successful_case_number = None
        super().__init__(**kwargs)

    @abstractmethod
    def case_numbers(self, year):
        pass

    @abstractmethod
    def parse(self, response):
        pass

    def start_requests(self):
        for case_number in self.case_numbers(self.year):
            yield Request(
                self.url,
                meta=self.zyteMeta,
                errback=self.handle_error,
            )

    def handle_error(self, failure):
        if failure.check(HttpError):
            response = failure.value.response
            if response.status == 404:
                self._missing_case(response)
            elif response.status == 500:
                self._failing_responses(response)
        else:
            self.logger.error(repr(failure))

    def _missing_case(self, response):
        missing_case_number = response.meta["case_number"]
        if self.last_successful_case_number is None:
            self.misses.add(missing_case_number)
        elif missing_case_number > self.last_successful_case_number:
            self.misses.add(missing_case_number)

        if self.misses:
            self.logger.info(f'misses: {", ".join(sorted(self.misses))}')

        if len(self.misses) > 50:
            breakpoint()
            raise CloseSpider("run of missing case number")

    def _failing_responses(self, response):
        failing_case_number = response.meta["case_number"]
        self.failures.add(failing_case_number)

        self.logger.info(f'failures: {", ".join(sorted(self.failures))}')

        if len(self.failures) > 20:
            raise CloseSpider("run of failures")

    def _success(self, response):
        successful_case_number = response.meta["case_number"]

        if self.last_successful_case_number is None:
            self.last_successful_case_number = successful_case_number
        elif self.last_successful_case_number < successful_case_number:
            self.last_successful_case_number = successful_case_number

        if successful_case_number == self.last_successful_case_number:
            self.misses = {
                case_number
                for case_number in self.misses
                if case_number > successful_case_number
            }

            if hasattr(response, "raw_api_response"):
                self.failures = set()


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
