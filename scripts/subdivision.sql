UPDATE
    court_case
SET
    subdivision = CASE
    WHEN substr(case_number, 5, 1) = '1' THEN
        CASE WHEN substr(case_number, 5, 2) = '10' THEN
            substr(case_number, 5, 3)
        ELSE
            substr(case_number, 5, 2)
        END
END;

