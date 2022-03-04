FROM python:3.9-alpine AS worker
WORKDIR /build
RUN apk add --no-cache --update python3-dev libffi-dev gcc musl-dev make g++
RUN python -m pip install --upgrade pip
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

FROM python:3.9-alpine
WORKDIR /code
COPY --from=worker /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY ./mailer ./mailer
COPY ./templates.txt /opt/templates.txt
CMD ["uvicorn", "mailer.main:app", "--proxy-headers", "--host", "0.0.0.0", "--port", "80"]