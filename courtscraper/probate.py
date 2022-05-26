from os.path import exists
import datetime
import re
import json

import lxml.html
import requests
import mechanize

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

    def get_next_request_body(self, url, result_table, requested_page):
        viewstate = result_table.xpath("//input[@name='__VIEWSTATE']")[0].value
        viewstategenerator = result_table.xpath("//input[@name='__VIEWSTATEGENERATOR']")[0].value
        eventvalidation = result_table.xpath("//input[@name='__EVENTVALIDATION']")[0].value

        next_request_body = {
            '__EVENTTARGET': 'ctl00$MainContent$grdRecords',
            '__EVENTARGUMENT': f'Page${requested_page}',
            '__VIEWSTATE': viewstate,
            '__VIEWSTATEGENERATOR': viewstategenerator,
            '__EVENTVALIDATION': eventvalidation
        }

        response = requests.post(url, data=next_request_body).text
        result_tree = lxml.html.fromstring(response)
        try:
            return result_tree.xpath(".//table[@id='MainContent_grdRecords']")[0]
        except ValueError:
            return

    def iterate_search_results(self, url, result_table, current_page_number=1):
        # check if this is the last page of results
        *_, last_page_text = result_table.xpath("./tr[@class='GridPager']//table//td//text()")
        current_page_text, = result_table.xpath("./tr[@class='GridPager']//span/text()")
        last_page = True if last_page_text == current_page_text else False

        case_data = {
            'case_number': '',
            'estate_of': '',
            'claimant': ''
        }
        # this slice omits column headers (first row), and pagination links (last row)
        for result in result_table[1:-1]:
            last_result = result == result_table[-2]
            case_number, estate, claimant, *_ = result.xpath("./td/text()")
            case_data['case_number'] = case_number.strip()
            case_data['estate_of'] = estate.strip()
            case_data['claimant'] = claimant.strip()
            yield case_data, last_result, last_page

        if not last_page:
            requested_page_number = current_page_number + 1
            next_table = self.get_next_request_body(url, result_table, requested_page_number)
            yield from self.iterate_search_results(url, next_table, current_page_number=requested_page_number)

    def initialize_date_search(self, url, br):
        response = br.open(url)
        br.select_form(id='ctl01')
        br.set_all_readonly(False)

        # Select the filing date radio button
        br.find_control(name='ctl00$MainContent$rblSearchType')\
          .get(id='MainContent_rblSearchType_2').selected = True

        # Manually update event target, spoofing JavaScript callback
        br['__EVENTTARGET'] = 'ctl00$MainContent$rblSearchType$2'

        # Remove unneeded values
        br.form.clear('ctl00$MainContent$txtCaseYear')
        br.form.clear('ctl00$MainContent$txtCaseNumber')
        br.form.clear('ctl00$MainContent$btnSearch')

        # Submit the form
        br.submit()

        br.select_form(id='ctl01')
        br.set_all_readonly(False)

        # Specify the date to search
        date_str = day.strftime('%m/%d/%Y')
        br['ctl00$MainContent$dtTxt'] = date_str

        response = br.submit().read().decode('utf-8')
        result_tree = lxml.html.fromstring(response)

        try:
            return result_tree.xpath(".//table[@id='MainContent_grdRecords']")[0]
        except ValueError:
            return

    def get_search_results(self, url, year='2021'):
        year_start = datetime.date(year, 1, 2)
        year_end = datetime.date(year, 12, 30)
        year_range = year_end - year_start
        weekdays = [
            year_start + datetime.timedelta(days=day)
            for day in range(year_range.days)
            if (year_start + datetime.timedelta(days=day)).weekday() < 5
        ]

        br = mechanize.Browser()
        br.addheaders = [('User-agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1')]
        br.set_handle_robots(False)
        for day in weekdays:
            result_table = self.initialize_date_search(url, br)
            if not result_table:
                continue

            case_data = {
                'case_number': '',
                'estate_of': '',
                'claimants': [],
                'filing_date': date_str,
            }

            for result, is_last_result, is_last_page in self.iterate_search_results(url, result_table):
                if case_data['case_number'] == result['case_number']:
                    case_data['claimants'].append(result['claimant'])

                elif case_data['case_number'] != result['case_number']:
                    if case_data['case_number']:  # Don't yield initial empty case data
                        yield case_data

                    case_data['case_number'] = result['case_number']
                    case_data['estate_of'] = result['estate_of']
                    case_data['claimants'] = [result['claimant']]

                if is_last_result and is_last_page:
                    yield case_data

    def scrape(self, url, year='2021'):
        viewstate, viewstategenerator, eventvalidation = self.get_dotnet_context(url)

        for result in self.get_search_results(url, year=year):
            case_year = result['case_number'][:4],
            case_code = result['case_number'][4],
            case_number = result['case_number'][5:]
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

            search_response = requests.post(url, data=request_body).text

            result_tree = lxml.html.fromstring(search_response)

            header, = result_tree.xpath("//span[@id='MainContent_lblDetailHeader']")
            header_case_number, = header.xpath(".//strong/text()")
            if 'No information found' in header_case_number:
                yield result['case_number'], result
            else:
                case_info = self.get_case_info(result_tree)
                party_info = self.get_parties(result_tree)
                events = self.get_docket_events(result_tree)

                case_obj = {
                    **case_info,
                    **party_info,
                    **result,
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
            print(f"Successfully scraped {case_number}")
