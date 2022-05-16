#!/bin/bash

get_job_id() {
  curl --globoff --header 'JOB-TOKEN: $CI_JOB_TOKEN' https://gitlab.com/api/v4/projects/36119029/jobs | jq 'first(.[] | select(.name == "job1").id)'
}

fetch_artifacts() {
  id=$1
  curl --output artifacts.zip --header "PRIVATE-TOKEN: $CI_JOB_TOKEN" https://gitlab.com/api/v4/projects/36119029/jobs/$id/artifacts
}

curl --globoff --header 'JOB-TOKEN: $CI_JOB_TOKEN' https://gitlab.com/api/v4/projects/36119029/jobs
job_id=$(get_job_id)
fetch_artifacts $job_id
unzip -j artifacts.zip
cat artifacts_1.txt
cat artifacts_2.txt

