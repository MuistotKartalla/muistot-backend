#! /bin/sh
cd "${0%/*}/.."
pytest --cov=app --cov-report term --cov-report html