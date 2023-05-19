#! /bin/sh
docker build -f Dockerfile -t muistot/namegen-dev-test:latest --target test .
docker run --rm -it -v "$(pwd)/htmlcov/:/root/htmlcov/" muistot/namegen-dev-test:latest