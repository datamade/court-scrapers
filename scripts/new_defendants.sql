CREATE TEMPORARY TABLE raw_defendant (
    defendant text NOT NULL,
    case_number text NOT NULL,
    court text NOT NULL
);

-- noqa: disable=PRS
.mode csv
.import /dev/stdin raw_defendant
-- noqa: enable=PRS

INSERT INTO defendant(defendant, case_number, court)
SELECT defendant, case_number, court FROM raw_defendant
