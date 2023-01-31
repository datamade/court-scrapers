.PHONY: all
all: upload

.PHONY : scrape
scrape :
	python courtscraper/probate.py --number_of_cases 10

.PHONY : upload
upload : scrape
	python scripts/upload_scrapes.py	
