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

## Rust GENESIS → Parquet (bridge experimental)

O Rust já gera os registros acadêmicos longitudinalmente por JSONL. Para validar
os Parquet e manifestos sem adicionar ainda as bibliotecas Arrow/Parquet ao binário
Rust, a ponte Python abaixo consome o stream em lotes limitados:

```powershell
python -m pip install -e ".[dev,research,streaming]"
python -m epa.genesis.rust_bridge --output data/rust-bridge-120-v1 --students 120 --seed 20261029
python tools/compare_genesis_parquet.py data/bench-v3-120-docker-001 data/rust-bridge-120-v1
```

Se o dataset v3 de referência não existir, gere um novo diretório com a mesma seed,
catálogo e quantidade de estudantes. **Não sobrescreva datasets existentes.**

O manifesto gerado usa schema `epa.genesis.dataset.rust_bridge.v1` e identifica
`generator_engine=rust-mt19937-jsonl-python-pyarrow-bridge`. Ele **não** deve ser
confundido com o GENESIS v3 puro ou com uma gravação Parquet nativa em Rust.

O comparador valida hashes SHA-256 dos arquivos, metadados das tabelas e
igualdade exata das linhas lógicas (multiconjuntos). Um comparador JSONL anterior
também analisa divergências numéricas com tolerância explícita.

Observação sobre desempenho: esta ponte inclui Cargo, subprocesso, parsing JSON
e PyArrow. Não use o tempo desse comando como benchmark do motor Rust puro ou
da escrita Parquet nativa. Esta implementação serve para homologar integração e
equivalência, não para demonstrar aceleração.
