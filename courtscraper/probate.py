from os.path import exists
import datetime
import re
import json
from typing import cast

from dateutil.rrule import rrule, DAILY
import lxml.html
import requests
from scrapelib import Scraper, FileCache, CachingSession
from scrapelib.cache import CacheResponse


class POSTCachingSession(CachingSession):

    def request(
        self,
        method,
        url,
        params,
        data,
        headers,
        cookies,
        files,
        auth,
        timeout,
        allow_redirects,
        proxies,
        hooks,
        stream,
        verify,
        cert,
        json,
        retry_on_404,
    ):
        # short circuit if cache isn't configured
        if not self.cache_storage:
            resp = super().request(
                method,
                url,
                params=params,
                data=data,
                headers=headers,
                cookies=cookies,
                files=files,
                auth=auth,
                timeout=timeout,
                allow_redirects=allow_redirects,
                proxies=proxies,
                hooks=hooks,
                stream=stream,
                verify=verify,
                cert=cert,
                json=json,
                retry_on_404=retry_on_404,
            )
            resp = cast(CacheResponse, resp)
            resp.fromcache = False
            return resp

        method = method.lower()

        # Overridden to pass data arg
        request_key = self.key_for_request(method, url, params, data)
        resp_maybe = None

        if request_key and not self.cache_write_only:
            resp_maybe = self.cache_storage.get(request_key)

        if resp_maybe:
            resp = cast(CacheResponse, resp_maybe)
            resp.fromcache = True
        else:
            resp = super().request(
                method,
                url,
                data=data,
                params=params,
                headers=headers,
                cookies=cookies,
                files=files,
                auth=auth,
                timeout=timeout,
                allow_redirects=allow_redirects,
                proxies=proxies,
                hooks=hooks,
                stream=stream,
                verify=verify,
                cert=cert,
                json=json,
                retry_on_404=retry_on_404,
            )
            # save to cache if request and response meet criteria
            if request_key and self.should_cache_response(resp):
                self.cache_storage.set(request_key, resp)
            resp = cast(CacheResponse, resp)
            resp.fromcache = False

        return resp

    def key_for_request(self, method, url, params, data=None):
        if method == "post":
            prepared_url = requests.Request(url=url, params=params, data=data).prepare().url
            return f"{prepared_url},{self.cache_key_suffix(data)}"

        return requests.Request(url=url, params=params).prepare().url

    def cache_key_suffix(self, data):
        raise NotImplementedError


class POSTScraper(Scraper, POSTCachingSession):
    pass


