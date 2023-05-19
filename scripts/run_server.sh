#! /bin/bash
cd "${0%/*}/.."
docker compose --profile server up --force-recreate --remove-orphans --build --attach app