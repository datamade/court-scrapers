import requests
import lxml.html
import mechanize
import re

import datetime
import json
from dateutil.rrule import rrule, DAILY

class CivilScraper:
    base_url = 'https://casesearch.cookcountyclerkofcourt.org/DocketSearch.aspx'

    def __init__(self):
        self.br = mechanize.Browser()
        self.br.addheaders = [('User-agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1')]
        self.br.set_handle_robots(False)

    def initialize_date_search(self, url, br, date_str):
        response = br.open(url)
        br.select_form(id='ctl01')
        br.set_all_readonly(False)

        # Select the filing date radio button
        br.find_control(name='ctl00$MainContent$rbSearchType')\
          .get(id='MainContent_rbSearchType_1').selected = True

        # Manually update event target, spoofing JavaScript callback
        br['__EVENTTARGET'] = 'ctl00$MainContent$rbSearchType$1'

        # Remove unneeded values
        br.form.clear('ctl00$MainContent$txtCaseYear')
        br.form.clear('ctl00$MainContent$txtCaseNumber')
        br.form.clear('ctl00$MainContent$btnSearch')

        # Submit the form
        br.submit()

        br.select_form(id='ctl01')
        br.set_all_readonly(False)

        # Specify the division to search
        br['ctl00$MainContent$ddlDatabase'] = ['1',]

        # Specify the date to search
        br['ctl00$MainContent$dtTxt'] = date_str

        response = br.submit().read().decode('utf-8')

        result_tree = lxml.html.fromstring(response)

        try:
            return result_tree.xpath(".//table[@id='MainContent_gvResults']")[0]
        except ValueError:
            return

    def get_search_results(self, table):
        table_rows = table.xpath('.//tr')
        assert len(table_rows) < 1000
        cases = []

        for row in table_rows[1:]:
            cells = row.xpath('.//td/text()')

            case_data = {
                'name': '',
                'case_number': '',
                'division': '',
                'party_type': '',
                'case_type': '',
                'date_filed': '',
                'case_url': ''
            }

            case_data['name'] = cells[0]
            case_data['case_number'] = cells[3]
            case_data['division'] = cells[4]
            case_data['party_type'] = cells[5]
            case_data['case_type'] = cells[6]
            case_data['date_filed'] = cells[7]

            # Build the case url
            case_num = case_data['case_number']
            url_beginning = 'https://courtlink.lexisnexis.com/cookcounty/FindDock.aspx?NCase='
            url_end = '&SearchType=0&Database=1&case_no=&PLtype=1&sname=&CDate='

            if case_num[4].isdigit():
                # If the character after the year in case number 
                # is numeric, build url with an M attached
                url_case_num = case_num[:4]+'-M' + case_num[4] + '-' + case_num[5:]

                case_data['case_url'] = url_beginning + url_case_num + url_end
                
            else:
                # Use the whole number as is
                case_data['case_url'] = url_beginning + case_num + url_end

            cases.append(case_data)

        return cases

    def clean_whitespace(self, text):
        return re.sub('\s+', ' ', text.text_content()).strip()

    def get_case_details(self, tree):
        result = {}

        # Accessing past the first gives repeat info
        case_details, = tree.xpath(".//div[@id='objCaseDetails']/table[1]")
        
        first_column = case_details.xpath(".//tr/td[1]")
        for row in first_column:
            clean_row = self.clean_whitespace(row)
            row_list = clean_row.split(':')

            key = row_list[0]
            value = row_list[1].strip()

            result[key] = value

        last_column = case_details.xpath(".//tr/td[3]")
        for row in last_column:
            clean_row = self.clean_whitespace(row)
            row_list = clean_row.split(':')

            key = row_list[0]
            value = row_list[1].strip()
            
            result[key] = value

        return result

    def get_party_information(self, tree):
        party_information, = tree.xpath(".//div[@id='objCaseDetails']//table[2]")
        
        plaintiffs = []
        defendants = []
        is_defendant = False
        
        first_column = party_information.xpath(".//tr/td[1]")
        for row in first_column[1:]:
            clean_row = self.clean_whitespace(row)
            person = {
                'name': ''
            } 

            # When reaching the row that says defendants, put following
            # names in the defendants list
            if is_defendant == True:
                person['name'] = clean_row
                defendants.append(person)
            elif clean_row == 'Defendant(s)':
                is_defendant = True
            else:
                person['name'] = clean_row
                plaintiffs.append(person)
        
        defendants_index = 0
        is_defendant = False

        last_column = party_information.xpath(".//tr/td[3]")
        for i, row in enumerate(last_column[1:]):
            clean_row = self.clean_whitespace(row)
            attorney = ''    

            # Assign the attorney to plaintiffs
            # until the str 'Attorney(s)' is found
            # then add the rest to defendants
            if is_defendant == True:
                attorney = clean_row
                defendants[defendants_index]['attorney'] = attorney
                defendants_index += 1
            elif clean_row == 'Attorney(s)':
                is_defendant = True
            else:
                attorney = clean_row
                plaintiffs[i]['attorney'] = attorney
        
        result = {
            'plaintiffs': plaintiffs,
            'defendants': defendants
        }

        return result

    def get_case_activity(self, tree):
        case_activity = tree.xpath(".//div[@id='objCaseDetails']/table[position() >= 3]")
        
        activities_list = []
        for i, row in enumerate(case_activity):
            result = { 
                'Date': '',
                'Participant': '',
                'Activity': '',
            }

            # Perform on every other table so we can organize related
            # info from the current table and the next one, in one dict
            if i % 2 == 0:
                # TODO: clean up var names to make them more readable?

                # Even tables
                activity_meta = row.xpath('.//td')
                date = self.clean_whitespace(activity_meta[0])
                date = date.split(':')[1].strip()
                result['Date'] = date

                participant = self.clean_whitespace(activity_meta[1])
                participant = participant.split(':')[1].strip()
                result['Participant'] = participant

                # Odd tables
                activity_overview = case_activity[i+1].xpath('./tr')
                activity_type = self.clean_whitespace(activity_overview[0])
                activity_details = case_activity[i+1].xpath('./tr[2]//tr')

                new_activity = {
                    'Type': activity_type,
                }
                
                for item in activity_details:
                    row = self.clean_whitespace(item)
                    
                    if row != '':
                        row = row.split(':')
                        detail_type = row[0]
                        detail_value = row[1].strip()
                        new_activity[detail_type] = detail_value

                result['Activity'] = new_activity
                activities_list.append(result)
        #TODO: change this to a yield possibly
        return activities_list

    def scrape_day(self, date_str):
        result_table = self.initialize_date_search(self.base_url, self.br, date_str)
        cases_list = self.get_search_results(result_table)

        for case in cases_list:
            url = case['case_url']
            response = self.br.open(url).read().decode('utf-8')
            result_tree = lxml.html.fromstring(response)

            case_dict = {
                'case_number': case['case_number'],
                'case_details': {},
                'party_information': {},
                'case_activity': []
            }

            case_dict['case_details'] = self.get_case_details(result_tree)
            case_dict['party_information'] = self.get_party_information(result_tree)
            case_dict['case_activity'] = self.get_case_activity(result_tree)
            yield case_dict

    def scrape(self, begin_date, end_date):
        begin_date_values = begin_date.split('-')
        for i, value in enumerate(begin_date_values):
            begin_date_values[i] = int(value.lstrip('0'))
        
        end_date_values = end_date.split('-')
        for i, value in enumerate(end_date_values):
            end_date_values[i] = int(value.lstrip('0'))


        weekdays = rrule(
            DAILY,
            dtstart=datetime.date(*begin_date_values),
            until=datetime.date(*end_date_values),
            byweekday=[0, 1, 2, 3, 4]
        )

        for day in weekdays:
            for case in self.scrape_day(str(day)):
                yield case

scraper = CivilScraper()
for case in scraper.scrape('2022-10-04', '2022-10-11'):
    case_number = case['case_number']
    print('outputting case #:', case_number)
    
    file_path = f'./scrape/{case_number}.json'
    with open(file_path, 'w+') as output:
        json.dump(case, output, sort_keys=True, indent=4)
    print('done')




