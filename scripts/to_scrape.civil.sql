-- Generates a priority queue of cases to re-scrape
-- Inspired by Cho and Molina, Estimating Frequency of Change
-- https://citeseerx.ist.psu.edu/document?repid=rep1&type=pdf&doi=
-- 60c8e42055dfb80072a547c73fbc18dfbacc20aa

WITH
overall_rate AS (
    SELECT
        sum(
            1 / (julianday(scraped_at) - julianday(updated_at))
        ) / count(*) FILTER (
            WHERE julianday(scraped_at) > julianday(updated_at)
        ) AS rate,
        3 AS prior_weight
    FROM court_case
)

SELECT court_case.case_number
FROM court_case
INNER JOIN overall_rate ON 1 = 1
WHERE court_case.court = 'civil'
ORDER BY
    (
        (overall_rate.prior_weight + 1)
        / (
            overall_rate.prior_weight / overall_rate.rate
            + julianday(court_case.scraped_at)
            - julianday(court_case.updated_at)
        )
    )
    * (julianday('now') - julianday(court_case.scraped_at)) DESC
LIMIT 3000;
