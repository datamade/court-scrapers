-- Query to find the serial number of the last chancery case
-- added to the database

WITH serials AS (
    SELECT
        case_number,
        (
            substring(
                case_number,
                7,
                5
            )
        ) AS serial
    FROM
        court_case
    WHERE
        court = 'chancery'
        AND substr(case_number, 1, 4) = strftime('%Y', current_timestamp)
)

SELECT serial
FROM
    serials
ORDER BY
    -serial
LIMIT
    1;
