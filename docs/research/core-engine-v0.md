# EPA CORE ENGINE v0 — benchmark longitudinal sintético

## Executar

```bash
python -m pip install -e ".[dev,research]"
python -m epa.genesis.generate --output data/demo --students 500 --seed 20261029
python -m epa.core_engine.cli --dataset data/demo/academic_history.parquet --output data/demo/report.json
pytest -q
```

## Critérios

Prediz se a média de disciplinas **no próximo ano** será >= 6. Cada observação de treino corresponde a um estudante no ano de origem e possui rótulo no ano seguinte. A última série não pode ser origem, pois não há rótulo futuro.

Cada identidade de estudante pertence exclusivamente ao treino ou ao teste no protocolo atual. Modelos são treinados apenas com dados de treino, com imputação/scaling internos.

Este é um teste *de generalização para alunos não vistos dentro da mesma população sintética*, não uma validação temporal para períodos futuros. O target se origina de regras do gerador e NÃO prova adequação à realidade escolar.

## Próximos incrementos

- validação por períodos futuros e por escola (quando houver escolas em Genesis)
- snapshots M1/M2/M3 com avaliações internas bimestrais
- ablação das features históricas
- clustering e avaliação de perfis sem vazamento
- rastreamento MLflow e autorizações assinadas Sentinel/Ledger
