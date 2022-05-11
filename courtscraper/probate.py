from os.path import exists

import json
import lxml.html
import requests

class ProbateScraper(requests.Session):
    def get_cell_value(self, cell):
        if cell:
            return cell[0].text or ''
        return ''

    def scrape(self, url, year='2019', division_code='P', first_case_number=1, final_case_number=50):
        response = requests.get(url).text

        tree = lxml.html.fromstring(response)
        viewstate = tree.xpath("//input[@id='__VIEWSTATE']")[0].value
        viewstategenerator = tree.xpath("//input[@id='__VIEWSTATEGENERATOR']")[0].value
        eventvalidation = tree.xpath("//input[@id='__EVENTVALIDATION']")[0].value

        # searching by case number is the default; no need to change form type
        for i in range(first_case_number, final_case_number + 1):
            if exists(f'./courtscraper/scrape/{year}{division_code}{i}.json'):
                continue
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

            header = result_tree.xpath("//span[@id='MainContent_lblDetailHeader']")[0]
            header_case_number = header.xpath(".//strong")[0].text
            if 'No information found' in header_case_number:
                header_case_number = header_case_number.split(":")[1]
                file_path = f'./courtscraper/scrape/{header_case_number}.json'
                with open(file_path, 'w+') as output:
                    output.write(json.dumps({}))
                continue

            participant = result_tree.xpath(".//span[@id='MainContent_lblPartyTitle']")[0].text[10:]

            # First data table
            first_table = result_tree.xpath(".//table[@class='table table-striped']")[0]

            case_number_cell = first_table.xpath(".//span[@id='MainContent_lblCaseNumber']")
            case_number = self.get_cell_value(case_number_cell)

            calendar_cell = first_table.xpath(".//span[@id='MainContent_lblCalendar']")
            calendar = self.get_cell_value(calendar_cell)

            date_filed_cell = first_table.xpath(".//span[@id='MainContent_lblDateFiled']")
            date_filed = self.get_cell_value(date_filed_cell)

            division_cell = first_table.xpath(".//span[@id='MainContent_lblDivision']")
            division = self.get_cell_value(division_cell)

            filing_date_cell = first_table.xpath(".//span[@id='MainContent_lblFilingDate']")
            filing_date = self.get_cell_value(filing_date_cell)

            estate_of_cell = first_table.xpath(".//span[@id='MainContent_lblEstateOf']")
            estate_of = self.get_cell_value(estate_of_cell)

            case_type_cell = first_table.xpath(".//span[@id='MainContent_lblCaseType']")
            case_type = self.get_cell_value(case_type_cell)

            # Party information
            party_info_table = result_tree.xpath("//table[@id='MainContent_gdvPartyInformationDefendant']")
            if party_info_table:
                defendant = party_info_table[0].xpath("./tr/td")[0].text.strip()
                attorney = party_info_table[0].xpath("./tr/td")[1].text.strip()
            else:
                defendant = ''
                attorney = ''

            # Case activity
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

            case_obj = {
                'case_number': case_number.strip(),
                'calendar': calendar.strip(),
                'filing_date': filing_date.strip(),
                'division': division.strip(),
                'date_filed': date_filed.strip(),
                'estate_of': estate_of.strip(),
                'case_type': case_type.strip(),
                'defendant': defendant.strip(),
                'attorney': attorney.strip(),
                'case_activity': case_activity,
            }

            file_path = f'./courtscraper/scrape/{header_case_number}.json'
            with open(file_path, 'w+') as output:
                output.write(json.dumps(case_obj, sort_keys=True, indent=4))

if __name__ == '__main__':
    scraper = ProbateScraper()
    years = [2019, 2020, 2021]
    url = 'https://casesearch.cookcountyclerkofcourt.org/ProbateDocketSearch.aspx'
    for year in years:
        scraper.scrape(url, year=year)
        scraper.scrape(url, year=year, division_code='W', first_case_number=70000,
                       final_case_number=70050)
        scraper.scrape(url, year=year, division_code='W', first_case_number=71000,
                       final_case_number=71050)
