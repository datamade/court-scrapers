from abc import ABC

from scrapy import Spider, Request
from scrapy.http import FormRequest
from scrapy.spidermiddlewares.httperror import HttpError

from lxml import html

from scripts.hash import dict_hash


class CourtCallSpider(ABC, Spider):
    name = "courtcalls"
    url = "https://casesearch.cookcountyclerkofcourt.org/CourtCallSearch.aspx"

    def __init__(self, **kwargs):
        self.current_page = 1
        super().__init__(**kwargs)

    def nextBusinessDays(self, n):
        """Returns the dates of the next n business days."""

        return ["3/12/2024"]

    def start_requests(self):
        for date in self.nextBusinessDays(5):
            self.current_page = 1
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
                },
                errback=self.handle_error,
            )

    def has_page_num(self, n, response):
        """Check if there's another page of court calls."""
        tree = html.fromstring(response.text)
        page_table = tree.xpath("//table")[1]
        next_page_link = page_table.xpath(f".//a[contains(@href,'Page${n}')]")
        return bool(next_page_link)

    def get_court_calls(self, response):
        tree = html.fromstring(response.text)
        results_table = tree.xpath("//table[@id='MainContent_grdRecords']")[0]

        rows = results_table.xpath(".//tr")
        headers = rows[0].xpath(".//a/text()")
        for row in rows[1:-1]:
            cells = row.xpath(".//td/text()")
            if cells:
                yield dict(zip(headers, cells))

    def extract_form(self, response, form_xpath):
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
        form_data = self.extract_form(response, "//form[@id='ctl01']")
        form_data["__EVENTTARGET"] = "ctl00$MainContent$grdRecords"
        form_data["__EVENTARGUMENT"] = f"Page${n}"
        return form_data

    def parse(self, response):
        cases = self.get_court_calls(response)
        for case in cases:
            case["hash"] = dict_hash(case)
            yield case

        breakpoint()
        self.current_page += 1
        next_page = self.has_page_num(self.current_page, response)
        if not next_page:
            return

        # self._success(response)
        next_page_form_data = self.get_page_n_form_data(self.current_page, response)
        yield FormRequest.from_response(
            response,
            formxpath="//form[@id='ctl01']",
            formdata=next_page_form_data,
            callback=self.parse,
            dont_click=True,
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
