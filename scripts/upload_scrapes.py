import boto3
import os
from datetime import datetime


def main():
    client = boto3.client('s3')

    with open('data/artifact_1.txt', 'w') as f:
        f.write(f'Hello from... ({datetime.today().isoformat()})')

    with open('data/artifact_2.txt', 'w') as f:
        f.write(f'...an artifact! ({datetime.today().isoformat()})')

    client.upload_file(os.path.abspath('data/artifact_1.txt'), 'court-scrapers', 'artifact_1.txt')
    client.upload_file(os.path.abspath('data/artifact_2.txt'), 'court-scrapers', 'artifact_2.txt')


if __name__ == '__main__':
    main()

