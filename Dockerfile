FROM python:3.12-slim-bookworm

LABEL maintainer "DataMade <info@datamade.us>"

RUN apt-get update && \
	apt-get install -y --no-install-recommends curl make sqlite3 gnupg2 jq zip unzip

# Install Heroku
RUN curl https://cli-assets.heroku.com/install-ubuntu.sh | sh

RUN heroku plugins:install heroku-builds

RUN mkdir /app
WORKDIR /app

RUN apt-get install -y gcc

# Install Python requirements
COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

RUN apt remove -y gcc

# Install Datasette plugins
RUN datasette install datasette-auth-passwords datasette-auth-tokens

COPY . /app
