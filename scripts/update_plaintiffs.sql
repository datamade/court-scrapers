CREATE TEMPORARY TABLE raw_case (
    plaintiff text,
    case_number text
);

.mode csv -- noqa
.import /dev/stdin raw_case -- noqa

DELETE FROM plaintiff
WHERE
    case_number IN (SELECT case_number FROM raw_case);

INSERT INTO plaintiff(plaintiff, case_number)
SELECT * FROM raw_case
