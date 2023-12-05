CREATE TEMPORARY TABLE raw_case (
    description text,
    date text, -- noqa
    comments text,
    case_number text
);

.mode csv -- noqa
.import /dev/stdin raw_case -- noqa

DELETE FROM event
WHERE
    case_number IN (SELECT case_number FROM raw_case);

INSERT INTO event(description, date, comments, case_number)
SELECT * FROM raw_case
