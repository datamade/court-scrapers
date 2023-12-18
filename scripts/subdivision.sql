-- Populates the subdivision column in the court_case table

UPDATE
court_case
SET
    subdivision = CASE
        WHEN substr(case_number, 5, 1) = '1'
            THEN
                CASE WHEN substr(case_number, 5, 2) = '10'
                        THEN
                            substr(case_number, 5, 3)
                    ELSE
                        substr(case_number, 5, 2)
                END
        -- Chancery cases don't have subdivisions
        WHEN substr(case_number, 5, 1) != 'C' THEN
            substr(case_number, 5, 1)
    END
WHERE subdivision IS NULL;
