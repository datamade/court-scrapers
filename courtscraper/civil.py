import requests
import lxml.html
import mechanize
import re

url = 'https://casesearch.cookcountyclerkofcourt.org/DocketSearch.aspx'
date_str = '10/04/2022' # mm/dd/yyy
br = mechanize.Browser()
br.addheaders = [('User-agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1')]
br.set_handle_robots(False)

def initialize_date_search(url, br, date_str):
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

def get_search_results(table):
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

def clean_whitespace(text):
    return re.sub('\s+', ' ', text.text_content()).strip()

def get_case_details(tree):
    result = {}

    # Accessing past the first gives repeat info
    case_details, = tree.xpath(".//div[@id='objCaseDetails']/table[1]")
    
    first_column = case_details.xpath(".//tr/td[1]")
    for row in first_column:
        clean_row = clean_whitespace(row)
        row_list = clean_row.split(':')

        key = row_list[0]
        value = row_list[1].strip()

        result[key] = value

    last_column = case_details.xpath(".//tr/td[3]")
    for row in last_column:
        clean_row = clean_whitespace(row)
        row_list = clean_row.split(':')

        key = row_list[0]
        value = row_list[1].strip()
        
        result[key] = value

    return result

def get_party_information(tree):
    party_information, = tree.xpath(".//div[@id='objCaseDetails']//table[2]")
    
    plaintiffs = []
    defendants = []
    is_defendant = False
    
    first_column = party_information.xpath(".//tr/td[1]")
    for row in first_column[1:]:
        clean_row = clean_whitespace(row)
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
        clean_row = clean_whitespace(row)
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

def get_case_activity(tree):
    case_activity = tree.xpath(".//div[@id='objCaseDetails']/table[position() >= 3]")
    
    activities_list = []
    for i, row in enumerate(case_activity):
        result = { 
            'date': '',
            'participant': '',
            'activity': '',
        }

        # Perform on every other table so we can organize related
        # info from the current table and the next one, in one dict
        if i % 2 == 0:
            # TODO: clean up variable names to make them more readable?

            # Even tables
            activity_meta = row.xpath('.//td')
            date = clean_whitespace(activity_meta[0])
            date = date.split(':')[1].strip()
            result['date'] = date

            participant = clean_whitespace(activity_meta[1])
            participant = participant.split(':')[1].strip()
            result['participant'] = participant

            # Odd tables
            activity_details = case_activity[i+1].xpath('./tr')
            activity = clean_whitespace(activity_details[0])

            # This requires different formatting than other activities
            if activity == 'New Case Filing':
                new_case = {
                    'name': 'New Case Filing',
                }

                # Select the details in the new case filing
                new_case_details = case_activity[i+1].xpath('./tr[2]//tr')
                for item in new_case_details:
                    row = clean_whitespace(item)
                    row = row.split(':')
                    detail_type = row[0]
                    detail_value = row[1]

                    # The other activity types have attorney as a key
                    # in the root of the result, as opposed to in
                    # a new_case dict. This keeps that uniform.
                    if detail_type == 'Attorney':
                        result[detail_type] = detail_value
                    else:
                        new_case[detail_type] = detail_value

                result['activity'] = new_case
            else:
                result['activity'] = activity

                for item in activity_details[1:]:
                    row = clean_whitespace(item)

                    if row != '':
                        row = row.split(':')
                        detail_type = row[0]
                        detail_value = row[1].strip()
                        result[detail_type] = detail_value
                
            activities_list.append(result)
    return activities_list

result_table = initialize_date_search(url, br, date_str)
cases_list = get_search_results(result_table)

for case in cases_list:
    url = case['case_url']
    response = br.open(url).read().decode('utf-8')
    result_tree = lxml.html.fromstring(response)

    case_dict = {
        'case_details': {},
        'party_information': {},
        'case_activity': {}
    }

    case_dict['case_details'] = get_case_details(result_tree)
    case_dict['party_information'] = get_party_information(result_tree)
    case_dict['case_activity'] = get_case_activity(result_tree)
    for item in case_dict['case_activity']:
        print(item)

    print('done------------------')
    




