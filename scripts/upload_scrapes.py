import pathlib
from datetime import datetime

import boto3


def main():
    client = boto3.client('s3')

    scrapes_dir = pathlib.Path('scrape')
    for file in scrapes_dir.glob('*.json'):

        client.upload_file(file.absolute(), 'court-scrapers', file.name)

if __name__ == '__main__':
    main()

