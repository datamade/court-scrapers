ATTACH DATABASE 'cases.db' AS cases; -- noqa

-- Temporary table to hold updated cases
-- i.e. cases whose hashes have changed
CREATE TEMPORARY TABLE updated_case(num text);
INSERT INTO
  updated_case
SELECT
  a.case_number
FROM
  court_case as a
  LEFT JOIN cases.court_case as b ON a.case_number = b.case_number
WHERE
  a.hash != b.hash;

UPDATE cases.court_case
SET
    calendar = r.calendar,
    filing_date = r.filing_date,
    division = r.division,
    case_type = r.case_type,
    ad_damnum = r.ad_damnum,
    court = r.court,
    hash = r.hash,
    scraped_at = CURRENT_TIMESTAMP,
    updated_at = CURRENT_TIMESTAMP
FROM court_case as r
WHERE
    court_case.case_number IN (SELECT * FROM updated_case);

-- Update related attorneys
DELETE FROM cases.attorney
WHERE
    case_number IN (SELECT * FROM updated_case);

INSERT INTO cases.attorney
SELECT * FROM attorney
WHERE
    case_number IN (SELECT * FROM updated_case);

-- Update related defendants
DELETE FROM cases.defendant
WHERE
    case_number IN (SELECT * FROM updated_case);

INSERT INTO cases.defendant
SELECT * FROM defendant
WHERE
    case_number IN (SELECT * FROM updated_case);

-- Update related events
DELETE FROM cases.event
WHERE
    case_number IN (SELECT * FROM updated_case);

INSERT INTO cases.event
SELECT * FROM event
WHERE
    case_number IN (SELECT * FROM updated_case);

-- Update related plaintiffs
DELETE FROM cases.plaintiff
WHERE
    case_number IN (SELECT * FROM updated_case);

INSERT INTO cases.plaintiff
SELECT * FROM plaintiff
WHERE
    case_number IN (SELECT * FROM updated_case);

-- For cases that haven't changed, just update their scraped_at field
UPDATE cases.court_case
SET scraped_at = CURRENT_TIMESTAMP
WHERE
    case_number NOT IN (SELECT * FROM updated_case);
