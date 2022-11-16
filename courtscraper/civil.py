import lxml.html
import re
import json
from torrequest import TorRequest
import random
import time

BROWSER_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "keep-alive",
    "Host": "courtlink.lexisnexis.com",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0",
}


class CivilScraper:
    base_url = "https://casesearch.cookcountyclerkofcourt.org/DocketSearch.aspx"

    def __init__(self):
        self.tr = TorRequest(proxy_port=9050, ctrl_port=9051, password=None)
        self.case_types = [
            {
                "district": "2",
                "type": "",
                "start": 0,
                "end": 999999,
                "serial_format": "%06d",
            },
            {
                "district": "3",
                "type": "",
                "start": 0,
                "end": 999999,
                "serial_format": "%06d",
            },
            {
                "district": "4",
                "type": "",
                "start": 0,
                "end": 999999,
                "serial_format": "%06d",
            },
            {
                "district": "5",
                "type": "",
                "start": 0,
                "end": 999999,
                "serial_format": "%06d",
            },
            {
                "district": "6",
                "type": "",
                "start": 0,
                "end": 999999,
                "serial_format": "%06d",
            },
            {
                "district": "1",
                "type": "01",
                "start": 0,
                "end": 9999,
                "serial_format": "%04d",
            },
            {
                "district": "1",
                "type": "04",
                "start": 0,
                "end": 9999,
                "serial_format": "%04d",
            },
            {
                "district": "1",
                "type": "1",
                "start": 0,
                "end": 99999,
                "serial_format": "%05d",
            },
            {
                "district": "1",
                "type": "3",
                "start": 0,
                "end": 99999,
                "serial_format": "%05d",
            },
            {
                "district": "1",
                "type": "4",
                "start": 0,
                "end": 99999,
                "serial_format": "%05d",
            },
            {
                "district": "1",
                "type": "5",
                "start": 0,
                "end": 99999,
                "serial_format": "%05d",
            },
            {
                "district": "1",
                "type": "7",
                "start": 0,
                "end": 99999,
                "serial_format": "%05d",
            },
        ]

    def case_urls(self, year, district, case_type, start, end, serial_format):
        base_case_num = "{year}-M{district}-{type}".format(
            year=year, district=district, type=case_type
        )

        for serial in range(start, end + 1):
            case_number = base_case_num + str(serial_format % (serial,))
            full_url_template = "https://courtlink.lexisnexis.com/cookcounty/FindDock.aspx?NCase={case_number}&SearchType=0&Database=1&case_no=&PLtype=1&sname=&CDate="
            full_url = full_url_template.format(case_number=case_number)
            yield full_url, case_number

    def iterate_case_url(self, year):
        empty_searches = 0
        empty_search_limit = 25

        for case_type in self.case_types:

            for full_url, case_number in self.case_urls(
                year, case_type['district'], case_type['type'],
                case_type['start'], case_type['end'], case_type['serial_format']
            ):
                self.tr.session.cookies.clear()
                response = self.tr.get("https://ipecho.net/plain")
                print("Tor Ip Address", response.text)
                response = self.tr.get(full_url, headers=BROWSER_HEADERS)
                time.sleep(1 + 3 * random.random())

                result_tree = lxml.html.fromstring(response.text)

                if result_tree.xpath(".//div[@id='objCaseDetails']/table"):
                    empty_searches = 0
                    yield case_number, result_tree, full_url

                elif result_tree.xpath(".//div/table[@id='dgdCaseList']"):
                    empty_searches = 0

                    print("found multiple cases for same case number at:", case_number)
                    multi_case = result_tree.xpath(".//div/table[@id='dgdCaseList']")
                    multi_case = multi_case[0].xpath("./tr[position() >= 2]")

                    for i, row in enumerate(multi_case):
                        # Go to each case link found
                        multi_case_link = row.xpath("./td[1]/a")
                        href = multi_case_link[0].attrib["href"]
                        multi_url = "https://courtlink.lexisnexis.com/cookcounty/" + href
                        response = self.tr.get(multi_url, headers=BROWSER_HEADERS)
                        time.sleep(1 + 3 * random.random())

                        multi_case_number = case_number + "-" + str(i + 1)
                        result_tree = lxml.html.fromstring(response.text)

                        yield multi_case_number, result_tree, multi_url

                else:
                    empty_searches += 1
                    print("Nothing found")
                    print("There have been", empty_searches, "empty searches")

                    # Reset Tor
                    self.tr = TorRequest(proxy_port=9050, ctrl_port=9051, password=None)
                    self.tr.reset_identity()

                    if empty_searches > empty_search_limit:
                        empty_searches = 0
                        break

    def clean_whitespace(self, text):
        return re.sub("\s+", " ", text.text_content()).strip()

    def get_case_details(self, tree):
        result = {}

        (case_details,) = tree.xpath(".//div[@id='objCaseDetails']/table[1]")

        first_column = case_details.xpath(".//tr/td[1]")
        for row in first_column:
            clean_row = self.clean_whitespace(row)
            row_list = clean_row.split(":")

            key = row_list[0]
            value = row_list[1].strip()

            result[key] = value

        last_column = case_details.xpath(".//tr/td[3]")
        for row in last_column:
            clean_row = self.clean_whitespace(row)
            row_list = clean_row.split(":")

            key = row_list[0]
            value = row_list[1].strip()

            result[key] = value

        return result

    def get_party_information(self, tree):
        (party_information,) = tree.xpath(".//div[@id='objCaseDetails']//table[2]")

        plaintiffs = []
        defendants = []
        is_defendant = False

        first_column = party_information.xpath(".//tr/td[1]")
        for row in first_column[1:]:
            clean_row = self.clean_whitespace(row)
            person = {"name": ""}

            # When reaching the row that says defendants, put following
            # names in the defendants list
            if is_defendant == True:
                person["name"] = clean_row
                defendants.append(person)
            elif clean_row == "Defendant(s)":
                is_defendant = True
            else:
                person["name"] = clean_row
                plaintiffs.append(person)

        defendants_index = 0
        is_defendant = False

        last_column = party_information.xpath(".//tr/td[3]")
        for i, row in enumerate(last_column[1:]):
            clean_row = self.clean_whitespace(row)
            attorney = ""

            # Assign the attorney to plaintiffs
            # until the str 'Attorney(s)' is found
            # then add the rest to defendants
            if is_defendant is True:
                attorney = clean_row
                defendants[defendants_index]["attorney"] = attorney
                defendants_index += 1
            elif clean_row == "Attorney(s)":
                is_defendant = True
            else:
                attorney = clean_row
                plaintiffs[i]["attorney"] = attorney

        middle_column = party_information.xpath(".//tr/td[2]")
        defendants_index = 0
        is_defendant = False
        for i, row in enumerate(middle_column):
            clean_row = self.clean_whitespace(row)

            if is_defendant is True:
                # This nested if accounts for if the first defendant does
                # not have a date of service, but the next one does.
                # The defendants index will be incremented regardless,
                # in order to keep up.
                if clean_row != "":
                    defendants[defendants_index]["date_of_service"] = clean_row
                defendants_index += 1
            elif clean_row == "Defendant Date of Service":
                is_defendant = True

        result = {
            "plaintiffs": plaintiffs,
            "defendants": defendants,
        }

        return result

    def get_case_activity(self, tree):
        case_activity = tree.xpath(
            ".//div[@id='objCaseDetails']/table[position() >= 3]"
        )

        activities_list = []
        for i, row in enumerate(case_activity):
            result = {
                "Date": "",
                "Participant": "",
                "Activity": "",
            }

            # Perform on every other table so we can organize related
            # info from the current table and the next one, in one dict
            if i % 2 == 0:

                # Even tables
                activity_meta = row.xpath(".//td")
                date = self.clean_whitespace(activity_meta[0])
                date = date.split(":")[1].strip()
                result["Date"] = date

                participant = self.clean_whitespace(activity_meta[1])
                participant = participant.split(":")[1].strip()
                result["Participant"] = participant

                # Odd tables
                activity_overview = case_activity[i + 1].xpath("./tr")
                activity_type = self.clean_whitespace(activity_overview[0])
                activity_details = case_activity[i + 1].xpath("./tr[2]//tr")

                new_activity = {
                    "Type": activity_type,
                }

                for item in activity_details:
                    row = self.clean_whitespace(item)

                    if row != "":
                        row = row.split(":")
                        detail_type = row[0]
                        detail_value = row[1].strip()
                        new_activity[detail_type] = detail_value

                result["Activity"] = new_activity
                activities_list.append(result)

        return activities_list

    def scrape_year(self, year):

        for case_number, result_tree, full_url in self.iterate_case_url(year):
            case_dict = {
                "case_url": "",
                "case_number": "",
                "case_details": {},
                "party_information": {},
                "case_activity": [],
            }

            try:
                case_dict["case_url"] = full_url
                case_dict["case_number"] = case_number

                case_dict["case_details"] = self.get_case_details(
                    result_tree
                )
                case_dict["party_information"] = self.get_party_information(
                    result_tree
                )
                case_dict["case_activity"] = self.get_case_activity(
                    result_tree
                )
                yield case_dict

            except Exception:
                print("Error: Neither of the expected tables found,")
                print("but passed previous checks")


scraper = CivilScraper()

for case in scraper.scrape_year(2021):
    case_number = case["case_number"]
    print("outputting case #:", case_number)

    file_path = f"./scrape/{case_number}.json"
    with open(file_path, "w+") as output:
        json.dump(case, output, sort_keys=True, indent=4)
    print("done")
