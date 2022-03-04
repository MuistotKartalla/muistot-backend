#! /bin/bash
cd "${0%/*}/.."
docker-compose -f test-runner-compose.yml down -v --remove-orphans
docker-compose -f test-runner-compose.yml up \
  --force-recreate --remove-orphans --build \
  --abort-on-container-exit --exit-code-from runner
test_result=$?
docker-compose -f test-runner-compose.yml down -v --remove-orphans
if [ "$test_result" = "0" ]; then
  echo "Tests Passed"
  exit 0
else
  echo "Tests Failed"
  exit 1
fi