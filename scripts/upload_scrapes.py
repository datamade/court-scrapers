import os
import os
from datetime import datetime

import boto3
from dotenv import dotenv_values


def main():
    key_id, access_key = dotenv_values(".env").values()
    client = boto3.client('s3',
        aws_access_key_id=key_id,
        aws_secret_access_key=access_key
    )

    scrapes_dir = 'courtscraper/scrape'
    for file in os.listdir(scrapes_dir):
        if file == '.gitkeep':
            continue

        client.upload_file(os.path.abspath(f'{scrapes_dir}/{file}'), 'court-scrapers', f'{file}')

if __name__ == '__main__':
    main()

