from .base import CourtSpiderBase


class CivilSpider(CourtSpiderBase):
    name = "civil"

    def case_numbers(self, year):
        base_case_num = "{year}{district}{type}{serial_format}".format(
            year=year, **self.case_type
        )

        for serial in range(self.case_type["start"], self.case_type["end"] + 1):
            case_number = base_case_num % serial
            yield case_number

    def parse(self, response):
        case_info = self.get_case_info(response)
        case_info["events"] = self.get_activities(response)

        self._success(response)

        return case_info

    def get_case_info(self, response):
        case_number = response.xpath(
            "//span[@id='MainContent_lblCaseNumber']/text()"
        ).get()
        calendar = response.xpath("//span[@id='MainContent_lblCalendar']/text()").get()
        filing_date = response.xpath(
            "//span[@id='MainContent_lblDateFiled']/text()"
        ).get()
        division = response.xpath(".//span[@id='MainContent_lblDivision']/text()").get()
        case_type = response.xpath("//span[@id='MainContent_lblCaseType']/text()").get()

        plaintiffs = response.xpath(
            "//td/span[@id='MainContent_lblPlaintiffs']/text()"
        ).getall()

        defendants = response.xpath(
            "//td/span[@id='MainContent_lblDefendants']/text()"
        ).getall()

        attorneys = response.xpath(
            "//td/span[@id='MainContent_lblAttorney']/text()"
        ).getall()

        ad_damnum = response.xpath("//span[@id='MainContent_lblAdDamnum']/text()").get()

        return {
            "case_number": case_number.strip(),
            "calendar": calendar.strip(),
            "filing_date": filing_date.strip(),
            "division": division.strip(),
            "case_type": case_type.strip(),
            "ad_damnum": ad_damnum.strip(),
            "plaintiffs": [plaintiff.strip() for plaintiff in plaintiffs],
            "defendants": [defendant.strip() for defendant in defendants],
            "attorneys": [attorney.strip() for attorney in attorneys],
        }

    def get_activities(self, response):
        case_activities = []

        case_activity_tables = response.xpath(
            ".//td[contains(text(), 'Activity Date')]/ancestor::table"
        )

        for activity_table in case_activity_tables:
            activity = {}
            cells = activity_table.xpath("./tbody/tr/td")

            for i in range(0, len(cells), 2):
                key = cells[i].xpath("./text()").get().strip(": \n")
                value = cells[i + 1].xpath("./text()").get()
                if value is None:
                    value = ""
                activity[key] = value.strip()

            case_activities.append(
                {
                    "description": activity["Event Desc"],
                    "date": activity["Activity Date"],
                    "comments": activity["Comments"],
                }
            )

        return case_activities[::-1]
