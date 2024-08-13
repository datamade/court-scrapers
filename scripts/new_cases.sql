CREATE TEMPORARY TABLE raw_case (
    ad_damnum text NOT NULL,
    calendar text NOT NULL,
    case_number text NOT NULL,
    case_type text NOT NULL,
    court text NOT NULL,
    division text NOT NULL,
    filing_date text NOT NULL,
    hash text NOT NULL,
    scraped_at text DEFAULT current_timestamp,
    updated_at text DEFAULT current_timestamp
);

-- noqa: disable=PRS
.mode csv
.import /dev/stdin raw_case
-- noqa: enable=PRS

-- Normalize filing dates to ISO format
UPDATE raw_case
SET
    filing_date
    = substr(filing_date, -4, 4)
    || "-"
    || substr(filing_date, 1, 2)
    || "-"
    || substr(filing_date, 4, 2)
WHERE filing_date LIKE "__/__/____";

INSERT INTO
  court_case(
    case_number,
    filing_date,
    division,
    case_type,
    calendar,
    ad_damnum,
    court,
    hash,
    scraped_at,
    updated_at
  )
SELECT
  case_number,
  filing_date,
  division,
  case_type,
  calendar,
  ad_damnum,
  court,
  hash,
  current_timestamp,
  current_timestamp
FROM
  raw_case;
