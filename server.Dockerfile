FROM python:3.9-alpine AS worker
WORKDIR /build
RUN apk add --no-cache --update python3-dev libffi-dev gcc musl-dev make g++
RUN python -m pip install --upgrade pip \
    && python -m pip install --upgrade wheel \
    && python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN pip install gunicorn
COPY ./email ./email
RUN pip install ./email

FROM python:3.9-alpine
WORKDIR /code
RUN apk add --no-cache --update libmagic hiredis && mkdir -p /opt/files
COPY --from=worker /opt/venv /opt/venv
COPY src .
ENV PATH="/opt/venv/bin:$PATH"
ENV WEB_CONCURRENCY=2
ENV PORT=5600
EXPOSE 5600
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker","muistot.backend.main:app"]
