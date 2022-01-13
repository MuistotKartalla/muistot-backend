## Backend Server

#### Multistage Docker image for testing

Builds the server image in two stages by copying over
a [virtual environment](https://docs.python.org/3/library/venv.html) to the final image.

Runs currently on __Alpine Linux__ from `python:3.9-alpine` base image.

The final image is around `100MB`

#### Backend server

The server is built with [FastAPI](https://fastapi.tiangolo.com/) and runs on [Uvicorn](https://www.uvicorn.org/)

---

## Setup

- Server on `5600`
- Database on `5601`
- Adminer on `5602`

The setup scripts could be refactored into single files.

#### Recreating database

```shell
docker-compse down -v
docker volume rm muistot-db-data
docker volume rm muistot-file-data
docker volume create --name muistot-db-data
docker volume create --name muistot-file-data
docker-compose up -d db
```

OR

```shell
sh scripts/recreate_db
```

#### Running test server

```shell
docker-compose -f test-runner-compose.yml down -v
docker-compose -f test-runner-compose.yml up --force-recreate --remove-orphans --build app
docker-compose -f test-runner-compose.yml down -v # This can be omitted to leave db on
```

OR

```shell
sh scripts/server.sh
```

#### Stopping

```shell
docker-compose down -v
```

#### Testing

The tests can be run using the following commands

```shell
docker-compose -f test-runner-compose.yml down -v --remove-orphans
docker-compose -f test-runner-compose.yml up --force-recreate --remove-orphans --build
docker-compose -f test-runner-compose.yml down -v --remove-orphans # This can be omitted to leave db on
```

OR

````shell
sh scripts/run_tests.sh
````

Generates coverage reports in terminal and [html reports](./htmlcov/index.html)

#### Others

Build the test image

```shell
docker build -t 'image_name' -f testserver.Dockerfile .
```

This isn't needed for anything as `docker-compose` takes care of things.

---

## Database Migration

[migration.sql](./database/migration.sql) should migrate the old db data to the new one.

1. Connect to the MariaDB `root:test` and dump the database into the server.
2. Then run the `migration.sql`

You might need to change the database name if your dump is a bit different.

#### TODO

The old dump didn't include users or comments so migrating them is yet untested

- Happy path integration tests
- Test shown counts for sites, memories, comments, etc.
- Test permissions
- Test site fetch params
- Not so happy tests

## DEV Notes

#### 13.01.2022

Added new column to memories, please migrate existing data:

````mariadb
ALTER TABLE memories
    ADD COLUMN IF NOT EXISTS deleted BOOLEAN NOT NULL DEFAULT FALSE
````