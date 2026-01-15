FROM python:3.14

ENV path="/opt/program"

COPY ./service $path
COPY ./service/sensor_tectonic_stress $path

# Would install through git
RUN pip install -r $path/requirements.txt

WORKDIR $path
