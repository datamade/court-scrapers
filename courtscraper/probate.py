from os.path import exists

import json
import lxml.html
import requests

class ProbateScraper(requests.Session):
    def get_dotnet_context(self, url):
        response = requests.get(url).text

        tree = lxml.html.fromstring(response)
        viewstate = tree.xpath("//input[@id='__VIEWSTATE']")[0].value
        viewstategenerator = tree.xpath("//input[@id='__VIEWSTATEGENERATOR']")[0].value
        eventvalidation = tree.xpath("//input[@id='__EVENTVALIDATION']")[0].value

        return viewstate, viewstategenerator, eventvalidation

    def get_parties(self, tree):
        participant = tree.xpath(".//span[@id='MainContent_lblPartyTitle']")[0].text[10:]

        party_info_table = tree.xpath("//table[@id='MainContent_gdvPartyInformationDefendant']")
        if party_info_table:
            defendant, attorney = party_info_table[0].xpath("./tr/td/text()")
        else:
            defendant = ''
            attorney = ''

        return {
            'participant': participant.strip(),
            'defendant': defendant.strip(),
            'attorney': attorney.strip()
        }

    def get_docket_events(self, result_tree):
        case_activity_table = result_tree.xpath("//table[@id='MainContent_gdvCaseActivity']")[0]
        case_activity_rows = case_activity_table.xpath("./tr")

        case_activity = []
        for row in case_activity_rows[1:]:
            cells = row.xpath("./td")
            case_activity.append({
                'activity_date': cells[0].text.strip(),
                'activity': cells[1].text.strip(),
                'judge': cells[2].text.strip(),
                'court_date': cells[3].text.strip(),
                'court_time': cells[4].text.strip(),
                'attorney': cells[5].text.strip(),
                'court_fee': cells[6].text.strip(),
                'court_room': cells[7].text.strip(),
                'participant': cells[8].text.strip()
            })

        return case_activity

    def get_case_info(self, result_tree):
        first_table, *_ = result_tree.xpath(".//table[@class='table table-striped']")[0]

        case_number, = first_table.xpath(".//span[@id='MainContent_lblCaseNumber']/text()") or ['']
        calendar, = first_table.xpath(".//span[@id='MainContent_lblCalendar']/text()") or ['']
        date_filed, = first_table.xpath(".//span[@id='MainContent_lblDateFiled']/text()") or ['']
        division, = first_table.xpath(".//span[@id='MainContent_lblDivision']/text()") or ['']
        filing_date, = first_table.xpath(".//span[@id='MainContent_lblFilingDate']/text()") or ['']
        estate_of, = first_table.xpath(".//span[@id='MainContent_lblEstateOf']/text()") or ['']
        case_type, = first_table.xpath(".//span[@id='MainContent_lblCaseType']/text()") or ['']

        return {
            'case_number': case_number.strip(),
            'calendar': calendar.strip(),
            'filing_date': filing_date.strip(),
            'division': division.strip(),
            'date_filed': date_filed.strip(),
            'estate_of': estate_of.strip(),
            'case_type': case_type.strip()
        }

    def get_next_request_body(self, html_tree):
        # use the html tree for current page of search results
        # to return new request obj:
        # next_request_body = {
            # __EVENTTARGET: ctl00$MainContent$grdRecords
            # __EVENTARGUMENT: Page$6
            # __VIEWSTATE: [from current html_tree]
            # __VIEWSTATEGENERATOR: [from current html_tree]
            # __EVENTVALIDATION: [from current html_tree]
        # }

        # if request fails due to page being out of range, return None
        # else, return
        pass

    def iterate_search_results(self, date, current_page_number=1):
        # first, send post request to url using:
        # request_body = {
            # '__VIEWSTATE': viewstate,
            # '__VIEWSTATEGENERATOR': viewstategenerator,
            # '__EVENTVALIDATION': eventvalidation,
            # ctl00$MainContent$rblSearchType: FilingDate
            # ctl00$MainContent$dtTxt: date (date as string, e.g. '8/3/2021')
            # ctl00$MainContent$btnSearch: Start New Search
        # }
        # result_page = get(url, ...)

        # case_data = {
            # 'case_number': some_case_number,
            # 'claimants': a_string
        # }

        # parse out rows from table in a loop && yield data using template ^^

        # we can use this to add a "filing_date," which is often blank on the case detail page,
        # in addition to adding all names in the `Claimant, Minor or Representative` column.
        # If this case number is the last on a page (there are 10 rows per page of results),
        # the above data obj will allow us to easily avoid duplicates of cases if a case
        # has multiple rows that are broken up by a page of results.

        # if current page number != last cell in fancy table in table pagination thing
            # self.iterate_search_results(date, current_page_number + 1)
            # [handle combination in get_search_results]
        pass

    def get_search_results(self, url, year='2021'):
        # for weekday in year:
            # case_data = {
            #     'case_number': None,
            #     'filing_date': date,
            #     'claimants': [],
            # }

            # for result in self.iterate_search_results(date):
            #   check if file with this case # already exists; if so, update claimants
            #   if not, yield case_data
        pass

    def scrape(self, url, year='2021', division_code='P', first_case_number=1, final_case_number=15000):
        viewstate, viewstategenerator, eventvalidation = self.get_dotnet_context(url)

        # cases = self.get_search_results(url, year=year)

        # we will likely have to get new `viewstate`, `viewstategenerator`, and `eventvalidation` values
        # in order to search by case number

        # loop over cases instead of incrementally over all possible case numbers
        # searching by case number is the default; no need to change form type
        for i in range(first_case_number, final_case_number + 1):
            request_body = {
                '__VIEWSTATE': viewstate,
                '__VIEWSTATEGENERATOR': viewstategenerator,
                '__EVENTVALIDATION': eventvalidation,
                'ctl00$MainContent$rblSearchType': 'CaseNumber',
                'ctl00$MainContent$txtCaseYear': str(year),
                'ctl00$MainContent$txtCaseCode': division_code,
                'ctl00$MainContent$txtCaseNumber': str(i),
                'ctl00$MainContent$btnSearch': 'Start New Search'
            }


            search_response = requests.post(url, data=request_body).text

            result_tree = lxml.html.fromstring(search_response)

            header, = result_tree.xpath("//span[@id='MainContent_lblDetailHeader']")
            header_case_number, = header.xpath(".//strong/text()")
            if 'No information found' in header_case_number:
                continue

            case_info = self.get_case_info(result_tree)
            party_info = self.get_parties(result_tree)
            events = self.get_docket_events(result_tree)

            case_obj = {
                **case_info,
                **party_info,
                'events': events,
            }

            yield header_case_number, case_obj


if __name__ == '__main__':
    scraper = ProbateScraper()
    years = [2021, 2022]
    url = 'https://casesearch.cookcountyclerkofcourt.org/ProbateDocketSearch.aspx'
    for year in years:
        for case_number, case_obj in scraper.scrape(url, year=year):
            file_path = f'./courtscraper/scrape/{case_number}.json'
            with open(file_path, 'w+') as output:
                output.write(json.dumps(case_obj, sort_keys=True, indent=4))
