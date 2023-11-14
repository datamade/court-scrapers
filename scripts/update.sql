-- Given a CSV of re-scraped cases, update the matching cases in the database
CREATE TEMPORARY TABLE raw_case (
        ad_damnum text,
        calendar text,
        case_number text,
        case_type text,
        court text,
        division text,
        filing_date text,
        hash text,
        scraped_at text,
        updated_at text
);

.mode csv
.import /dev/stdin raw_case

-- Update cases that have changed (i.e. their hashes are different)
UPDATE court_case
SET calendar = raw_case.calendar,
filing_date = raw_case.filing_date,
division = raw_case.division,
case_type = raw_case.case_type,
ad_damnum = raw_case.ad_damnum,
court = raw_case.court,
hash = raw_case.hash,
scraped_at = raw_case.scraped_at,
updated_at = raw_case.scraped_at
FROM raw_case
WHERE court_case.case_number = raw_case.case_number and court_case.hash != raw_case.hash;

-- For cases that haven't changed, just update their scraped_at field
UPDATE court_case
SET scraped_at = raw_case.scraped_at
from raw_case
where court_case.case_number = raw_case.case_number and court_case.hash = raw_case.hash;
