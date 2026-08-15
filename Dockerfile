FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY api ./api
COPY topology ./topology
COPY detectors ./detectors
COPY correlator ./correlator
COPY localiser ./localiser
COPY evidence ./evidence
COPY narrator ./narrator
COPY actions ./actions
COPY bench ./bench
COPY worker ./worker

RUN pip install --no-cache-dir -e .

EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]