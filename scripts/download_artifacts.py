import boto3


def main():
    client = boto3.client('s3')

    with open('artifact_1.txt', 'wb') as f:
        client.download_fileobj('court-scrapers', 'artifact_1.txt', f)

    with open('artifact_2.txt', 'wb') as f:
        client.download_fileobj('court-scrapers', 'artifact_2.txt', f)

    with open('artifact_1.txt') as f:
        print(f.read())

    with open('artifact_2.txt') as f:
        print(f.read())


if __name__ == '__main__':
    main()