class ProbateScraper(POSTScraper):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.cache_storage = FileCache("cache/probate")
        self.cache_write_only = False
        self.requests_per_minute = 60

    def request(self, *args, **kwargs):
        response = super().request(*args, **kwargs)

        if "1/1/0001" in response.text:
            response.status_code = 404

        return response

    def cache_key_suffix(self, data):
        if data:
            return f"{data['ctl00$MainContent$txtCaseYear']}{data['ctl00$MainContent$txtCaseCode']}{data['ctl00$MainContent$txtCaseNumber']}"

    def case_numbers(self, year, start=1, end=100):
        case_number_format = "{year}P{serial}"

        for serial in range(start, end + 1):
            padded_serial = str(serial).zfill(6)
            yield (
                str(year),
                "P",
                padded_serial,
                case_number_format.format(year=year, serial=padded_serial)
            )

    def scrape(self, url, year='2022'):
        viewstate, viewstategenerator, eventvalidation = self.get_dotnet_context(url)

        for case_year, case_code, case_number, full_case_number in self.case_numbers(year=year):
            logging.info(f"Attempting to scrape case {full_case_number}")

            request_body = {
                '__VIEWSTATE': viewstate,
                '__VIEWSTATEGENERATOR': viewstategenerator,
                '__EVENTVALIDATION': eventvalidation,
                'ctl00$MainContent$rblSearchType': 'CaseNumber',
                'ctl00$MainContent$txtCaseYear': case_year,
                'ctl00$MainContent$txtCaseCode': case_code,
                'ctl00$MainContent$txtCaseNumber': case_number,
                'ctl00$MainContent$btnSearch': 'Start New Search'
            }

            response = self.post(url, data=request_body)

            if response.ok:
                logging.info(f"Found case {full_case_number}")

                result_tree = lxml.html.fromstring(response.text)

                case_info = self.get_case_info(result_tree)
                events = self.get_activities(result_tree)

                case_obj = {
                    **case_info,
                    'events': events,
                }

                yield full_case_number, case_obj

            else:
                logging.warning(f"Case {full_case_number} not found. Skipping...")

    def get_dotnet_context(self, url):
        response = self.get(url).text

        tree = lxml.html.fromstring(response)
        viewstate = tree.xpath("//input[@id='__VIEWSTATE']")[0].value
        viewstategenerator = tree.xpath("//input[@id='__VIEWSTATEGENERATOR']")[0].value
        eventvalidation = tree.xpath("//input[@id='__EVENTVALIDATION']")[0].value

        return viewstate, viewstategenerator, eventvalidation

    def get_case_info(self, result_tree):
        case_number, = result_tree.xpath(".//span[@id='MainContent_lblCaseNumber']/text()")
        estate_title, = result_tree.xpath(".//td/span[@id='MainContent_lblCaseType']/../../td[1]/text()")
        calendar, = result_tree.xpath(".//span[@id='MainContent_lblCalendar']/text()") or ['']
        division, = result_tree.xpath(".//span[@id='MainContent_lblDivision']/text()") or ['']
        filing_date, = result_tree.xpath(".//span[@id='MainContent_lblDateFiled']/text()") or ['']
        case_type, = result_tree.xpath(".//span[@id='MainContent_lblCaseType']/text()") or ['']

        return {
            'case_number': case_number.strip(),
            'calendar': calendar.strip(),
            'filing_date': filing_date.strip(),
            'division': division.strip(),
            'estate_of': estate_title.strip(),
            'case_type': case_type.strip()
        }

    def get_activities(self, result_tree):
        case_activities = []

        case_activity_tables = result_tree.xpath(".//div[contains(text(), 'Activity Date')]/ancestor::table")

        for activity_table in case_activity_tables:
            description, = activity_table.xpath("descendant::strong/text()")
            date, = activity_table.xpath("descendant::div[contains(text(), 'Activity Date')]/text()")
            court_fee, = activity_table.xpath("descendant::td[contains(text(), 'Court Fee')]/following-sibling::td[1]/text()")
            attorney = re.sub(
                r"\s+",
                " ",
                ", ".join([line.strip() for line in activity_table.xpath("descendant::td[contains(text(), 'Attorney')]/following-sibling::td[1]/text()")])
            )
            judgement_amount, = activity_table.xpath("descendant::td[contains(text(), 'Judgement Amount')]/following-sibling::td[1]/text()")
            judge, = activity_table.xpath("descendant::td[contains(text(), 'Judge:')]/following-sibling::td[1]/text()")

            try:
                rep_minor_claimant, = activity_table.xpath("descendant::td[contains(text(), 'Rep, Minor or Claimant')]/following-sibling::td[1]/text()")
                microfilm, = activity_table.xpath("descendant::td[contains(text(), 'Microfilm')]/following-sibling::td[1]/text()")
                court_date, = activity_table.xpath("descendant::td[contains(text(), 'Court Date')]/following-sibling::td[1]/text()")
                court_room, = activity_table.xpath("descendant::td[contains(text(), 'Court Room')]/following-sibling::td[1]/text()")
                court_time, = activity_table.xpath("descendant::td[contains(text(), 'Court Time')]/following-sibling::td[1]/text()")
                insurance_code, = activity_table.xpath("descendant::td[contains(text(), 'Insurance Code')]/following-sibling::td[1]/text()")
                shared_case_number, = activity_table.xpath("descendant::td[contains(text(), 'Shared Case Number')]/following-sibling::td[1]/text()")
            except:
                import pdb
                pdb.set_trace()

            case_activities.append({
                "description": description.strip(),
                "date": date.replace("Activity Date:", "").strip(),
                "court_fee": court_fee.strip(),
                "attorney": attorney.strip(),
                "judgement_amount": judgement_amount.strip(),
                "judge": judge.strip(),
                "rep_minor_claimant": rep_minor_claimant.strip(),
                "microfilm": microfilm.strip(),
                "court_date": court_date.strip(),
                "court_room": court_room.strip(),
                "court_time": court_time.strip(),
                "insurance_code": insurance_code.strip(),
                "shared_case_number": shared_case_number.strip(),
            })

        return case_activities


if __name__ == '__main__':
    import logging
    import tqdm
    import sys

    logging.basicConfig(level=logging.DEBUG)
    file_limit = int(sys.argv[1])

    scraper = ProbateScraper()
    years = [2022]
    url = 'https://casesearch.cookcountyclerkofcourt.org/ProbateDocketSearch.aspx'
    i = 0
    for year in years:
        if i >= file_limit:
            break
        for case_number, case_obj in tqdm.tqdm(scraper.scrape(url, year=year)):
            file_path = f'./scrape/{case_number}.json'
            with open(file_path, 'w+') as output:
                output.write(json.dumps(case_obj, sort_keys=True, indent=4))
            print(f"Successfully scraped {case_number}")
            i += 1
            if i >= file_limit:
                break
