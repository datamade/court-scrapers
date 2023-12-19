-- Query to find the serial number of the last civil case added to the database

WITH serials AS (
    SELECT
        case_number,
        (
            substring(
                case_number,
                5 + length(subdivision),
                7 - length(subdivision)
            )
        ) AS serial
    FROM
        court_case
    WHERE
        court = 'civil'
        -- noqa: disable=all
        AND subdivision = :subdivision
        -- noqa: enable=all
        AND substr(case_number, 1, 4) = strftime('%Y', current_timestamp)
)

SELECT serial
FROM
    serials
ORDER BY
    -serial
LIMIT
    1;
