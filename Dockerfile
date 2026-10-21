# The official Python image publishes both linux/arm64 and linux/amd64.
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src/ ./src/
RUN python -m pip install --no-cache-dir "setuptools>=75,<81" \
    && python -m pip install --no-cache-dir --no-build-isolation . \
    && groupadd --gid 10001 app \
    && useradd --uid 10001 --gid 10001 --no-create-home app \
    && install -d -o 10001 -g 10001 -m 0700 /credentials \
    && install -d -o 10001 -g 10001 -m 0750 \
        /workspace /workspace/results /workspace/.local

USER 10001:10001
WORKDIR /workspace
ENTRYPOINT ["python", "-m", "tradingview_screening"]
CMD ["--help"]
