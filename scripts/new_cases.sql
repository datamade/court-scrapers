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
  scraped_at,
  updated_at
FROM
  raw_case;
