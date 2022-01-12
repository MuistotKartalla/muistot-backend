#! /bin/sh
cd "${0%/*}/.."
docker-compose -f test-runner-compose.yml down -v --remove-orphans
docker-compose -f test-runner-compose.yml up --force-recreate --remove-orphans --build
docker-compose -f test-runner-compose.yml down -v --remove-orphans # This can be omitted to leave db on