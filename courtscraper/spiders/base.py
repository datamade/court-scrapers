import os
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone

from scrapy import Spider
from scrapy.exceptions import CloseSpider
from scrapy.spidermiddlewares.httperror import HttpError

from scripts.hash import dict_hash


class UnsuccessfulAutomation(Exception):
    ...


class CourtSpiderBase(ABC, Spider):
    def __init__(
        self,
        division="2",
        year=2024,
        start=0,
        case_numbers="",  # Comma-separated string of case numbers
        case_numbers_file=None,
        **kwargs,
    ):
        self.year = year
        self.misses = set()
        self.failures = set()
        self.last_successful_case_number = None
        self.update = bool(case_numbers_file)
        self.start = int(start)

        if case_numbers_file:
            self.case_numbers = self.case_numbers_from_file(case_numbers_file)
        else:
            self.case_numbers = self.get_case_numbers(self.year)

        if case_numbers:
            self.case_numbers = case_numbers.split(",")

        start_time_iso = os.getenv(
            "START_TIME", datetime.now(tz=timezone.utc).isoformat()
        )
        self.start_time = datetime.fromisoformat(start_time_iso)

        time_limit_in_secs = os.getenv("TIME_LIMIT", 21600)
        self.time_limit = timedelta(seconds=int(time_limit_in_secs))

        super().__init__(**kwargs)

    @property
    @abstractmethod
    def name(self):
        pass

    @property
    @abstractmethod
    def url(self):
        pass

    @abstractmethod
    def start_requests(self):
        pass

    @abstractmethod
    def get_case_numbers(self):
        pass

    def out_of_time(self) -> bool:
        """
        Checks whether the we have enough time to continue scraping.
        We'll assume we need at most 30 minutes to clean up and finish
        post-scrape tasks.
        """

        runtime = datetime.now(tz=timezone.utc) - self.start_time
        if runtime >= self.time_limit:
            return True

        return False

    def case_numbers_from_file(self, filename):
        with open(filename) as f:
            for case_number in f:
                yield case_number.strip()

    def parse(self, response):
        try:
            case_info = self.get_case_info(response)
            case_info.update(
                {
                    "events": self.get_activities(response),
                    "court": self.name,
                }
            )
            case_info["hash"] = dict_hash(case_info)
        except Exception as e:
            self.logger.error(
                f"Error while parsing case {response.meta['case_number']}"
            )
            raise e

        self._success(response)

        return case_info

    def get_case_info(self, response):
        case_number = response.xpath(
            "//span[@id='MainContent_lblCaseNumber']/text()"
        ).get()
        calendar = response.xpath("//span[@id='MainContent_lblCalendar']/text()").get()
        filing_date = response.xpath(
            "//span[@id='MainContent_lblDateFiled']/text()"
        ).get()
        division = response.xpath(".//span[@id='MainContent_lblDivision']/text()").get()
        case_type = response.xpath("//span[@id='MainContent_lblCaseType']/text()").get()

        plaintiffs = response.xpath(
            "//td/span[@id='MainContent_lblPlaintiffs']/text()"
        ).getall()

        defendants = response.xpath(
            "//td/span[@id='MainContent_lblDefendants']/text()"
        ).getall()

        attorneys = response.xpath(
            "//td/span[@id='MainContent_lblAttorney']/text()"
        ).getall()

        ad_damnum = response.xpath("//span[@id='MainContent_lblAdDamnum']/text()").get()

        return {
            "case_number": case_number.strip(),
            "calendar": calendar.strip() if calendar else None,
            "filing_date": filing_date.strip(),
            "division": division.strip(),
            "case_type": case_type.strip(),
            "ad_damnum": ad_damnum.strip() if ad_damnum else None,
            "plaintiffs": [plaintiff.strip() for plaintiff in plaintiffs],
            "defendants": [defendant.strip() for defendant in defendants],
            "attorneys": [attorney.strip() for attorney in attorneys],
        }

    def get_activities(self, response):
        case_activities = []

        case_activity_tables = response.xpath(
            ".//td[contains(text(), 'Activity Date')]/ancestor::table"
        )

        for activity_table in case_activity_tables:
            activity = {}
            cells = activity_table.xpath("./tbody/tr/td")

            for i in range(0, len(cells), 2):
                key = cells[i].xpath("./text()").get().strip(": \n")

                try:
                    value = cells[i + 1].xpath("./text()").get()
                except IndexError:
                    value = ""

                activity[key] = value.strip() if value else ""

            case_activities.append(
                {
                    "description": activity["Event Desc"],
                    "date": activity["Activity Date"],
                    "comments": activity["Comments"],
                }
            )

        return case_activities[::-1]

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
