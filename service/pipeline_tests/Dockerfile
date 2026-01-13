FROM python:3.6

ENV path="/opt/program"

COPY ./service $path
COPY ./service/pipeline_tests $path

RUN pip install -r $path/requirements.txt

WORKDIR $path
