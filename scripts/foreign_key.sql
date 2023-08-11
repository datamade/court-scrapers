update plaintiff set case_number = court_case.case_number from court_case where plaintiff.case_number = court_case._key;

update attorney set case_number = court_case.case_number from court_case where attorney.case_number = court_case._key;

update defendant set case_number = court_case.case_number from court_case where defendant.case_number = court_case._key;

update event set case_number = court_case.case_number from court_case where event.case_number = court_case._key;
