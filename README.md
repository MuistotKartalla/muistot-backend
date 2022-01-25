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

- Backend on `5600`
- Database on `5601`
- Adminer on `5602`
- MailDev on `5603`

The setup scripts could be refactored into single files.

#### Recreating database

```shell
sh scripts/recreate_db.sh
```

#### Running test server

```shell
sh scripts/run_server.sh
```

OR

```shell
sh scripts/run_alt_server.sh
```

for new Docker versions.

#### Stopping

```shell
docker-compose down -v
```

#### Testing

The tests can be run using the following commands

````shell
sh scripts/run_tests.sh
````

OR

````shell
sh scripts/run_alt_tests.sh
````

for new Docker versions.

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

```mariadb
ALTER TABLE memories
    ADD COLUMN IF NOT EXISTS deleted BOOLEAN NOT NULL DEFAULT FALSE
```

#### 20.01

Added superusers. Migrate please.

```mariadb
CREATE TABLE IF NOT EXISTS superusers
(
    user_id INTEGER NOT NULL,
    PRIMARY KEY pk_superusers (user_id),
    CONSTRAINT FOREIGN KEY fk_superusers (user_id) REFERENCES users (id)
) COMMENT 'Global SuperUsers';
```