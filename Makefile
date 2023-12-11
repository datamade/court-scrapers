DB=cases.db

.INTERMEDIATE: *.csv *.jl *.json

.PHONY: all
all: upload

.PHONY: clean
clean:
	rm $(DB)

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
get_new_records: import_new_cases import_new_attorneys import_new_events import_new_plaintiffs import_new_defendants

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

cases.json : 2022_civil.jl 2023_civil.jl 2022_chancery.jl 2023_chancery.jl
	cat $^ | sort | python scripts/remove_dupe_cases.py | jq --slurp '.' > $@

%_civil.jl : %_civil-2.jl %_civil-3.jl %_civil-4.jl %_civil-5.jl	\
             %_civil-6.jl %_civil-101.jl %_civil-104.jl %_civil-11.jl	\
             %_civil-13.jl %_civil-14.jl %_civil-15.jl %_civil-17.jl
	cat $^ > $@

2022_chancery.jl :
	 scrapy crawl chancery -a year=2022 -O $@

2023_chancery.jl :
	 scrapy crawl chancery -a year=2023 -O $@

2022_civil-%.jl :
	 scrapy crawl civil -a division=$* -a year=2022 -O $@

2023_civil-%.jl :
	 scrapy crawl civil -a division=$* -a year=2023 -O $@

cases.db :
	sqlite3 $@ < scripts/initialize_db.sql

.PHONY : upload
upload : 2022_civil.json
	python scripts/upload_scrapes.py
