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
RUN apk add --no-cache --update libmagic hiredis && mkdir -p /opt/files
COPY --from=worker /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
CMD ["uvicorn", "muistot.backend.main:app", "--reload", "--proxy-headers", "--host", "0.0.0.0", "--port", "80"]
