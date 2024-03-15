CREATE TEMPORARY TABLE raw_events (
    description text,
    date text NOT NULL,
    comments text,
    case_number text NOT NULL
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
