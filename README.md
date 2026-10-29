# EduPredict Analytics — EPA Research Platform

Plataforma de experimentação científica educacional. O repositório está em desenvolvimento; **não possui resultados científicos validados nem proteção para dados pessoais reais**.

## Componentes

| Nome | Escopo | Implementação |
| --- | --- | --- |
| EPA ATLAS | Referências e matrizes curriculares versionadas | Validação de catálogo demo |
| EPA GENESIS | Históricos escolares sintéticos longitudinais | Gerador experimental Parquet |
| EPA CORE ENGINE | Modelos e avaliação | Planejado |
| EPA SENTINEL | Verificações temporais e integridade | Protótipo |
| EPA LEDGER | Cadeia local de auditoria | Protótipo |

**Stack:** Python + DuckDB + Parquet; Rails + Hotwire e MLflow planejados para integrações posteriores.

## Execução rápida

```bash
python -m pip install -e ".[dev,research]"
pytest -q
python -m epa.genesis.generate --output data/demo --students 100 --seed 20261029
```

`data/demo` conterá Parquet e manifesto SHA-256; outputs nunca são sobrescritos.

> A matriz em `examples/atlas.demo.json` é **inteiramente ilustrativa**. A BNCC orienta a estrutura, mas ainda não foi importada nem validada habilidade por habilidade. Não confundir esse exemplo com um currículo MEC verificado.

## Referências internas

- [Catálogo de componentes](docs/nomenclature/catalog.md)
- [ADRs](docs/adr/README.md)
- [Modelo de ameaças](docs/security/threat-model.md)
- [Contrato Atlas/Genesis](docs/architecture/atlas-genesis.md)
- [Protocolo de validação](docs/research/validation-protocol.md)

**Segurança:** não comitar registros reais, senhas, secrets ou artefatos não verificados. A verificação de hash isoladamente não comprova origem. Sem permissão de publicação no MVP.
