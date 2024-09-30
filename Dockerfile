FROM python:3-slim

WORKDIR /sensor
COPY requirements.txt /sensor
RUN pip3 install --no-cache-dir -r requirements.txt

COPY sensor/ /sensor

ENTRYPOINT [ "python", "./sensor.py"]

