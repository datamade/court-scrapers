CREATE TEMPORARY TABLE raw_case (
    attorney text,
    case_number text
);

.mode csv -- noqa
.import /dev/stdin raw_case -- noqa

DELETE FROM attorney
WHERE
    case_number IN (SELECT case_number FROM raw_case);

INSERT INTO attorney(attorney, case_number)
SELECT * FROM raw_case
