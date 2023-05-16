#! /bin/bash
# If new docker compose is used the log driver is ignored and attach needs to be used
cd "${0%/*}/.."
docker compose -f test-runner-compose.yml down -v --remove-orphans
docker compose -f test-runner-compose.yml up \
  --force-recreate --remove-orphans --build \
  --abort-on-container-exit --exit-code-from runner --attach runner
test_result=$?
docker compose -f test-runner-compose.yml down -v --remove-orphans # This can be omitted to leave db on
if [ "$test_result" = "0" ]; then
  echo "Tests Passed"
  exit 0
else
  echo "Tests Failed"
  exit 1
fi