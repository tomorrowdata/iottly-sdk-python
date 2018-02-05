#!/bin/sh


docker build -f Dockerfile-py3-shell -t iottly-sdk-shell .

docker run -it -v `pwd`/examples:/mybeautifulapp iottly-sdk-shell sh
