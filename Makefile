year:=$(shell date +%Y)
START_TIME:=$(shell export TZ=UTC; date -Iseconds)
TIME_LIMIT=19800

# Default subdivisions (all subdivisions)
DEFAULT_SUBDIVISIONS = 2 3 4 5 6 101 104 11 13 14 15 17 chancery probate

# Override subdivisions based on input
SUBDIVISIONS ?= $(DEFAULT_SUBDIVISIONS)

# Generate subdivision file names
SUBDIVISION_FILES = $(foreach file,$(SUBDIVISIONS),$(call parse_subdivision,$(file)))

define parse_subdivision
  $(if $(filter $(1),2 3 4 5 6 101 104 11 13 14 15 17),civil-$(1).jl,$(if $(filter $(1),chancery probate),$(1).jl,))
endef

.PHONY: all
all: upload

.PHONY: clean
clean:
	rm *.csv *.jl *.json

cases.zip : cases.db
	- rm -rf cases_csv
	mkdir cases_csv
	echo "select * from court_case" | sqlite3 -csv -header cases.db > cases_csv/court_case.csv
	echo "select * from plaintiff" | sqlite3 -csv -header cases.db > cases_csv/plaintiff.csv
	echo "select * from defendant" | sqlite3 -csv -header cases.db > cases_csv/defendant.csv
	echo "select * from attorney" | sqlite3 -csv -header cases.db > cases_csv/attorney.csv
	echo "select * from event" | sqlite3 -csv -header cases.db > cases_csv/event.csv
	zip -r $@ cases_csv

.PHONY: get_new_records
get_new_records: import_new_cases import_new_attorneys import_new_events import_new_plaintiffs import_new_defendants set_subdivisions

.PHONY: set_subdivisions
set_subdivisions: cases.db
	sqlite3 cases.db < scripts/subdivision.sql

.PHONY: import_new_%
import_new_%: new_%.csv cases.db
	cat $< | sqlite3 cases.db -init scripts/new_$*.sql -bail

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

cases.json : $(SUBDIVISION_FILES)
	cat $^ | sort | python scripts/remove_dupe_cases.py | jq --slurp '.' > $@

# Query parameterized by civil case subdivision
CASE_SCRAPE_START_QUERY=$(shell cat scripts/nightly_case_start.sql)

civil-%.jl: cases.db
	START=$$(sqlite-utils query --csv --no-headers cases.db \
	      "$(CASE_SCRAPE_START_QUERY)" -p subdivision $* \
	      -p court civil -p year $(year)) \
	      export START_TIME=$(START_TIME); export TIME_LIMIT=$(TIME_LIMIT); \
	      scrapy crawl civil -s CLOSESPIDER_TIMEOUT=3600 -a year=$(year) -a division=$* -a start=$$START -O $@;

chancery.jl: cases.db
	START=$$(sqlite-utils query --csv --no-headers cases.db \
	      "$(CASE_SCRAPE_START_QUERY)" -p subdivision null \
	      -p court chancery -p year $(year)) \
	      export START_TIME=$(START_TIME); export TIME_LIMIT=$(TIME_LIMIT); \
	      scrapy crawl chancery -a year=$(year) -a start=$$START -O $@;

probate.jl: cases.db
	START=$$(sqlite-utils query --csv --no-headers cases.db \
	      "$(CASE_SCRAPE_START_QUERY)" -p court probate \
	      -p subdivision P -p year $(year)); \
	      export START_TIME=$(START_TIME); export TIME_LIMIT=$(TIME_LIMIT); \
	      scrapy crawl probate -a year=$(year) -a start=$$START -O $@;

cases.db :
	sqlite3 $@ < scripts/initialize_db.sql

.PHONY : upload
upload : 2022_civil.json
	python scripts/upload_scrapes.py
