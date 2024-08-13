import logging
from datetime import datetime, timedelta
from collections import defaultdict
from itertools import chain

from scrapy import Spider, Request
from scrapy.http import FormRequest
from scrapy.exceptions import CloseSpider
from scrapy.spidermiddlewares.httperror import HttpError

from lxml import html

from scripts.hash import dict_hash


class CourtCallSpider(Spider):
    name = "courtcalls"
    url = "https://casesearch.cookcountyclerkofcourt.org/CourtCallSearch.aspx"

    def __init__(self, **kwargs):
        self.failures = set()
        self.case_calendars = {}
        super().__init__(**kwargs)

    def next_business_days(self, n):
        """Returns the dates of the next n business days."""

        current_date = datetime.today()
        count = 0
        while count <= n:
            yield f"{current_date.month}/{current_date.day}/{current_date.year}"

            next_date = current_date + timedelta(days=1)
            while next_date.weekday() > 4:
                # Skip weekends
                next_date += timedelta(days=1)

            current_date = next_date
            count += 1

    def start_requests(self):
        for division in ["CV", "CH", "PB"]:
            for date in self.next_business_days(5):
                yield Request(
                    CourtCallSpider.url,
                    meta={
                        "zyte_api_automap": {
                            "httpResponseHeaders": True,
                            "browserHtml": True,
                            "actions": [
                                {
                                    "action": "waitForSelector",
                                    "selector": {
                                        "type": "css",
                                        "value": "#MainContent_rblSearchType_2",
                                    },
                                    "timeout": 5,
                                    "onError": "return",
                                },
                                {
                                    "action": "click",
                                    "selector": {
                                        "type": "css",
                                        "value": "#MainContent_rblSearchType_2",
                                    },
                                    "onError": "return",
                                },
                                {
                                    "action": "waitForSelector",
                                    "selector": {
                                        "type": "css",
                                        "value": "#MainContent_ddlDivisionCode",
                                    },
                                    "timeout": 5,
                                    "onError": "return",
                                },
                                {
                                    "action": "select",
                                    "selector": {
                                        "type": "css",
                                        "value": "#MainContent_ddlDivisionCode",
                                    },
                                    "values": [division],
                                    "onError": "return",
                                },
                                {
                                    "action": "type",
                                    "selector": {
                                        "type": "css",
                                        "value": "#MainContent_dtTxt",
                                    },
                                    "text": date,
                                    "onError": "return",
                                },
                                {
                                    "action": "click",
                                    "selector": {
                                        "type": "css",
                                        "value": "#MainContent_btnSearch",
                                    },
                                    "onError": "return",
                                },
                                {
                                    "action": "waitForSelector",
                                    "selector": {
                                        "type": "css",
                                        "value": "#MainContent_pnlResults",
                                    },
                                    "timeout": 5,
                                    "onError": "return",
                                },
                            ],
                        },
                        "date": date,
                        "result_page_num": 1,
                        "division": division,
                        "calendars": {},
                        "priority": -1,
                    },
                    errback=self.handle_error,
                    callback=self.parse_results_page,
                    priority=-1,
                )

    def has_page_num(self, n, response):
        """Check if there's an nth page of court call results."""

        tree = html.fromstring(response.text)
        page_table = tree.xpath("//table")[1]
        next_page_link = page_table.xpath(f".//a[contains(@href,'Page${n}')]")
        return bool(next_page_link)

    def has_results(self, response):
        """Check if a court call search results page is empty."""

        tree = html.fromstring(response.text)
        results_table = tree.xpath("//table[@id='MainContent_grdRecords']")[0]

        no_results = results_table.xpath(
            ".//*[text()[contains(.,'No cases found matching your selected"
            " criteria.')]]"
        )
        if no_results:
            return False

        return True

    def get_court_calls(self, response):
        """Returns the court calls found on a result page."""

        tree = html.fromstring(response.text)
        results_table = tree.xpath("//table[@id='MainContent_grdRecords']")[0]
        rows = results_table.xpath(".//tr")
        headers = rows[0].xpath(".//a/text()")

        court_calls = defaultdict(list)
        case_details_to_fetch = []
        already_requested_case = set()
        for result_num, row in enumerate(rows[1:-1]):
            cells = row.xpath(".//td/text()")
            if cells:
                court_call = dict(zip(headers, cells))
                case_num = court_call["Case Number"]

                if case_num in self.case_calendars:
                    # Only get a case's calendar value once
                    court_call["Calendar"] = self.case_calendars[case_num]
                    court_call["hash"] = dict_hash(court_call)
                elif case_num not in already_requested_case:
                    # We need to remember what position this case occupies
                    # in the results list to request the detail page
                    case_details_to_fetch.append((case_num, result_num))
                    already_requested_case.add(case_num)

                court_calls[case_num].append(court_call)

        try:
            case_num, result_num = case_details_to_fetch.pop()
        except IndexError:
            # We already have calendar values for all the cases on this page
            yield from chain.from_iterable(court_calls.values())
            return

        form_data = self.extract_form(response, "//form[@id='ctl01']")
        form_data["__EVENTTARGET"] = "ctl00$MainContent$grdRecords"
        form_data["__EVENTARGUMENT"] = f"Select${result_num}"
        yield FormRequest.from_response(
            response,
            meta={
                "current_case": case_num,
                "case_details_to_fetch": case_details_to_fetch,
                "court_calls": court_calls,
                "result_page_form": form_data,
                "result_page_response": response,
                "priority": response.meta["priority"] - 1,
            },
            formxpath="//form[@id='ctl01']",
            formdata=form_data,
            callback=self.parse_calendar,
            dont_click=True,
            priority=response.meta["priority"] - 1,
        )

    def parse_calendar(self, response):
        """Adds the calendar and hash to a court call's dictionary."""

        calendar = response.xpath("//span[@id='MainContent_lblCalendar']/text()").get()
        current_case_calls = response.meta["court_calls"][response.meta["current_case"]]
        for call in current_case_calls:
            call["Calendar"] = calendar
            call["hash"] = dict_hash(call)

        self.case_calendars[response.meta["current_case"]] = calendar

        if not response.meta["case_details_to_fetch"]:
            # We've got the calendar value of all of the results
            # on the current page
            yield from chain.from_iterable(response.meta["court_calls"].values())

        else:
            # Request the case detail for the next case on our stack
            next_case_num, next_result_num = response.meta[
                "case_details_to_fetch"
            ].pop()

            form_data = response.meta["result_page_form"]
            form_data["__EVENTARGUMENT"] = f"Select${next_result_num}"
            yield FormRequest.from_response(
                response.meta["result_page_response"],
                meta={
                    "current_case": next_case_num,
                    "case_details_to_fetch": response.meta["case_details_to_fetch"],
                    "court_calls": response.meta["court_calls"],
                    "result_page_form": form_data,
                    "result_page_response": response.meta["result_page_response"],
                    "priority": response.meta["priority"] - 1,
                },
                formxpath="//form[@id='ctl01']",
                formdata=form_data,
                callback=self.parse_calendar,
                dont_click=True,
                priority=response.meta["priority"] - 1,
            )

            logging.info(
                f"Fetching calendar for case {response.meta['current_case']}..."
            )

    def extract_form(self, response, form_xpath):
        """
        ASP.NET pages are essentially forms that store the data needed to send
        POST requests in hidden form inputs on the page.

        From https://www.trickster.dev/post/scraping-legacy-asp-net-site-with-
        scrapy-a-real-example/
        """

        form_data = dict()

        for hidden_input in response.xpath(form_xpath).xpath(
            ".//input[@type='hidden']"
        ):
            name = hidden_input.attrib.get("name")
            if name is None:
                continue
            value = hidden_input.attrib.get("value")
            if value is None:
                value = ""

            form_data[name] = value

        return form_data

    def get_page_n_form_data(self, n, response):
        """
        Returns the form fields needed to send a POST request
        for the nth page of court call results.
        """

        form_data = self.extract_form(response, "//form[@id='ctl01']")
        form_data["__EVENTTARGET"] = "ctl00$MainContent$grdRecords"
        form_data["__EVENTARGUMENT"] = f"Page${n}"
        return form_data

    def parse_results_page(self, response):
        if self.has_results(response):
            yield from self.get_court_calls(response)
        else:
            logging.error(
                f"No results found for division {response.meta['division']}"
                f" on {response.meta['date']}!"
            )
            return

        # Request the next page of results
        next_page_num = response.meta["result_page_num"] + 1
        next_page_exists = self.has_page_num(next_page_num, response)
        if not next_page_exists:
            return

        next_page_form_data = self.get_page_n_form_data(next_page_num, response)

        # Only copy over the meta entries we need
        prev_meta = {
            key: response.meta[key] for key in ["date", "result_page_num", "division"]
        }

        logging.info(
            f"Requesting page {next_page_num} of cases from "
            f"{response.meta['division']} on {response.meta['date']}..."
        )
        yield FormRequest.from_response(
            response,
            meta=prev_meta
            | {"result_page_num": next_page_num, "priority": -next_page_num * 100},
            formxpath="//form[@id='ctl01']",
            formdata=next_page_form_data,
            callback=self.parse_results_page,
            dont_click=True,
            priority=-next_page_num * 100,
        )

    def _failing_responses(self, response):
        self.failures.add(
            f"{response.meta['date']} page {response.meta['result_page_num']}"
        )

        self.logger.info(f'failures: {", ".join(sorted(self.failures))}')

        if len(self.failures) > 20:
            raise CloseSpider("run of failures")

    def handle_error(self, failure):
        if failure.check(HttpError):
            response = failure.value.response
            if response.status in (404, 500):
                self._failing_responses(response)
        else:
            self.logger.error(repr(failure))
