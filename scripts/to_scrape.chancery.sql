-- Generates a priority queue of cases to re-scrape
-- Inspired by Cho and Molina, Estimating Frequency of Change
-- https://citeseerx.ist.psu.edu/document?repid=rep1&type=pdf&doi=60c8e42055dfb80072a547c73fbc18dfbacc20aa
WITH
overall_rate AS (
    SELECT
        sum(
            1 / (julianday(last_checked_at) - julianday(updated_at))
        ) / count(*) FILTER (
            WHERE julianday(last_checked_at) > julianday(updated_at)
        ) AS rate,
        3 AS prior_weight
    FROM court_case
)

SELECT case_number
FROM court_case
INNER JOIN overall_rate ON 1 = 1
WHERE court = "chancery"
ORDER BY
    ((prior_weight + 1) / (prior_weight / rate + julianday(last_checked_at) - julianday(updated_at)))
    * (julianday('now') - julianday(last_checked_at)) DESC
LIMIT 3000;
