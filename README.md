# EduPredict Analytics — EPA Research Platform

Plataforma de pesquisa para análise longitudinal e validação científica de modelos educacionais.

> **Status:** fundação experimental v0.1. Não há modelos validados, proteções criptográficas implantadas nem garantias de segurança demonstradas.

## Componentes

| Componente | Escopo |
| --- | --- |
| EPA ATLAS | Registro curricular e referências versionadas |
| EPA GENESIS | Geração longitudinal de dados sintéticos |
| EPA CORE ENGINE | Features, experimentos e modelos científicos |
| EPA SENTINEL | Políticas de integridade e segurança de execução |
| EPA LEDGER | Proveniência, auditoria e evidências |

**Stack definida:** Rails + Hotwire (aplicação futura), Python científico, DuckDB + Parquet, MLflow. O banco operacional e a infraestrutura distribuída continuam sujeitos a ADR técnico.

## Primeira entrega

Este repositório contém a primeira fatia executável de **EPA SENTINEL**:

- esquema de manifesto de entrada com digest SHA-256;
- verificação da integridade de um arquivo;
- verificação de dependências temporais declaradas;
- regra fail-closed para evidência insuficiente;
- decisão de política PERMIT / DENY / UNKNOWN;
- testes automatizados.

**Importante:** os manifestos atualmente não são assinados e suas dependências são autodeclaradas; um originador malicioso pode falsificar esses dados. Esta versão **não é uma barreira completa** nem deve processar dados pessoais reais.

### Executar localmente

```bash
python -m pip install -e ".[dev]"
pytest -q
python -m epa.sentinel.cli verify --manifest examples/manifest.sample.json --root .
```

O exemplo tem um digest placeholder e, propositalmente, deve falhar até que seja apontado para um artefato real com digest calculado.

## Documentação

- [Catálogo de componentes](docs/nomenclature/catalog.md)
- [ADRs](docs/adr/README.md)
- [Modelo de ameaças](docs/security/threat-model.md)
- [Contratos e estados](docs/architecture/contracts.md)
- [Critérios de validação](docs/research/validation-protocol.md)

## Desenvolvimento seguro

Não comitar registros escolares reais, chaves, tokens, datasets sensíveis ou artefatos de modelos desconhecidos. A branch de implementação deve passar por revisão antes de integrar à principal.
