#! /bin/bash

if [ ! -f vars.sh ]; then
    echo "You need to setup your vars.sh file first"
    exit
fi

source test-vars.sh

docker compose --file docker-compose-test.yml up --force-recreate -d
source venv/bin/activate

pytest src/.

docker compose --file docker-compose-test.yml down

