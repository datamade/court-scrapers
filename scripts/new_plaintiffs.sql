CREATE TEMPORARY TABLE raw_plaintiff (
    plaintiff text NOT NULL,
    case_number text NOT NULL,
    court text NOT NULL
);

-- noqa: disable=PRS
.mode csv
.import /dev/stdin raw_plaintiff
-- noqa: enable=PRS

INSERT INTO plaintiff(plaintiff, case_number, court)
SELECT plaintiff, case_number, court FROM raw_plaintiff
