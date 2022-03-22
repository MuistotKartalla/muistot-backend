FROM muistot-usernames:latest
COPY ./test ./test
CMD pytest --cov=app --cov-report=html --cov-report=term && echo 'Tests Done'