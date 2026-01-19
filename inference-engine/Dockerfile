FROM python:3.12-slim AS builder

WORKDIR /build

RUN pip install --no-cache-dir grpcio-tools==1.60.0

COPY ../proto-contracts/src/main/proto ./proto

RUN python -m grpc_tools.protoc \
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
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY --from=builder /build/generated ./generated

COPY src ./src

COPY models ./models

RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 50051

CMD ["python", "-u", "src/inference/server.py"]