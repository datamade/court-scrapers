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

-- Normalize event dates to ISO format
UPDATE raw_events
SET
    date
    = substr(date, -4, 4)
    || "-"
    || substr(date, 1, 2)
    || "-"
    || substr(date, 4, 2)
WHERE date LIKE "__/__/____";

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
