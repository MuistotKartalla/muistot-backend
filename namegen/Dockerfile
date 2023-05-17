FROM python:3.9-alpine AS server
WORKDIR /root

RUN apk add sqlite
COPY ./requirements.txt .
RUN pip install -r requirements.txt

COPY ./setup.py .
COPY ./src ./src
RUN pip install .

COPY ./db.sql .
RUN sqlite3 usernames.db < ./db.sql

CMD uvicorn --port 80 --host 0.0.0.0 --workers 1 --no-access-log app.main:app

FROM server AS test
COPY ./test ./test
CMD pytest --cov=app --cov-report=html --cov-report=term