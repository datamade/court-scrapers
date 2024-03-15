CREATE TEMPORARY TABLE raw_plaintiff (
    plaintiff text NOT NULL,
    case_number text NOT NULL
);

-- noqa: disable=PRS
.mode csv
.import /dev/stdin raw_plaintiff
-- noqa: enable=PRS

INSERT INTO plaintiff(plaintiff, case_number)
SELECT plaintiff, case_number FROM raw_plaintiff
