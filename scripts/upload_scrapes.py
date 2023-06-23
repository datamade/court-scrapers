import pathlib

import tqdm
import boto3


def main():
    client = boto3.client('s3')

    scrapes_dir = pathlib.Path('scrape')
    for f in tqdm.tqdm(scrapes_dir.glob('*.json')):

        client.upload_file(str(f.absolute()), 'court-scrapers', f.name)

if __name__ == '__main__':
    main()

