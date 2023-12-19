CREATE TEMPORARY TABLE raw_attorney (
    attorney text,
    case_number text
);

-- noqa: disable=PRS
.mode csv
.import /dev/stdin raw_attorney
-- noqa: enable=PRS

INSERT INTO attorney(attorney, case_number)
SELECT attorney, case_number FROM raw_attorney
