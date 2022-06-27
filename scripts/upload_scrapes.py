import os
from datetime import datetime

import boto3


def main():
    client = boto3.client('s3')

    scrapes_dir = 'courtscraper/scrape'
    for file in os.listdir(scrapes_dir):
        if file == '.gitkeep':
            continue

        client.upload_file(os.path.abspath(f'{scrapes_dir}/{file}'), 'court-scrapers', f'{file}')

if __name__ == '__main__':
    main()

