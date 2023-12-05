CREATE TEMPORARY TABLE raw_case (
    defendant text,
    case_number text
);

.mode csv -- noqa
.import /dev/stdin raw_case -- noqa

DELETE FROM defendant
WHERE
    case_number IN (SELECT case_number FROM raw_case);

INSERT INTO defendant(defendant, case_number)
SELECT * FROM raw_case
