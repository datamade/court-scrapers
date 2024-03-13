from abc import ABC
from datetime import datetime, timedelta

from scrapy import Spider, Request
from scrapy.http import FormRequest
from scrapy.exceptions import CloseSpider
from scrapy.spidermiddlewares.httperror import HttpError

from lxml import html

from scripts.hash import dict_hash


class CourtCallSpider(ABC, Spider):
    name = "courtcalls"
    url = "https://casesearch.cookcountyclerkofcourt.org/CourtCallSearch.aspx"

    def __init__(self, **kwargs):
        self.failures = set()
        super().__init__(**kwargs)

    def nextBusinessDays(self, n):
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
        for date in self.nextBusinessDays(5):
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
                                    "value": "#MainContent_dtTxt",
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
                                "values": ["CV"],
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
                },
                errback=self.handle_error,
                callback=self.parse_results,
            )

    def has_page_num(self, n, response):
        """Check if there's an nth page of court call results."""

        tree = html.fromstring(response.text)
        page_table = tree.xpath("//table")[1]
        next_page_link = page_table.xpath(f".//a[contains(@href,'Page${n}')]")
        return bool(next_page_link)

    def get_court_calls(self, response):
        """Returns the court calls found on a result page."""

        tree = html.fromstring(response.text)
        results_table = tree.xpath("//table[@id='MainContent_grdRecords']")[0]

        no_results = results_table.xpath(
            ".//*[text()[contains(.,'No cases found matching your selected"
            "criteria.')]]"
        )
        if no_results:
            return

        rows = results_table.xpath(".//tr")
        headers = rows[0].xpath(".//a/text()")
        for row in rows[1:-1]:
            cells = row.xpath(".//td/text()")
            if cells:
                yield dict(zip(headers, cells))

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

    def parse_results(self, response):
        cases = self.get_court_calls(response)
        if not cases:
            return

        for case in cases:
            case["hash"] = dict_hash(case)
            yield case

        # Request the next page of results
        next_page_num = response.meta["result_page_num"] + 1
        next_page_exists = self.has_page_num(next_page_num, response)
        if not next_page_exists:
            return

        next_page_form_data = self.get_page_n_form_data(next_page_num, response)
        yield FormRequest.from_response(
            response,
            meta={"result_page_num": next_page_num},
            formxpath="//form[@id='ctl01']",
            formdata=next_page_form_data,
            callback=self.parse_results,
            dont_click=True,
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
