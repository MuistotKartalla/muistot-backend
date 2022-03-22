#! /bin/sh
cd "${0%/*}/"
docker build -f Dockerfile -t muistot-usernames:latest .
docker build -f test.Dockerfile -t muistot-usernames-test:latest .
docker run --rm -it -v "$(pwd)/htmlcov/:/root/htmlcov/" muistot-usernames-test:latest