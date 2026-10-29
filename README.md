# EduPredict Analytics — EPA Research Platform

Plataforma experimental de pesquisa educacional; **não há modelos validados em dados reais nem controles completos para dados pessoais**.

| Nome | Papel | Estado |
| --- | --- | --- |
| EPA ATLAS | Catálogo curricular | Demo sintética |
| EPA GENESIS | Históricos longitudinais Parquet | Protótipo |
| EPA CORE ENGINE | Modelos e benchmarks | Baseline sintético |
| EPA SENTINEL | Políticas e verificação temporal | Protótipo |
| EPA LEDGER | Auditoria e evidências hash-linked | Protótipo |

## Rodar o primeiro benchmark

```bash
python -m pip install -e ".[dev,research]"
pytest -q
python -m epa.genesis.generate --output data/demo --students 500 --seed 20261029
python -m epa.core_engine.cli --dataset data/demo/academic_history.parquet --output data/demo/report.json
```

A execução compara majority, regressão logística e Random Forest prevendo **média anual >= 6 no ano seguinte**, com separação por estudante. Isso **não representa evasão** ou o antigo experimento M1/M2/M3.

As regras de geração e o catálogo curricular são sintéticos e **não foram calibrados contra dados escolares reais**. Nenhuma alegação de habilidade BNCC mapeada ou de proficiência real deve ser feita.

Veja [ADRs](docs/adr/README.md), [Atlas/Genesis](docs/architecture/atlas-genesis.md) e [Core Engine](docs/research/core-engine-v0.md).
