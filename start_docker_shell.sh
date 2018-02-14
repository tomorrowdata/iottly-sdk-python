#!/bin/sh


docker build -f Dockerfile-py3-shell -t iottly-sdk-shell .

docker run -it -v `pwd`/examples:/mybeautifulapp iottly-sdk-shell sh

#docker run -it  \
#  -v `pwd`/iottlyagent_1.6.0_linux_AMD64.tar.gz:/tmp/iottlyagent_1.6.0_linux_AMD64.tar.gz \
#  -v `pwd`/examples:/mybeautifulapp \
#  iottly-sdk-shell \
#  sh
