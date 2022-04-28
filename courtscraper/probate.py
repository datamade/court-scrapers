import requests
import lxml.html

class ProbateScraper(requests.Session):
    def scrape(self):
        url = 'https://casesearch.cookcountyclerkofcourt.org/ProbateDocketSearch.aspx'
        response = requests.get(url).text

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
        search_response = requests.post(url, data=request_body).text

scraper = ProbateScraper()
scraper.scrape()