#! /bin/bash

docker build -t hydrabot:latest .
docker build -t ganache-fork:latest -f Dockerfile-localfork .
