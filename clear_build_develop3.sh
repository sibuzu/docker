#!/bin/sh

sudo nvidia-docker build --no-cache -t sibuzu/base3 -f Dockerfile.base3 .
sudo nvidia-docker build --no-cache -t sibuzu/python3 -f Dockerfile.python3 .
sudo nvidia-docker build --no-cache -t sibuzu/jupyter3 -f Dockerfile.jupyter3 .
sudo nvidia-docker build --no-cache -t sibuzu/nodejs3 -f Dockerfile.nodejs3 .
sudo nvidia-docker build --no-cache -t sibuzu/sshd3 -f Dockerfile.sshd3 .
sudo nvidia-docker build --no-cache -t sibuzu/tensorflow3 -f Dockerfile.tensorflow3 .
sudo nvidia-docker build --no-cache -t sibuzu/develop3 -f Dockerfile.develop3 .


