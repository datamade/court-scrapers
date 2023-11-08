.PHONY: all
all: upload

cases.zip : cases.db
	- rm -rf cases_csv
	mkdir cases_csv
	echo "select * from court_case" | sqlite3 -csv -header cases.db > cases_csv/court_case.csv
	echo "select * from plaintiff" | sqlite3 -csv -header cases.db > cases_csv/plaintiff.csv
	echo "select * from defendant" | sqlite3 -csv -header cases.db > cases_csv/defendant.csv
	echo "select * from attorney" | sqlite3 -csv -header cases.db > cases_csv/attorney.csv
	echo "select * from event" | sqlite3 -csv -header cases.db > cases_csv/event.csv
	zip -r $@ cases_csv

cases.db : attorney.csv defendant.csv plaintiff.csv court_case.csv event.csv
	csvs-to-sqlite $^ $@
	cat scripts/foreign_key.sql | sqlite3 $@
	sqlite-utils add-column $@ court_case subdivision text
	sqlite3 $@ < scripts/subdivision.sql
	sqlite-utils transform $@ court_case \
            --drop _key \
            --pk case_number \
            --column-order case_number \
            --column-order filing_date \
            --column-order division \
            --column-order subdivision \
            --column-order case_type \
            --column-order calendar \
            --column-order ad_damnum
	sqlite-utils add-foreign-keys $@ \
            attorney case_number court_case case_number \
            defendant case_number court_case case_number \
            plaintiff case_number court_case case_number \
            event case_number court_case case_number
	sqlite-utils transform $@ defendant \
            --rename _key order \
            --column-order case_number \
            --column-order order \
            --column-order defendant
	sqlite-utils transform $@ attorney \
            --rename _key order \
            --column-order case_number \
            --column-order order \
            --column-order attorney
	sqlite-utils transform $@ event \
            --rename _key order \
            --column-order case_number \
            --column-order order \
            --column-order date \
            --column-order description \
            --column-order comments
	sqlite-utils transform $@ plaintiff \
            --rename _key order \
            --column-order case_number \
            --column-order order \
            --column-order plaintiff
	sqlite-utils convert $@ court_case filing_date 'r.parsedate(value)'
	sqlite-utils convert $@ event date 'r.parsedate(value)'

%.csv: court_case_raw.%.csv
	cat $< | \
           sed '1s/court_case_raw\._key/case_number/g' | \
           sed -r '1s/[a-z0-9_]+\.//g' > $@

court_case.csv : court_case_raw.csv
	cat $< | sed -r '1s/[a-z0-9_]+\.//g' > $@

court_case_raw.attorney.csv court_case_raw.defendant.csv court_case_raw.plaintiff.csv court_case_raw.csv court_case_raw.event.csv : cases.json
	perl json-to-multicsv.pl --file $< \
            --path /:table:court_case_raw \
            --path /*/events/:table:event \
            --path /*/plaintiffs/:table:plaintiff \
            --path /*/defendants/:table:defendant \
            --path /*/attorneys/:table:attorney

# cases.json : 2022_civil.jl 2023_civil.jl 2022_chancery.jl 2023_chancery.jl
cases.json : 2022_civil.jl
	cat $^ | sort | python scripts/remove_dupe_cases.py | jq --slurp '.' > $@

%_civil.jl : %_civil-2.jl
	cat $^ > $@

# %_civil.jl : %_civil-2.jl %_civil-3.jl %_civil-4.jl %_civil-5.jl	\
#              %_civil-6.jl %_civil-101.jl %_civil-104.jl %_civil-11.jl	\
#              %_civil-13.jl %_civil-14.jl %_civil-15.jl %_civil-17.jl
# 	cat $^ > $@

2022_chancery-%.jl :
	 scrapy crawl civil -a year=2022 -O $@

2023_chancery-%.jl :
	 scrapy crawl civil -a year=2023 -O $@

2022_civil-%.jl :
	 scrapy crawl civil -a division=$* -a year=2022 -O $@

2023_civil-%.jl :
	 scrapy crawl civil -a division=$* -a year=2023 -O $@

.PHONY : upload
upload : 2022_civil.json
	python scripts/upload_scrapes.py
