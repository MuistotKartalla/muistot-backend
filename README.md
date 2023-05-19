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

#### Stopping

```shell
docker-compose down -v
```

#### Testing

The tests can be run using the following commands

````shell
sh scripts/run_tests.sh
````

Generates coverage reports in terminal and [html reports](./htmlcov/index.html)

---

#### Coverage

Measured with branches included Branch coverage disabled in a few lines in the following files:

- [api/publish.py](src/muistot/backend/api/publish.py)
    - Exhaustive else-if without default branch
- [backend/main.py](src/muistot/backend/main.py)
    - Testing switch

## Application Config

Check the defaults in [configuratioin models](src/muistot/config/models.py).

Two configs are currently in use for development:

- [config.json](config.json)
- [config-test.json](config-test.json)

## Login

Logins are handled through email.
There are multiple types of mailers available for mailing in [mailer](src/muistot/mailer).
The [ZonerMailer](src/muistot/mailer/zoner.py) is used for mailing to the local Maildev.

## Session Storage

The sessions are stored in redis and the management is done with the
[sessions](src/muistot/security/sessions.py) module.
Sessions are stored in redis and the session token byte length is defined in the config.
The tokens are base64 encoded in the Authorization header and get stored in hashed format in Redis.
Stale sessions get removed from the user pool on login.
The session manager maintains a linking to all user sessions so that it can clear them.

Sessions and user data can be accessed using the [session middleware](src/muistot/middleware/session.py).

## Databases

These are found under [database](src/muistot/database)

These are wrapped connections from SQLAlchemy with async support through SQLAlchemy and asyncmy.
Some custom wrappers are used to retain backwards compatibility with the old custom implementation.

The database connections are provided to the request scope from
the [database middleware](src/muistot/middleware/database.py).

## OpenAPI

There is a small hack done to the OpenAPI in
[helpers.py](src/muistot/errors/handlers.py)
to replace the original errors.
This is due to how the application handles errors and uses a different schema from default.

## Repos

This whole thing is under [repos](src/muistot/backend/repos). These take care of fetching and converting the data coming
from and going into the database. The `base` contains the base definitions and checks for repos and the `status`
module takes care of fetching resource status information. This status information is used for the repo decorations to
manage access control.

_A bit more clarification on the inner workings of this:_

```
1. REQUEST                       -> REPO (init)
2.         -> STATUS (decorator) -> REPO (method)
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

Here is an example of a repo method:

```python
@append_identifier('project', key='id')
@require_status(Status.DOES_NOT_EXIST | Status.SUPERUSER, errors={
    Status.DOES_NOT_EXIST | Status.AUTHENTICATED: HTTPException(
        status_code=HTTP_403_FORBIDDEN,
        detail="Not enough privileges",
    )
})
async def create(self, model: NewProject) -> PID:
    ...
```

First, the `append_identifier` decorator is used to add the project being created to the available identifiers for
status checks. This is important to do for each method where this information is not directly available from the initial
batch of identifiers given to the repo. In the usual case the [repo creator](src/muistot/backend/api/utils/repo.py)
gives the repo all the path parameters as identifiers.

Second, the `require_status` decorator is used to require a status check to pass before the method is called.
The `require_status` decorator [defines some default errors](src/muistot/backend/repos/status/base.py), but allows the
user to provide custom error conditions through the decorator as is seen above. Due to the SUPERUSER check, we need to
provide a custom error when the DOES_NOT_EXIST condition would be true without SUPERUSER present.

Usually the status checks do not need custom errors even with multiple status checks:

```python
@append_identifier('site', value=True)
@require_status(Status.EXISTS | Status.ADMIN, Status.EXISTS | Status.OWN)
async def modify(self, site: SID, model: ModifiedSite, status: Status) -> bool:
    ...
``` 

In this case the multiple status conditions passed to the decorator cause it to allow any request matching __any__ of
the given statuses.

## Security

The [security](src/muistot/security) provides classes for users and crude session scope based resource access control
management. The access control is double-checked, once at the resource level to prevent grossly illegal calls and a
second time at the repo level to fetch the up-to-date information.

This could be improved further by revoking sessions upon receiving a permission level related issue from a repo meaning
someone was removed as an admin for example.

## Logging

The logging package [logging](src/muistot/logging/__init__.py) hooks into the uvicorn error logger to propagate log
messages.

## Config

Config is loaded with the [config](src/muistot/config) package. The config is a single Pydantic model that is read
from `./config.json` or `~/config.json` otherwise the base (testing) config is used.

## Testing

The tests are set up in a way where the setup builds the needed docker image and installs the server as a package there.
This has the added benefit of providing typehints for the project if used in conjunction
with [PyCharm](https://www.jetbrains.com/pycharm/) remote interpreters. Highly recommended btw, free for students.

Main [conftest.py](./src/test/conftest.py) takes care of loading the default database connection per __session__. The
integration folder conftest overrides the client default databas dependency with the initialized database dependency.

## CI/CD

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

The comments were scrapped.

__NOTE:__ Latest description is in the swagger docs of the app, or partly
at [Muistotkartalla - Api](https://muistotkartalla.fi/api/docs)

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
        - See the Repo Creator
    - See the actual _models_ for the api
    - Take a dive into the _repos_
        - Look at the _base_ module
            - See the _files_ attribute
        - Look at the _exists_ module
        - Take a look at the __repo__ and __exists__ for _memories_
    - See the _services_ module for user edit

#### Modifying the database schema

Remember to do changes that are somewhat backwards compatible and apply them to the actual database.
The schema is in an okay state, but additions are much easier than deletions.

#### Creating new features

If you need to develop new endpoints or features the following is suggested:

1. Create a new endpoint file under _muistot.backend.api_
    - Check imports from other api modules to see what is where
    - `router = make_router(tags=["Relevant feature(s) from main.py"])`
    - Use Cache with caution if needed by getting it from the middleware
2. Decide if the feature requires existence checks and/or provides CRUD to a resource
    - NO: new file under services
    - YES: consider setting up a repo, evaluate which is easier
3. Write service methods with Database as the first argument
4. Remember `async def` and `await`
5. Always write tests for the feature
    - At least do happy path tests for the endpoints

## Further Development

#### Improving Caching

Add caching to queries.

#### Improving testing

The testing speed is quite slow now, the tests could be split into smaller parts and run in parallel.

#### Improving configuration and repo model

The queries now fetch data for all requests and this is expensive. This could be refactored to use a caching service to
fetch on interval instead.

#### File Storage

The files are now stored on disk in the docker image which is not that good. This should be abstracted behind an
interface and be made to work with a Storage Bucket service.