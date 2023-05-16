FROM python:3.9-alpine AS worker
WORKDIR /test-runner
RUN apk add --no-cache --update python3-dev libffi-dev gcc musl-dev make g++ libmagic hiredis
RUN python -m pip install --upgrade pip \
    && python -m pip install --upgrade wheel \
    && python -m venv /test-runner/venv
RUN mkdir -p /opt/files
ENV PATH="/test-runner/venv/bin:$PATH"
COPY requirements*.txt ./
RUN pip install -r requirements-dev.txt
# Coverage
COPY ./pytest.ini .
COPY ./.coveragerc .
# Source
COPY ./src/ ./src/
# Copy test mailer
COPY ./src/test/core/mailer_test_module.py ./src/muistot/mailer/imaginary.py
# Install
RUN pip install ./src
CMD pytest && echo 'Tests Done'
