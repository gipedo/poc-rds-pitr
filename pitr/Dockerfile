FROM python:3.8-alpine

MAINTAINER aleksandar@globaldatanet.com

WORKDIR /app
COPY Pipfile* ./
RUN apk add --no-cache postgresql-client && \
    pip install pipenv && \
    pipenv install

COPY clone_db.py /app

CMD ["pipenv", "run", "clone_db"]