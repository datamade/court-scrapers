DB=cases.db

.INTERMEDIATE: *.csv *.jl *.json

.PHONY: all
all: upload

.PHONY: clean
clean:
	rm $(DB) *.csv *.jl *.json

cases.zip : $(DB)
	- rm -rf cases_csv
	mkdir cases_csv
	echo "select * from court_case" | sqlite3 -csv -header $(DB) > cases_csv/court_case.csv
	echo "select * from plaintiff" | sqlite3 -csv -header $(DB) > cases_csv/plaintiff.csv
	echo "select * from defendant" | sqlite3 -csv -header $(DB) > cases_csv/defendant.csv
	echo "select * from attorney" | sqlite3 -csv -header $(DB) > cases_csv/attorney.csv
	echo "select * from event" | sqlite3 -csv -header $(DB) > cases_csv/event.csv
	zip -r $@ cases_csv

.PHONY: get_new_records
get_new_records: import_new_cases import_new_attorneys import_new_events import_new_plaintiffs import_new_defendants set_subdivisions

.PHONY: set_subdivisions
set_subdivisions: $(DB)
	sqlite3 $(DB) < scripts/subdivision.sql

.PHONY: import_new_%
import_new_%: new_%.csv $(DB)
	cat $< | sqlite3 $(DB) -init scripts/new_$*.sql -bail

new_cases.csv: cases.json
	cat $^ | jq '.[] | [.ad_damnum, .calendar, .case_number, .case_type, .court, .division, .filing_date, .hash] | @csv' -r > $@

new_attorneys.csv: cases.json
	cat $^ | jq '.[] | . as $$p | .attorneys[] | [., $$p.case_number] | @csv' -r > $@

new_events.csv: cases.json
	cat $< | jq -r '.[] | .events[] + {case_number} | [.description, .date, .comments, .case_number] | @csv' > $@

new_plaintiffs.csv: cases.json
	cat $< | jq '.[] | . as $$p | .plaintiffs[] | [., $$p.case_number] | @csv' -r > $@

new_defendants.csv: cases.json
	cat $^ | jq '.[] | . as $$p | .defendants[] | [., $$p.case_number] | @csv' -r > $@

cases.json : civil-2.jl civil-3.jl civil-4.jl civil-5.jl	\
             civil-6.jl civil-101.jl civil-104.jl civil-11.jl	\
             civil-13.jl civil-14.jl civil-15.jl civil-17.jl chancery.jl
	cat $^ | sort | python scripts/remove_dupe_cases.py | jq --slurp '.' > $@

# Query parameterized by civil case subdivision
CIVIL_SCRAPE_START_QUERY=$(shell tail -n +2 scripts/nightly_civil_start.sql)

civil-%.jl: $(DB)
	START=$$(sqlite-utils query --csv --no-headers $(DB) \
	      "$(CIVIL_SCRAPE_START_QUERY)" -p subdivision $*); \
	      scrapy crawl civil -a division=$* -a start=$$START -O $@;

chancery.jl: $(DB)
	START=$$(sqlite3 $(DB) < scripts/nightly_chancery_start.sql); \
	      scrapy crawl chancery -a start=$$START -O $@;

cases.db :
	sqlite3 $@ < scripts/initialize_db.sql

.PHONY : upload
upload : 2022_civil.json
	python scripts/upload_scrapes.py
