#!/usr/bin/env bash

if [[ "$1" == "update" ]]; then
    docker-compose build --no-cache
fi
docker-compose up