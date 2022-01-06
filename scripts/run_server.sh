#! /bin/sh
cd "${0%/*}/.."
docker-compose up -d db
docker-compose up --force-recreate --remove-orphans --build app