# EduPredict Analytics — EPA Research Platform

Laboratório experimental para análise longitudinal de educação. **Os dados e resultados atuais são sintéticos e não foram validados empiricamente.**

## Componentes EPA

| Nome | Papel | Estado |
| --- | --- | --- |
| EPA ATLAS | Catálogo curricular | Demonstração sintética |
| EPA GENESIS | Geração longitudinal | Gerador DuckDB + Parquet |
| EPA CORE ENGINE | Modelos | Baselines e relatório JSON |
| EPA SENTINEL | Verificações e políticas | Protótipo não autenticado |
| EPA LEDGER | Auditoria de hashes | Protótipo local |

## Executar o laboratório local

Requisitos: Ruby 3.3, Rails (Bundler), Python 3.11+ e dependências instaladas.

```bash
bundle install
python3 -m pip install -e ".[dev,research]"
bundle exec rails db:prepare
bundle exec rails server -b 127.0.0.1
```

Abra **http://127.0.0.1:3000/experiments**. Escolha modelo e seed e clique em **Executar experimento**.

A primeira execução gera automaticamente a demo com 500 alunos sintéticos, se ainda não houver dataset local. Cada run grava seu JSON e digests na tabela `experiment_runs`; resultados são apresentados após execução real do Python. A seleção de modelo é destaque na UI; os três baselines são treinados e comparados pelo CLI.

Caso o executável Python tenha outro nome:

```bash
EPA_PYTHON_EXECUTABLE=.venv/bin/python bundle exec rails server -b 127.0.0.1
```

O job runner é **local, não durável**; não é adequado para produção pública ou dados reais.

## Testes e capturas da interface real

```bash
pytest -q
bundle exec rails db:prepare
bundle exec rails test
```

O workflow Rails gera capturas do aplicativo iniciado no runner do GitHub Actions e as publica como artifact `epa-laboratory-screenshots` quando a etapa de screenshots é concluída.

## Restrições

- Sem acesso web público a jobs: ação de execução só aceita requisições locais em desenvolvimento/teste.
- Sem autenticação/RBAC, MLS/MLflow, assinatura de proveniência ou isolamento em container.
- Sem dados de alunos reais; a grade no Atlas é ilustrativa e não representa importação homologada da BNCC.
- A predição experimental é `média anual do próximo ano >= 6`, diferente de M1/M2/M3 e evasão.

[ADRs](docs/adr/README.md) · [Atlas/Genesis](docs/architecture/atlas-genesis.md) · [Core Engine](docs/research/core-engine-v0.md).
