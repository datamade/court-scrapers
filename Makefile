
.PHONY: all
all: upload

.PHONY : scrape
scrape :
	python courtscraper/probate.py 100


.PHONY : upload
upload : scrape
	python scripts/upload_scrapes.py	
