UPDATE plaintiff SET case_number = court_case.case_number



FROM court_case
WHERE plaintiff.case_number = court_case._key;

UPDATE attorney SET case_number = court_case.case_number
FROM court_case
WHERE attorney.case_number = court_case._key;

UPDATE defendant SET case_number = court_case.case_number
FROM court_case
WHERE defendant.case_number = court_case._key;

UPDATE event SET case_number = court_case.case_number
FROM court_case
WHERE event.case_number = court_case._key;
