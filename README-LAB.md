# EPA local research lab (Docker Compose)

Place `Dockerfile.research`, `compose.research.yaml`, and `tools/compare_genesis.py`
in the repository root, preserving `tools/`.

## Requirements
Docker Desktop running on Windows with Linux containers enabled.

## Quick checks
```powershell
docker --version
docker compose version
docker info --format '{{.OSType}}'
docker compose -f compose.research.yaml config --quiet
docker compose -f compose.research.yaml build research
docker compose -f compose.research.yaml run --rm research python --version
```

## Reproducibility test (preserves existing experiment files)
```powershell
docker compose -f compose.research.yaml run --rm research python -m epa.genesis.v3 --output data/bench-v3-120-docker-001 --students 120 --seed 20261029
docker compose -f compose.research.yaml run --rm research python tools/compare_genesis.py data/tgi2-experimento-001 data/bench-v3-120-docker-001
```

Note: image-build time and container startup time must not be confused with
GENESIS processing time. These tests are initial smoke/equivalence tests, not
rigorous performance benchmarks. If the v3 directory exists choose a fresh name.
