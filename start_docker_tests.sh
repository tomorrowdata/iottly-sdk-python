#!/bin/sh

dockerfile='Dockerfile-py3'

if [ $# -eq 1 ]; then
  dockerfile=$1
fi


docker build -f $dockerfile -t iottly-sdk-test .

docker run -it iottly-sdk-test /test/tests_runner.sh
