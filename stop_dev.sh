#! /bin/bash

if [ ! -f vars.sh ]; then
    echo "You need to setup your vars.sh file first"
    exit
fi

source vars.sh

docker compose --profile ganache down

