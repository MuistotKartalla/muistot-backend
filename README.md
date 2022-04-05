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
- Not so happy tests
- Finish documentation examples with something sensible

#### Developer Notes

##### Login

Logins are handled through email. There is a general purpose interface for mailing in [mailer](src/muistot/mailer).
This can be used to integrate with _Mailgun_, _Amazon SES_, _Local Server_, ...

There was a plan to add OAuth from other provides, __but it is currently unfinished__.

##### Session Storage

The sessions are stored in redis and the management is done with the [sessions](src/muistot/sessions) module.
Sessions are stored in redis and the session token byte length is defined in the config. The tokens are base64 encoded.
The sessions are bound to users in the Redis and any two sessions cannot share the same token. The sessions are stored
in the following way:

- token => Session Data
- user => Session Tokens

Technically it would be possible to end up in a situation where the user bucket has a session token that expired and was
assigned to someone else. However, since this only leads to the session getting culled if the other user clear all their
session it is not deemed a security risk. The data in the user bucket is __only__ used for session clearing.

To remedy this risk a redis pub/sub listener should be employed in the final deployment that removes the value from any
user set on expiry.

##### Databases

These are found under [database](src/muistot/database)

The database connections are held inside a holder `Databases`. The connections used to be handled by the `databases`
library, but it caused some weird and hard to track connection bugs at the end of the project deadline in Spring 2022,
so this module was reworked in one day to handle all the connection needs for the application.

If the `ContextVars` and connection bugs are fixed from `databases` the library could be used as a near drop-in
replacement for the custom connection classes. For this it might be the best to wait until the library and at least one
of the backends reaches maturity `>=1.0.0` and then swap to using it.

The `:name` query parameters were originally used from `databases`, but the `pymysql` expects format `%(name)s`
so they are just swapped with regex `:(\w+)` => `%(\1)s`.

##### FastAPI

The dependency and callsite clutter are quite annying at places. The callsites of many functions are polluted by request
and _Depends_ parameters, but grouping them under one dependency is not really worth it. This could be improved later.

There is a small hack done to the OpenAPI in [helpers.py](src/muistot/errors/helpers.py) to replace the original
errors. Also, all the error handlers are defined there.

##### httpheaders

This `pypi`package provides convenient access to HTTP headers and was deemed useful enough to publish a package of.
Although the package is used here it is not owned by the organization as the projects are not __actively__ maintained,
only as a part of student groups.

##### Repos

This whole thing is under [repos](src/muistot/backend/repos). These take care of fetching and converting the data
coming from and going into the database. The `base` contains the base definitions and checks for repos nad the `exists`
module takes care of fetching resource status information. This status information is used for the repo decorations to
manage access control.

##### Security

The [security](src/muistot/security) provides classes for users and crude session scope based resource access control
management. The access control is double-checked, once at the resource level to prevent grossly illegal calls and a
second time at the repo level to fetch the up-to-date information.

This could be improved further by revoking sessions upon receiving a permission level related issue from a repo meaning
someone was removed as an admin for example.

##### Logging

The logging package [logging](src/muistot/logging/__init__.py) hooks into the uvicorn error logger to propagate log
messages.

##### Config

Config is loaded with the [config](src/muistot/config) package. The config is a single Pydantic model that is read
from `./config.json` or `~/config.json` otherwise the base (testing) config is used.

##### Testing

The tests are setup in a way where the setup builds the needed docker image and installs the server as a package there.
This has the added benefit of providing typehints for the project if used in conjunction
with [PyCharm](https://www.jetbrains.com/pycharm/) remote interpreters. Highly recommended btw, free for students.

The tests rely on the server default config and there are two kinds of scripts under [scripts](./scripts) compatible
with both `docker-compose` and `docker compose` (alt) commands. The invocation is a bit different between them as the
alt versions need to add `--attach` to only get output from a subset of the services.

Main [conftest.py](./src/test/conftest.py) takes care of loading the default database connection per __session__. The
integration folder conftest overrides the client dependency with the initialized dependency.

##### CI/CD

The [file](./.github/workflows/main.yml) takes care of contacting the deployment server through ssh to install the new
version. This could be changed in the future to build a docker image that is pushed to a remote repo to make this
easier.

##### Further Development

This project could be refactored into smaller services e.g:

- login
- users
- admin
- data

And could then be run in a lower cost environment e.g. Amazon Lambda. This would also allow breaking down the project
into smaller parts that could be containerized individually and could be run like microservices.