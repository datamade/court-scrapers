CREATE TEMPORARY TABLE raw_defendant (
    defendant text,
    case_number text
);

-- noqa: disable=PRS
.mode csv
.import /dev/stdin raw_defendant
-- noqa: enable=PRS

INSERT INTO defendant(defendant, case_number)
SELECT defendant, case_number FROM raw_defendant
