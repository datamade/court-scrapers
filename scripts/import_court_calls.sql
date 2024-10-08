CREATE TEMPORARY TABLE raw_court_call (
    case_number text,
    division text,
    plaintiff text,
    defendant text,
    court_date text,
    room text,
    district text,
    sequence text,
    calendar text,
    time text,
    call_type text,
    hash text
);

-- noqa: disable=PRS
.mode csv
.import /dev/stdin raw_court_call
-- noqa: enable=PRS

-- Find and insert the new court calls
INSERT INTO
  court_call(
    case_number,
    division,
    plaintiff,
    defendant,
    court_date,
    room,
    district,
    sequence,
    calendar,
    time,
    call_type,
    hash
  )
SELECT
  case_number,
  division,
  plaintiff,
  defendant,
  court_date,
  room,
  district,
  sequence,
  calendar,
  time,
  call_type,
  hash
FROM
  raw_court_call
WHERE raw_court_call.hash NOT IN (SELECT hash FROM court_call);
