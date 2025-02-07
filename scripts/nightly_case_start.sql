/* Query to find the serial number of the last case added to the database */
WITH
serials AS (
    SELECT
        case_number,
        CASE
            WHEN subdivision IS NOT NULL
                THEN
                    (
                        substring(
                            case_number,
                            5 + length(subdivision),
                            7 - length(subdivision)
                        )
                    )
            ELSE (substring(case_number, 7, 5))
        END AS serial,
        subdivision
    FROM court_case
    WHERE
        court = :court /* noqa */
        AND (
            CASE
                WHEN court IN ('civil', 'probate')
                    THEN subdivision = :subdivision /* noqa */
                ELSE 1
            END
        )
	AND substr(case_number, 1, 4) = strftime(:year, current_timestamp)
)

/* If we don't have any cases for the current year, start from zero */
SELECT coalesce((SELECT serial FROM serials ORDER BY -serial LIMIT 1), 0);
