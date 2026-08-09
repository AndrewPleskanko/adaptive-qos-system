FROM python:3.12-slim AS builder

WORKDIR /build

RUN pip install --no-cache-dir "setuptools<82.0.0" grpcio-tools==1.60.0

COPY proto ./proto

RUN mkdir -p ./generated && \
    python -m grpc_tools.protoc \
    -I./proto \
    --python_out=./generated \
    --grpc_python_out=./generated \
    ./proto/*.proto

FROM python:3.12-slim

WORKDIR /app

RUN groupadd -r appgroup && \
    useradd -r -g appgroup appuser

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    netcat-openbsd && \
    GRPC_HEALTH_PROBE_VERSION=v0.4.24 && \
    ARCH=$(uname -m) && \
    if [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then PROBE_ARCH="linux-arm64"; else PROBE_ARCH="linux-amd64"; fi && \
    curl -sSfL -o /usr/local/bin/grpc_health_probe \
      https://github.com/grpc-ecosystem/grpc-health-probe/releases/download/${GRPC_HEALTH_PROBE_VERSION}/grpc_health_probe-${PROBE_ARCH} && \
    chmod +x /usr/local/bin/grpc_health_probe && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY inference-engine/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY --from=builder /build/generated ./generated

COPY inference-engine/src ./src

COPY inference-engine/models ./models

RUN python src/inference/train.py && \
    echo "ML model trained successfully"

RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 50051

CMD ["python", "-u", "src/inference/server.py"]