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
    print(response)
    result_tree = lxml.html.fromstring(response)

    try:
        return result_tree.xpath(".//table[@id='MainContent_gvResults']")[0]
    except ValueError:
        return

result = initialize_date_search(url, br, date_str)
	
