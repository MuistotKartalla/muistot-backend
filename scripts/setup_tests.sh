#! /bin/sh
cd "${0%/*}/.."
pip install -r ./requirements-dev.txt
pip install -e ./src