#! /bin/sh
cd "${0%/*}/.."
docker-compose down -v
docker volume rm muistot-db-data
docker volume create --name muistot-db-data
docker-compose up -d db