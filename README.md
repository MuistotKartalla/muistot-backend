## Backend Server

#### Multistage Docker image for testing

Builds the server image in two stages by copying over
a [virtual environment](https://docs.python.org/3/library/venv.html) to the final image.

Runs currently on __Alpine Linux__ from `python:3.9-alpine` base image.

The final image is around `100MB`

#### Backend server

The server is built with [FastAPI](https://fastapi.tiangolo.com/) and runs on [Uvicorn](https://www.uvicorn.org/)

#### Notes

If the database gets messed up its easier to just delete the volume and re-compose.

#### Setting it all up

Create a volume for the database

```shell
$ sh script/create_volume.sh
```

To delete it

```shell
$ sh script/delete_volume.sh
```

This will setup:

- Server on `5600`
- Database on `5601`
- Adminer on `5602`

```shell
$ docker-compose up -d
```

But only DB is needed for tests

```shell
$ docker-compose up -d db
```

This will recreate all containers

```shell
$ docker-compose up -d --force-recreate
```

This will stop the containers and delete volumes (not db volume)

```shell
$ docker-compose down -v
```

Or just stop them

```shell
$ docker-compose down
```

Or just running the server:

```shell
$ sh script/testserver.sh
```

You can build the image too:

```shell
$ sh script/build_testserver.sh
```