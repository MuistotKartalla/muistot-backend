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
COPY ./src/ ./src/
# Copy test oauth and mailer
COPY ./src/test/server/login/oauth_test_module.py ./src/muistot/login/providers/imaginary.py
COPY ./src/test/core/mailer_test_module.py ./src/muistot/mailer/imaginary.py
# Install
RUN pip install ./src
CMD pytest --cov=muistot --cov-report term --cov-report html --cov-report xml:./htmlcov/coverage.xml && echo 'Tests Done'
