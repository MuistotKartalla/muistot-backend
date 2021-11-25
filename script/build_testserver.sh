#! /bin/sh
cd "${0%/*}/.."
docker build -t muistot_testserver -f testserver.Dockerfile .