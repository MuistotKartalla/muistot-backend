#! /bin/bash
# If new docker compose is used the log driver is ignored and attach needs to be used
cd "${0%/*}/.."
docker compose down -v --remove-orphans
docker compose --profile test up --force-recreate --remove-orphans --build \
  --abort-on-container-exit --exit-code-from testrunner --attach testrunner
test_result=$?
docker compose down -v --remove-orphans # This can be omitted to leave db on
if [ "$test_result" = "0" ]; then
  echo "Tests Passed"
  exit 0
else
  echo "Tests Failed"
  exit 1
fi