#! /bin/bash
cd "${0%/*}/.."
docker compose up --force-recreate --remove-orphans --build --attach app