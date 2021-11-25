#! /bin/sh
cd "${0%/*}/.."
docker run -p 127.0.0.1:5603:80 -i -t --rm  -v "$PWD/src/app":/code/app --name muistot-testserver muistot_testserver