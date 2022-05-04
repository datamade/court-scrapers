import requests
import lxml.html

class ProbateScraper(requests.Session):
    def __init__(self, url):
        self.url = url

    def scrape(self):
        response = requests.get(self.url).text

        tree = lxml.html.fromstring(response)
        viewstate = tree.xpath("//input[@id='__VIEWSTATE']")[0].value
        viewstategenerator = tree.xpath("//input[@id='__VIEWSTATEGENERATOR']")[0].value
        eventvalidation = tree.xpath("//input[@id='__EVENTVALIDATION']")[0].value

        # searching by case number is the default; no need to change form type
        request_body = {
            '__VIEWSTATE': viewstate,
            '__VIEWSTATEGENERATOR': viewstategenerator,
            '__EVENTVALIDATION': eventvalidation,
            'ctl00$MainContent$rblSearchType': 'CaseNumber',
            'ctl00$MainContent$txtCaseYear': '2021',
            'ctl00$MainContent$txtCaseCode': 'P',
            'ctl00$MainContent$txtCaseNumber': '000001',
            'ctl00$MainContent$btnSearch': 'Start New Search'
        }
        search_response = requests.post(self.url, data=request_body).text

        result_tree = lxml.html.fromstring(search_response)

        header = result_tree.xpath("//span[@id='MainContent_lblDetailHeader']")[0]

        participant = result_tree.xpath(".//span[@id='MainContent_lblPartyTitle']")[0].text[10:]

        # First data table
        first_table = result_tree.xpath(".//table[@class='table table-striped']")[0]

        case_number_cell = first_table.xpath(".//span[@id='MainContent_lblCaseNumber']")
        if case_number_cell:
            case_number = case_number_cell[0].text or ''
        else:
            case_number = ''

        calendar_cell = first_table.xpath(".//span[@id='MainContent_lblCalendar']")
        if calendar_cell:
            calendar = calendar_cell[0].text or ''
        else:
            calendar = ''

        date_filed_cell = first_table.xpath(".//span[@id='MainContent_lblDateFiled']")
        if date_filed_cell:
            date_filed = date_filed_cell[0].text or ''
        else:
            date_filed = ''

        division_cell = first_table.xpath(".//span[@id='MainContent_lblDivision']")
        if division_cell:
            division = division_cell[0].text or ''
        else:
            division = ''

        filing_date_cell = first_table.xpath(".//span[@id='MainContent_lblFilingDate']")
        if filing_date_cell:
            filing_date = filing_date_cell[0].text or ''
        else:
            filing_date = ''

        estate_of_cell = first_table.xpath(".//span[@id='MainContent_lblEstateOf']")
        if estate_of_cell:
            estate_of = estate_of_cell[0].text or ''
        else:
            estate_of = ''

        case_type_cell = first_table.xpath(".//span[@id='MainContent_lblCaseType']")
        if case_type_cell:
            case_type = case_type_cell[0].text or ''
        else:
            case_type = ''


        # Party information
        party_info_table = result_tree.xpath("//table[@id='MainContent_gdvPartyInformationDefendant']")[0]
        defendant = party_info_table.xpath("./tr/td")[0].text.strip()
        attorney = party_info_table.xpath("./tr/td")[1].text.strip()

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

        # json obj
        # activity as array of objs
        # scrape subdir with json objects
        # each case is its own json file
        # file name is case #

scraper = ProbateScraper('https://casesearch.cookcountyclerkofcourt.org/ProbateDocketSearch.aspx'
)
scraper.scrape()