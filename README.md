## Backend Server

[![codecov](https://codecov.io/gh/MuistotKartalla/muistot-backend/branch/master/graph/badge.svg?token=4FYJJVP12R)](https://codecov.io/gh/MuistotKartalla/muistot-backend)

#### Backend server

The server is built with [FastAPI](https://fastapi.tiangolo.com/) and runs on [Uvicorn](https://www.uvicorn.org/)

---

## Development Setup

- Backend on `5600`
- Database on `5601`
- Adminer on `5602`
- MailDev on `5603`

The setup scripts could be refactored into single files.

#### Recreating database

Deletes all data and volumes

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

---

#### Coverage

Measured with branches included Branch coverage disabled in a few lines in the following files:

- [api/__init__.py](src/muistot/backend/api/__init__.py)
    - Feature switch, marked with TODO
- [api/publish.py](src/muistot/backend/api/publish.py)
    - Exhaustive else-if without default branch
- [backend/main.py](src/muistot/backend/main.py)
    - Testing switch
- [exists/decorators.py](src/muistot/backend/repos/exists/decorators.py)
    - Possible bug in coverage for decorator function, marked with TODO
- [cache/decorators.py](src/muistot/cache/decorator.py)
    - Double-checked locking

## Default Config

```json
{
  "testing": true,
  "databases": {
    "default": {
      "host": "db",
      "port": 3306,
      "database": "muistot",
      "user": "root",
      "password": "test",
      "ssl": false,
      "workers": 4,
      "cpw": 4,
      "max_wait": 2
    }
  },
  "security": {
    "bcrypt_cost": 12,
    "oauth": {}
  },
  "sessions": {
    "redis_url": "redis://session-storage?db=0",
    "token_lifetime": 960,
    "token_bytes": 32
  },
  "files": {
    "location": "/opt/files",
    "allowed_filetypes": [
      "image/jpg",
      "image/jpeg",
      "image/png"
    ]
  },
  "namegen": {
    "url": "http://username-generator"
  },
  "cache": {
    "redis_url": "redis://session-storage?db=1",
    "cache_ttl": 600
  },
  "mailer": {
    "driver": "muistot_mailers",
    "config": {
      "driver": "dev-log"
    }
  },
  "localization": {
    "default": "fi",
    "supported": [
      "fi",
      "en"
    ]
  }
}
```

## Developer Notes

##### Login

Logins are handled through email. There is a general purpose interface for mailing in [mailer](src/muistot/mailer). This
can be used to integrate with _Mailgun_, _Amazon SES_, _Local Server_, ...

There was a plan to add OAuth from other provides, __but it is currently unfinished__.

There is still support for password login.

##### Session Storage

The sessions are stored in redis and the management is done with the [sessions](src/muistot/sessions) module. Sessions
are stored in redis and the session token byte length is defined in the config. The tokens are base64 encoded. The
sessions are bound to users in the Redis and any two sessions cannot share the same token. The sessions are stored in
the following way:

- token => Session Data
- user => Session Tokens

Stale sessions are removed from the user pool on login. Tokens are hashed before storage.

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

There is a small hack done to the OpenAPI in [helpers.py](src/muistot/errors/helpers.py) to replace the original errors.
Also, all the error handlers are defined there.

##### Repos

This whole thing is under [repos](src/muistot/backend/repos). These take care of fetching and converting the data coming
from and going into the database. The `base` contains the base definitions and checks for repos and the `exists`
module takes care of fetching resource status information. This status information is used for the repo decorations to
manage access control.

_A bit more clarification on the inner workings of this:_

```
1. REQUEST                       -> REPO (init)
2.         -> EXISTS (decorator) -> REPO (method)
3.                               <- REPO (result)

1. Call comes to an endpoint and repo is constructed
  1.1. The repo is constructed
  1.2. The configure method is called to add information available from the request
  1.3. A fully functional repo is returned
2. A repo method is called and the exist constructor on it intercepts it
  2.1. The exists decorator queries the relevant exists helper for the repo class
  2.2. The decorator method sets up any attributes fetched from the database on the repo
  2.3. A Status is returned and injected into the repo method arguments if desired
  2.4. The call proceeds to the fully initialized repo
3. An entity is returned from the repo and it is mapped to a response
   Usually the database fetch_one is returned and it gets serialized into the response body
```

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

## Information

Here is the general structure of the api and a description of actions available for each resource.

![[]](.github/images/api-structure.png)

__NOTE:__ Latest description is in the swagger docs of the app, or partly
at [Muistotkartalla - Api](https://muistotkartalla.fi/api/docs)

#### Replacing databases

This should do the trick if used in connection store

```python
import databases

Database = databases.Database


def create_connection(database):
    from urllib.parse import quote
    return databases.Database(
        url=(
            f"{database.driver}://"
            f"{quote(database.host)}:{database.port}/{quote(database.database)}"
            f"?username={quote(database.user)}"
            f"&password={quote(database.password)}"
            f"&ssl={str(database.ssl).lower()}"
        ),
        force_rollback=database.rollback,
        **database.driver_config
    )
```

## Developing the Project

#### Getting up to speed

The following steps should get you up to speed on the project structure:

1. Read the previous section on developer notes
2. Take a look at the _database/schemas_ folder
    - See what is stored where
    - How are entities related
3. Take a look at the _muistot.backend_ module
    - See the _api_ module for endpoints
        - See the imports and what they provide
        - Analyze the general endpoint file structure
    - See the actual _models_ for the api
    - Take a dive into the _repos_
        - Look at the _base_ module
            - Look at *\_\_init\_subclass\_\_* and *\_\_init\_\_*
            - See the _files_ attribute
        - Look at the _exists_ module
            - *\_actual\_exists* in _decorators.py_
            - *Exists#start* in _base.py*
        - Take a look at the __repo__ and __exists__ for _comments_
    - See the _services_ module for user edit

#### Modifying the database schema

Always create a new sql file under _database/schemas_ which goes alphabetically last in the file list and that can be applied on top of the old
files. This should ideally be something that can be run as-is even on the live server.

#### Creating new features

If you need to develop new endpoints or features the following is suggested:

1. Create a new endpoint file under _muistot.backend.api_
    - `from ._imports import *`
    - `router = make_router(tags=["Relevant feature(s) from main.py"])`
    - Use Cache with caution if needed: `caches = Cache("memories", evicts={"sites"})`
2. Decide if the feature requires existence checks and/or provides CRUD to a resource
    - NO: new file under services
    - YES: consider setting up a repo, evaluate which is easier
3. Write service methods with Database as the first argument
4. Remember `async def` and `await`
5. Always write tests for the feature
    - At least do happy path tests for the endpoints

## Further Development

#### Replacing Database module

Have this use a ready-made async library.

#### Improving Caching

Add caching to queries.

#### Implementing OAuth

Add support for OAuth login methods.

#### Convert Password login to OAuth module

This would make removing passwords easier in the future as this is meant to be passwordless one day.

#### Splitting the services

The modules are already split per use-case and some further consolidation could be used to split the backend into
multiple small microservices.

#### Improving testing

The testing speed is quite slow now, the tests could be split into smaller parts and run in parallel.

#### Improving configuration and repo model

The queries now fetch data for all requests and this is expensive. This could be refactored to use a caching service to
fetch on interval instead.

#### File Storage

The files are now stored on disk in the docker image which is not that good. This should be abstracted behind an
interface and be made to work with a Storage Bucket service.