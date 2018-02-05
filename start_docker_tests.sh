#!/bin/sh


docker build -f Dockerfile-py3 -t iottly-sdk-test .

docker run -it iottly-sdk-test /test/tests_runner.sh
