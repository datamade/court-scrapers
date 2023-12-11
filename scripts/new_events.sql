CREATE TEMPORARY TABLE raw_events (
    description text,
    date text,
    comments text,
    case_number text
);

-- noqa: disable=PRS
.mode csv
.import /dev/stdin raw_events
-- noqa: enable=PRS

INSERT INTO
  event(
    description,
    date,
    comments,
    case_number
  )
SELECT
    description,
    date,
    comments,
    case_number
FROM
  raw_events;
