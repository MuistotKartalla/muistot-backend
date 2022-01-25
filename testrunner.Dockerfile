FROM python:3.9-alpine AS worker
WORKDIR /test-runner
RUN apk add --no-cache --update python3-dev libffi-dev gcc musl-dev make g++
RUN python -m pip install --upgrade pip
RUN python -m venv /test-runner/venv
ENV PATH="/test-runner/venv/bin:$PATH"
COPY requirements.txt .
COPY requirements-dev.txt .
RUN pip install -r requirements-dev.txt
COPY ./src/ ./src/
RUN pip install -e ./src
CMD pytest --cov=muistoja --cov-report term --cov-report html && echo 'Tests Done'
