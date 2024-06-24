FROM python:3.11-slim-bookworm

RUN apt-get update && apt-get install -y postgresql-client libpq-dev

WORKDIR /opt

ADD requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

ADD src /opt/hydrabot
WORKDIR /opt/hydrabot

CMD ["python", "chat_bot.py"]