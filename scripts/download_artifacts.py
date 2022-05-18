import boto3


def main():
    client = boto3.client('s3')

    client.download_file('court-scrapers', 'artifact_1.txt', 'artifact_1.txt')
    client.download_file('court-scrapers', 'artifact_2.txt', 'artifact_2.txt')

    with open('artifact_1.txt') as f:
        print(f.read())

    with open('artifact_2.txt') as f:
        print(f.read())


if __name__ == '__main__':
    main()
