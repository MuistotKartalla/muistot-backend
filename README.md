## Backend Server

#### Multistage Docker image for testing

Builds the server image in two stages by copying over
a [virtual environment](https://docs.python.org/3/library/venv.html) to the final image.

Runs currently on __Alpine Linux__ from `python:3.9-alpine` base image.

The final image is around `100MB`

#### Backend server

The server is built with [FastAPI](https://fastapi.tiangolo.com/) and runs on [Uvicorn](https://www.uvicorn.org/)

---

## Information

![[]](.github/images/api-structure.png)

Here is the general structure of the api and a description of actions available for each resource.

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
docker build -t 'image_name' -f server.Dockerfile .
```

This isn't needed for anything as `docker-compose` takes care of things.

---

#### TODO

The old dump didn't include users or comments so migrating them is yet untested

- Happy path integration tests
- Test shown counts for sites, memories, comments, etc.
- Test permissions
- Test site fetch params
- Not so happy tests
