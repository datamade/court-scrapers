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
        participant = result_tree.xpath("//span[@id='MainContent_lblPartyTitle']")[0].text[10:]

        party_info_table = result_tree.xpath("//table[@id='MainContent_gdvPartyInformationDefendant']")[0]
        defendant = party_info_table.xpath("//td") # WIP


        breakpoint()

scraper = ProbateScraper('https://casesearch.cookcountyclerkofcourt.org/ProbateDocketSearch.aspx'
)
scraper.scrape()