FROM python:3.13-slim

WORKDIR /app

RUN pip install --no-cache-dir pyyaml requests

COPY src/* ./

COPY entrypoint.sh ./
RUN chmod +x entrypoint.sh

ENV SCHEDULE_INTERVAL=300
ENV SETTINGS_FILE=/app/settings.yml

ENTRYPOINT ["./entrypoint.sh"]
