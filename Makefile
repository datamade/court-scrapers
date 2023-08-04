.PHONY: all
all: upload

2022_civil.json :
	 scrapy crawl civil -o $@

.PHONY : upload
upload : 2022_civil.json
	python scripts/upload_scrapes.py	
