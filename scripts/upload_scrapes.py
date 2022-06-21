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

    breakpoint()

    with open('data/artifact_1.txt', 'w') as f:
        f.write(f'Hello from... ({datetime.today().isoformat()})')

    with open('data/artifact_2.txt', 'w') as f:
        f.write(f'...an artifact! ({datetime.today().isoformat()})')

    client.upload_file(os.path.abspath('data/artifact_1.txt'), 'court-scrapers', 'artifact_1.txt')
    client.upload_file(os.path.abspath('data/artifact_2.txt'), 'court-scrapers', 'artifact_2.txt')


if __name__ == '__main__':
    main()

