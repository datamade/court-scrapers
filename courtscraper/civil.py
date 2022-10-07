import requests
import lxml.html
import mechanize

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


result_table = initialize_date_search(url, br, date_str)
cases_list = get_search_results(result_table)

for case in cases_list:
    url = case['case_url']

    response = br.open(url).read().decode('utf-8')
    result_tree = lxml.html.fromstring(response)

    case_details = result_tree.xpath(".//div[@id='objCaseDetails']//table[1]")
    # Accessing past the first gives repeat info
    print(case_details[0].text_content())
    print('case details printed')

    party_information = result_tree.xpath(".//div[@id='objCaseDetails']//table[2]")
    for field in party_information:
        print(field.text_content())
        print('party info printed')

    case_activity = result_tree.xpath(".//div[@id='objCaseDetails']//table[position() >= 3]")
    for field in case_activity:
        print(field.text_content())
        print('case activity printed')

    print('done')
    




