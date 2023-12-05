-- Given a CSV of re-scraped cases, update the matching cases in the database
CREATE TEMPORARY TABLE raw_case (
    ad_damnum text,
    calendar text,
    case_number text,
    case_type text,
    court text,
    division text,
    filing_date text,
    hash text
);

.mode csv -- noqa
.import /dev/stdin raw_case --noqa

-- Get a list of cases that need to be updated (i.e. their hashes are different)
SELECT court_case.case_number
FROM court_case
LEFT JOIN raw_case ON court_case.case_number = raw_case.case_number
WHERE
    court_case.hash != raw_case.hash;
