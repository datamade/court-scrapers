CREATE TEMPORARY TABLE raw_attorney (
    attorney text NOT NULL,
    case_number text NOT NULL
);

-- noqa: disable=PRS
.mode csv
.import /dev/stdin raw_attorney
-- noqa: enable=PRS

INSERT INTO attorney(attorney, case_number)
SELECT attorney, case_number FROM raw_attorney
