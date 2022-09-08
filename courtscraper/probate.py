from os.path import exists
import datetime
import re
import json

from dateutil.rrule import rrule, DAILY
import lxml.html
import requests
import mechanize


class ProbateScraper(requests.Session):
    def get_dotnet_context(self, url):
        response = self.get(url).text

        tree = lxml.html.fromstring(response)
        viewstate = tree.xpath("//input[@id='__VIEWSTATE']")[0].value
        viewstategenerator = tree.xpath("//input[@id='__VIEWSTATEGENERATOR']")[0].value
        eventvalidation = tree.xpath("//input[@id='__EVENTVALIDATION']")[0].value

        return viewstate, viewstategenerator, eventvalidation

    def party_table_parties(self, tree):
        party_info_table = tree.xpath("//table[@id='MainContent_gdvPartyInformationDefendant']")
        defendants = []
        attorneys = []
        if party_info_table:
            party_list = party_info_table[0].xpath("./tr/td/text()")
            defendant_list = []
            attorney_list = []
            for i, item in enumerate(party_list):
                if i % 2 == 0:
                    defendant_list.append(item)
                else:
                    attorney_list.append(item)

            defendants = [d.strip() for d in defendant_list if d.strip()]
            attorneys = [a.strip() for a in attorney_list if a.strip()]

        return set(defendants), set(attorneys)

    def activity_table_parties(self, tree):
        activity_table, *_ = tree.xpath("//table[@id='MainContent_gdvCaseActivity']")
        participants = []
        attorneys = []
        if activity_table is not None:
            for row in activity_table.xpath("./tr")[1:]:
                date, activity, judge, court_date, court_time, attorney, *_, participant = row.xpath(".//td/text()")

                attorney_clean = attorney.strip()
                if attorney_clean:
                    attorneys.append(attorney_clean)

                participant_clean = participant.strip()
                if participant_clean:
                    participants.append(participant_clean)


        return set(attorneys), set(participants)

    def get_parties(self, tree):
        # TODO: Rename participant to estate_of?
        # https://gitlab.com/court-transparency-project/court-scrapers/-/issues/15
        participant = tree.xpath(".//span[@id='MainContent_lblPartyTitle']")[0].text[10:]

        ptp_defendants, ptp_attorneys = self.party_table_parties(tree)
        atp_attorneys, atp_participants = self.activity_table_parties(tree)

        participants = {participant.strip(), *atp_participants}

        return {
            'participants': [*participants],
            'defendants': [*ptp_defendants],
            'attorneys': [*ptp_attorneys, *atp_attorneys]
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
        case_number = result_tree.xpath(".//span[@id='MainContent_lblDetailHeader']/descendant-or-self::*/text()")[-1]
        estate_title = result_tree.xpath(".//span[@id='MainContent_lblPartyTitle']/descendant-or-self::*/text()")[0]

        first_table, *_ = result_tree.xpath(".//table[@class='table table-striped']")[0]
        calendar, = first_table.xpath(".//span[@id='MainContent_lblCalendar']/text()") or ['']
        division, = first_table.xpath(".//span[@id='MainContent_lblDivision']/text()") or ['']
        filing_date, = first_table.xpath(".//span[@id='MainContent_lblFilingDate']/text()") or ['']
        case_type, = first_table.xpath(".//span[@id='MainContent_lblCaseType']/text()") or ['']

        return {
            'case_number': case_number.strip(),
            'calendar': calendar.strip(),
            'filing_date': filing_date.strip(),
            'division': division.strip(),
            'estate_of': self.get_estate_name(estate_title).strip(),
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

        response = self.post(url, data=next_request_body).text
        result_tree = lxml.html.fromstring(response)
        try:
            return result_tree.xpath(".//table[@id='MainContent_grdRecords']")[0]
        except ValueError:
            return

    def iterate_search_results(self, url, result_table, current_page_number=1):
        # check if this is the last page of results
        *_, last_page_text = result_table.xpath("./tr[@class='GridPager']//table//td//text()")
        current_page_text, = result_table.xpath("./tr[@class='GridPager']//span/text()")
        last_page = last_page_text == current_page_text
        # use `last_result` and `last_page` in `get_search_results` loop

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

    def initialize_date_search(self, url, br, date_str):
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
        br['ctl00$MainContent$dtTxt'] = date_str

        response = br.submit().read().decode('utf-8')
        result_tree = lxml.html.fromstring(response)

        try:
            return result_tree.xpath(".//table[@id='MainContent_grdRecords']")[0]
        except ValueError:
            return

    def get_search_results(self, url, year=2021):
        weekdays = rrule(
            DAILY,
            dtstart=datetime.date(year, 1, 2),
            until=datetime.date(year, 12, 30),
            byweekday=[0, 1, 2, 3, 4]
        )

        br = mechanize.Browser()
        br.addheaders = [('User-agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1')]
        br.set_handle_robots(False)
        for day in weekdays:
            date_str = date_str = day.strftime('%m/%d/%Y')

            result_table = self.initialize_date_search(url, br, date_str)
            if result_table is None:
                continue

            case_data = {
                'case_number': '',
                'estate_of': '',
                'claimants': [],
                'filing_date': date_str,
            }

            for result, is_last_result, is_last_page in self.iterate_search_results(url, result_table):
                # Cases can appear arbitrarily many times in search results.
                # This loop assumes that case number is a unique identifier,
                # and that records about cases will all appear together.
                #
                # If the current case number matches the previous case number,
                # continue adding information about the case.
                #
                # TODO: The same case number can be associated with many
                # different parties listed as the Estate. What does this mean?
                # https://gitlab.com/court-transparency-project/court-scrapers/-/issues/15
                #
                # TODO: Dedupe claimants.
                if case_data['case_number'] == result['case_number']:
                    case_data['claimants'].append(result['claimant'])

                # If the case number has changed, yield the previous case and
                # operate on a fresh copy of case_data.
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

            search_response = self.post(url, data=request_body).text

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

    def get_estate_name(self, estate_string):
        """Probate site has estate owner's name in 'Estate of [owner]' format"""

        pattern = r'Estate of ([A-Z, ]*)'
        result = re.search(pattern, estate_string)
        if result:
            return result.group(1)
        else:
            return ''


if __name__ == '__main__':
    import logging
    import tqdm
    import sys

    logging.basicConfig(level=logging.DEBUG)
    file_limit = int(sys.argv[1])

    scraper = ProbateScraper()
    years = [2021, 2022]
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
