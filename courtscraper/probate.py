import requests

class ProbateScraper(requests.Session):
    def scrape(self):
        url = 'https://casesearch.cookcountyclerkofcourt.org/ProbateDocketSearch.aspx'
        response = requests.get(url).text

        breakpoint()


scraper = ProbateScraper()
scraper.scrape()