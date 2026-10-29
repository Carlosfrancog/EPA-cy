# EduPredict Analytics — EPA Research Platform

Plataforma experimental de pesquisa educacional. **Não há modelos validados em dados reais nem controles completos para dados pessoais.**

## Componentes

| Nome | Papel | Estado |
| --- | --- | --- |
| EPA ATLAS | Catálogo curricular | Demo sintética |
| EPA GENESIS | Históricos longitudinais em Parquet | Protótipo |
| EPA CORE ENGINE | Modelos e benchmarks | Baseline sintético |
| EPA SENTINEL | Verificações e políticas | Protótipo |
| EPA LEDGER | Auditoria e evidências | Protótipo |

## Interface Rails navegável

Stack: Rails 8, Hotwire (Turbo), importmap e CSS próprio. O Rails é apenas a UI por enquanto: **não executa modelos a partir da web**.

```bash
bundle install
bundle exec rails s
```

Acesse `http://localhost:3000`. Navegação: Visão geral, Datasets, Experimentos, Modelos, Integridade, Arquitetura.

## Pipeline científico local

Python 3.11+, DuckDB, Parquet, scikit-learn:

```bash
python -m pip install -e ".[dev,research]"
pytest -q
python -m epa.genesis.generate --output data/demo --students 500 --seed 20261029
python -m epa.core_engine.cli --dataset data/demo/academic_history.parquet --output data/demo/report.json
```

Após gerar o dataset, a tela **Datasets** mostra o manifesto demonstrativo. A tela **Experimentos** apenas prepara a configuração, sem iniciar execução real. O CLI compara os três modelos independentemente do modelo destacado na UI.

As regras de geração e o catálogo são **sintéticos**, sem validação empírica. Nenhuma habilidade BNCC oficial foi importada ou verificada.

Referências: [ADRs](docs/adr/README.md), [Atlas/Genesis](docs/architecture/atlas-genesis.md), [Core Engine](docs/research/core-engine-v0.md).

**Não exponha a aplicação publicamente com dados reais antes de implementar autenticação e limites de autorização.**
