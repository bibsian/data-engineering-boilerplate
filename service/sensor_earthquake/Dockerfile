FROM python:3.14

ENV path="/opt/program"

COPY ./service $path
COPY ./service/sensor_earthquake $path

# would clone this from a git repo as
# opposed to copy paste
RUN pip install -r $path/requirements.txt

WORKDIR $path
