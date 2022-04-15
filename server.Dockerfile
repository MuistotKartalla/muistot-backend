FROM python:3.9-alpine AS worker
WORKDIR /build
RUN apk add --no-cache --update python3-dev libffi-dev gcc musl-dev make g++
RUN python -m pip install --upgrade pip \
    && python -m pip install --upgrade wheel \
    && python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY ./email ./email
RUN pip install ./email

FROM python:3.9-alpine
WORKDIR /code
RUN apk add --no-cache --update libmagic hiredis curl && mkdir -p /opt/files
COPY --from=worker /opt/venv /opt/venv
COPY src .
ENV PATH="/opt/venv/bin:$PATH"
EXPOSE 5600
HEALTHCHECK --interval=1m --timeout=10s --retries=1 --start-period=1m \
CMD sh -c "curl -fs http://localhost:$PORT/projects > /dev/null || kill 1"
CMD ["uvicorn", "muistot.backend.main:app", "--proxy-headers", "--port", "5600", "--workers", "2"]
