#! /bin/sh
cd "${0%/*}/.."
docker-compose up -d db
pytest --cov=app --cov-report term --cov-report html