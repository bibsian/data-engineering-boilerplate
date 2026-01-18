FROM ghcr.io/astral-sh/uv:python3.14-alpine

# Copy uv binary from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install bash
RUN apk add --no-cache bash

ENV PATH="/opt/program:$PATH"
ENV PYTHONPATH="/opt/program:$PYTHONPATH"

WORKDIR /opt/program

# Copy project files for dependency resolution
COPY pyproject.toml uv.lock ./

# Install dependencies including test dependencies
RUN uv pip install --system -r pyproject.toml --extra test

# Copy shared service files that might be needed for tests
COPY ./service/bronze_consumer.py ./service/kafka_client.py ./service/db.py ./service/lake.py ./service/stream_handles.py ./

# Copy service files  
COPY ./service/pipeline_tests/ ./
