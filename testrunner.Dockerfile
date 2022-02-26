FROM python:3.9-alpine AS worker
WORKDIR /test-runner
RUN apk add --no-cache --update python3-dev libffi-dev gcc musl-dev make g++ libmagic hiredis \
    && python -m pip install --upgrade pip \
    && python -m venv /test-runner/venv
RUN mkdir -p /opt/files
ENV PATH="/test-runner/venv/bin:$PATH"
COPY requirements*.txt .
RUN pip install -r requirements-dev.txt
COPY ./src/ ./src/
RUN pip install -e ./src
CMD pytest --cov=muistoja --cov-report term --cov-report html && echo 'Tests Done'
