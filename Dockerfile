FROM python:3.9-alpine AS virtualenv
WORKDIR /build
RUN apk add --no-cache --update python3-dev libffi-dev gcc musl-dev make g++ libmagic hiredis
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir --upgrade wheel \
    && python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.9-alpine AS base
WORKDIR /muistot
RUN apk add --no-cache --update libmagic hiredis curl && mkdir -p /opt/files
COPY --from=virtualenv /opt/venv /opt/venv

FROM base AS server
WORKDIR /muistot
ENV PATH="/opt/venv/bin:$PATH"
HEALTHCHECK --interval=1m --timeout=10s --retries=1 --start-period=1m \
CMD sh -c "curl -fs http://localhost:80/projects > /dev/null || kill 1"
EXPOSE 80
COPY src .
CMD ["uvicorn", "muistot.backend.main:app", "--proxy-headers", "--host", "0.0.0.0" , "--port", "80", "--workers", "2", "--log-level", "info"]

FROM server AS test-server
WORKDIR /muistot
ENV PATH="/opt/venv/bin:$PATH"
CMD ["uvicorn", "muistot.backend.main:app", "--reload", "--proxy-headers", "--host", "0.0.0.0", "--port", "80", "--log-level", "debug"]

FROM base AS test-runner
WORKDIR /muistot
ENV PATH="/opt/venv/bin:$PATH"
COPY pytest.ini .
COPY .coveragerc .
COPY requirements-dev.txt .
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY src src
RUN ls && pip install --no-cache-dir --no-index ./src
CMD ["pytest"]