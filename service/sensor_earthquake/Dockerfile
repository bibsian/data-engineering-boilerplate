FROM ghcr.io/astral-sh/uv:python3.14-alpine

# Copy uv binary from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PATH="/opt/program:$PATH"
ENV PYTHONPATH="/opt/program:$PYTHONPATH"

WORKDIR /opt/program

# Copy project files for dependency resolution
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
RUN uv pip install --system -r pyproject.toml

# Copy service-specific files
COPY ./service/kafka_client.py ./
COPY ./service/sensor_earthquake/ ./

# Copy shared service files
COPY ./service/db.py ./service/lake.py ./service/stream_handles.py ./
