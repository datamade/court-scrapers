BEGIN TRANSACTION;

PRAGMA foreign_keys = OFF;

-- Create a new court case table with a composite key
-- noqa: disable=PRS
CREATE TABLE new_court_case (
  case_number not null,
  filing_date text not null,
  division text not null,
  subdivision text,
  case_type text not null,
  calendar text not null,
  ad_damnum text not null,
  court text,
  hash text,
  scraped_at text default CURRENT_TIMESTAMP,
  updated_at text default CURRENT_TIMESTAMP,
  PRIMARY KEY (case_number, court) -- Define composite key here
);
-- noqa: enable=PRS

-- Copy data from the old table to the new table
INSERT INTO
  new_court_case (
    case_number,
    filing_date,
    division,
    subdivision,
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
  subdivision,
  case_type,
  calendar,
  ad_damnum,
  court,
  hash,
  scraped_at,
  updated_at
FROM
  court_case;

-- Drop the old table
  DROP TABLE court_case;

-- Rename the new table to the old table's name
ALTER TABLE
  new_court_case RENAME TO court_case;

-- Repeat for plaintiff table
ALTER TABLE
  plaintiff
ADD
  COLUMN court;

UPDATE
  plaintiff
SET
  court = court_case.court
FROM
  court_case
WHERE
  court_case.case_number = plaintiff.case_number;

CREATE TABLE new_plaintiff (
    case_number text not null,
    court text not null,
    plaintiff text,
    FOREIGN KEY(case_number, court) REFERENCES court_case(case_number, court)
  );

INSERT INTO
  new_plaintiff (case_number, court, plaintiff)
SELECT
  case_number,
  court,
  plaintiff
FROM
  plaintiff;

DROP TABLE plaintiff;

ALTER TABLE
  new_plaintiff RENAME TO plaintiff;

-- Repeat for defendant table
ALTER TABLE
  defendant
ADD
  COLUMN court;

UPDATE
  defendant
SET
  court = court_case.court
FROM
  court_case
WHERE
  court_case.case_number = defendant.case_number;

CREATE TABLE new_defendant (
    case_number text not null,
    court text not null,
    defendant text,
    FOREIGN KEY(case_number, court) REFERENCES court_case(case_number, court)
  );

INSERT INTO
  new_defendant (case_number, court, defendant)
SELECT
  case_number,
  court,
  defendant
FROM
  defendant;

DROP TABLE defendant;

ALTER TABLE
  new_defendant RENAME TO defendant;

-- Repeat for attorney table
ALTER TABLE
  attorney
ADD
  COLUMN court;

UPDATE
  attorney
SET
  court = court_case.court
FROM
  court_case
WHERE
  court_case.case_number = attorney.case_number;

CREATE TABLE new_attorney (
    case_number text not null,
    court text not null,
    attorney text,
    FOREIGN KEY(case_number, court) REFERENCES court_case(case_number, court)
  );

INSERT INTO
  new_attorney (case_number, court, attorney)
SELECT
  case_number,
  court,
  attorney
FROM
  attorney;

DROP TABLE attorney;

ALTER TABLE
  new_attorney RENAME TO attorney;

-- Repeat for event table
ALTER TABLE
  event
ADD
  COLUMN court;

UPDATE
  event
SET
  court = court_case.court
FROM
  court_case
WHERE
  court_case.case_number = event.case_number;

CREATE TABLE new_event (
    case_number text not null,
    court text not null,
    date text not null,
    description text,
    comments text,
    FOREIGN KEY(case_number, court) REFERENCES court_case(case_number, court)
  );

INSERT INTO
  new_event (case_number, court, date, description, comments)
SELECT
  case_number,
  court,
  date,
  description,
  comments
FROM
  event;

DROP TABLE event;

ALTER TABLE
  new_event RENAME TO event;

-- Remove the foreign key constraint for court_call
  CREATE TABLE new_court_call (
    case_number text not null,
    division,
    plaintiff,
    defendant,
    calendar,
    court_date,
    room,
    district,
    sequence,
    time,
    call_type,
    hash
  );

INSERT INTO
  new_court_call (
    case_number,
    division,
    plaintiff,
    defendant,
    calendar,
    court_date,
    room,
    district,
    sequence,
    time,
    call_type,
    hash
  )
SELECT
  case_number,
  division,
  plaintiff,
  defendant,
  calendar,
  court_date,
  room,
  district,
  sequence,
  time,
  call_type,
  hash
FROM
  court_call;

DROP TABLE court_call;

ALTER TABLE
  new_court_call RENAME TO court_call;

PRAGMA foreign_key_check;

PRAGMA foreign_keys = ON;

COMMIT;
