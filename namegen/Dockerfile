FROM python:3.9-alpine AS server
WORKDIR /root
RUN apk add sqlite
COPY ./requirements.txt .
RUN pip install -r requirements.txt
COPY ./db.sql .
RUN sqlite3 usernames.db < ./db.sql
COPY ./src ./src
RUN pip install --no-index ./src
CMD uvicorn --port 80 --host 0.0.0.0 --workers 1 --no-access-log namegen:app

FROM server AS test
COPY ./requirements-dev.txt .
RUN pip install -r requirements-dev.txt
COPY ./test ./test
CMD pytest --cov=namegen --cov-report=html --cov-report=term