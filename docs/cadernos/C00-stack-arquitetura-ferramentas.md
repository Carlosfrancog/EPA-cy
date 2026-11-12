# C00 — Arquitetura, stack e ferramentas do EduPredict Analytics

**Versão:** 0.1 — levantamento auditado em `develop`, 12/11/2026.  
**Tipo:** caderno tecnológico / materiais e métodos (artigo v0.3).  
**Escopo:** descrição da implementação observável, não proposta de funcionalidades ainda não existentes.  
**Classificação dos dados atuais:** `SYNTHETIC`. **Não há comprovação de eficácia preditiva em estudantes reais.**

## 00.1 — Perguntas do caderno

1. Quais tecnologias sustentam cada componente EPA e qual problema técnico resolvem?
2. Como o dado sintético passa por geração, armazenamento, auditoria, modelagem e apresentação?
3. Quais contratos e limites impedem confundir infraestrutura experimental com sistema escolar em produção?
4. Quais condições permitem reproduzir o ambiente, testes e benchmarks no artigo?

## 00.2 — Arquitetura observada

```text
ATLAS (examples/atlas.demo.json; currículo ilustrativo)
    |
    v
GENESIS (Python v2/v3 + Rust nativo)
    |  cinco entidades / Parquet / manifest SHA-256
    +--------------------------+
    |                          |
    v                          v
DuckDB / auditoria       MAPA / CORE ENGINE (Python)
  hashes, FKs,             snapshots N1/N2/N3, modelos,
  domínios                 splits por estudante, métricas
                               |
                               +----> LUPA (importância por permutação)
                               |
                               +----> JSON de resultados / MLflow opcional
                                          |
                                          v
                        Rails 8 / Hotwire / SQLite
                        UI e orquestração LOCAL experimental
```

**Importante:** as setas mostram os caminhos implementados **ou previstos pelo contrato**. O caminho MAPA de snapshots usa atualmente `read_verified_v2` em `epa/core_engine/student_timeline.py`, que exige o schema GENESIS **v2**; o formato `epa.genesis.dataset.rust_native.v1` não pode ser assumido como entrada direta compatível sem adaptador/testes. O backend Rails mantém também um benchmark longitudinal anterior com alvo diferente, segundo o README e ADR-010. Não representar esses fluxos como uma pipeline única de treinamento em grande escala já homologada.

## 00.3 — Inventário tecnológico fundamentado

| Camada | Tecnologia / restrição observada | Evidência no repositório | Estado e papel |
|---|---|---|---|
| Interface web | Ruby 3.3 em CI; Rails `~> 8.0`; Hotwire: Turbo, Stimulus, Importmap; Puma, Propshaft | `Gemfile`, `config/importmap.rb`, `config/routes.rb`, workflow Rails | Protótipo navegável e execução local; não homologado para exposição pública |
| Persistência operacional | SQLite `>=2.1` | `Gemfile`, `config/database.yml` | Registros de execução local, distinto dos datasets acadêmicos |
| Ciência de dados | Python `>=3.11`; pacote `epa-research 0.3.0` | `pyproject.toml` | Geração auxiliar, engenharia de atributos, modelos, validação |
| Machine learning | scikit-learn `>=1.5,<2`, NumPy `>=1.26,<3` | `pyproject.toml`, `epa/core_engine/mapa.py` | Dummy, Regressão Logística, Random Forest; MLP em experimento separado |
| Analítica SQL | DuckDB `>=1.2,<2` | `pyproject.toml`, `epa/genesis/parquet_deep_audit.py` | Consultas, integridade semântica, contagens e comparações `EXCEPT ALL` |
| Intercâmbio colunar | PyArrow `>=17,<30` (extra streaming) | `pyproject.toml`, `epa/genesis/v3.py` | Geração Python v3 e leitura/escrita Arrow/Parquet |
| Gerador de alto desempenho | Rust 2021, crate `genesis-rs 0.1.0` | `engines/genesis-rs/Cargo.toml` | Dados longitudinais sintéticos determinísticos, Parquet nativo |
| Bibliotecas Rust | `serde 1`, `serde_json 1`, `sha2 0.10`, `arrow-array 57`, `arrow-schema 57`, `parquet 57` | `engines/genesis-rs/Cargo.toml` | Tipagem, catálogo, integridade SHA-256, Arrow e persistência |
| Rastreamento ML | `mlflow>=3,<4` (extra tracking) | `pyproject.toml`, `epa/core_engine/mapa_tracking.py` | Adaptador **opcional** para métricas agregadas do MAPA; não presumir servidor operacional |
| Algoritmos adicionais | `xgboost>=2.1,<4` (extra boosting) | `pyproject.toml` | Dependência opcional disponível; **não** comprova benchmark científico do algoritmo |
| Testes | `pytest>=8,<10` e `cargo test --locked`; Rails tests | `pyproject.toml`, workflow Rust, workflow Rails | Regressão Python/Rust/Rails, golden vectors |
| CI/CD | GitHub Actions, Ubuntu/Windows Rust; Rails ubuntu-24.04 | `.github/workflows/genesis-rust-parity.yml`, `.github/workflows/rails-ui.yml` | Testes e capturas de tela; execução GitHub Actions não implica produção |
| Benchmark | `psutil>=5.9,<8`, Rust release, amostragem RSS | `pyproject.toml`, `tools/benchmark_genesis_rust_scale.py` | Medição de engenharia local; RSS observado não é pico garantido |

As faixas acima são **restrições declaradas**, não um inventário das versões instaladas nas máquinas. O lockfile Cargo pode especificar versões exatas; outros componentes precisam de um registro de execução do ambiente para garantir reprodutibilidade bit a bit.

## 00.4 — Componentes e maturidade

- **ATLAS:** catálogo curricular de demonstração; não equivale a dados oficiais BNCC homologados. `examples/atlas.demo.json`; `docs/architecture/atlas-genesis.md`.
- **GENESIS:** versões Python e Rust com artefatos Parquet e manifesto. O caminho Rust possui geração em lotes; a otimização tipada de `period_records` substitui `serde_json::Value` **somente nessa entidade**. `engines/genesis-rs/src/records.rs`, `native_parquet.rs`.
- **MAPA / CORE ENGINE:** benchmark supervisionado `approved/recovery/failed` para cortes N1/N2/N3, splits `GroupShuffleSplit` por estudante, atributos temporais e métricas agregadas. `epa/core_engine/mapa.py`. O baseline antigo de **média anual do ano seguinte >=6** é outra tarefa e precisa ficar separado do artigo de três classes.
- **LUPA:** `permutation_importance` no holdout, medindo sensibilidade de F1 e **não causalidade**. `epa/core_engine/lupa.py`.
- **SENTINEL / LEDGER:** há protótipos e ADRs; **não** alegar política assinada, autorização operacional ou auditoria integrada completa. `README.md`, `docs/adr/README.md`, `docs/adr/010-laboratory-orchestration.md`.
- **Rails Laboratory:** UI server-rendered, `ActiveJob async` local volátil, `Open3.capture3` para subprocessos com argumentos definidos, SQLite operacional. Sem autenticação/RBAC ou workers duráveis prontos para produção. `docs/adr/010-laboratory-orchestration.md`.
- **Dataset real:** uma futura importação longitudinal exigirá contrato de dados, autorização adequada, minimização de identificadores e segregação explícita de dados reais e sintéticos; não publicar históricos pessoais no GitHub.

## 00.5 — Contratos e reprodutibilidade

| Contrato | Verificação/ação |
|---|---|
| Proveniência | Registrar commit, SHA-256 do catálogo, seed, versão do gerador e schema do manifesto |
| Parquet | Verificar cinco entidades, contagens e SHA-256 de cada arquivo |
| Semântica | Auditoria DuckDB de chaves, FKs, notas/frequência, área/série e classificação sintética |
| Paridade | `EXCEPT ALL` de todas as tabelas entre implementações; é diferente de comparar tamanho/hash dos arquivos |
| Temporalidade | Dados disponíveis até N1/N2/N3; rótulo futuro não participa das features |
| Generalização | Split agrupado por identidade de estudante e comparação multi-seed/coortes independentes |
| Segurança | Ambiente local isolado, sem exposição pública; dados reais somente sob contrato e controle de acesso |
| Evidência | Relatórios imutáveis JSON, scripts e tabelas com origem rastreável |

### Comandos verificáveis

```powershell
python --version
rustc --version
cargo --version
ruby --version
bundle --version

python -m pip install -e ".[dev,research,streaming,benchmark]"
python -m pytest -q
cargo test --locked --manifest-path engines/genesis-rs/Cargo.toml
cargo build --locked --release --manifest-path engines/genesis-rs/Cargo.toml

# Execução LOCAL do laboratório web (depende de Ruby, Bundler e SQLite)
bundle install
bundle exec rails db:prepare
bundle exec rails test
```

O ambiente de benchmark informado no laboratório Windows foi Windows 11, Python 3.13.3, oito CPUs lógicas; compilação Rust release. Repetir medições e registrar versão do binário, contexto da máquina, row group, cache e tempo.

## 00.6 — Resultados de engenharia já observados (não inferir ML)

Os relatórios informados pelo executor local mostram o GENESIS Rust processando 25.000 estudantes e 5.400.000 registros bimestrais. Antes da tipagem, `114.4065632 s`; após a primeira tipagem de `period_records`, `64.8283327 s` e `71.1902481 s` (mediana `68.0092904 s`, redução observada de aproximadamente 40,55% em relação à única rodada anterior). Comparação DuckDB `EXCEPT ALL` para as cinco entidades: zero diferenças; auditoria adicional reportou `PASS`.

Limites: um teste da implementação anterior e dois da nova, hardware/cache sem controle experimental, RSS amostrado. Não afirmar causalidade estatisticamente estabelecida, equivalência de datasets reais ou maior acurácia de modelos. Esses números entram no artigo como **benchmark de engenharia**, não como resultado preditivo.

## 00.7 — Decisões e alternativas

- **Rails/Hotwire vs SPA:** monorepo e interface simples para revisão dos resultados, com menor acoplamento ao código Python. ADR-001 e ADR-009.
- **SQLite vs banco operacional distribuído:** adequado ao protótipo local, não uma decisão de escalabilidade multiusuário. ADR-010.
- **DuckDB/Parquet vs planilhas/CSV:** análise colunar, arquivo de troca e SQL direto para múltiplos milhões de registros; avaliar performance com testes, não só alegações genéricas. ADR-002.
- **Rust vs Python na geração:** Rust como motor de alta escala, Python como referência lógica e ambiente de modelos. Evidência de paridade e benchmark é requisito, não opcional.
- **MLflow:** disponível como adaptador opcional; adoção integral depende de ensaio de rastreamento reproduzível e armazenamento/controle adequados.

## 00.8 — Lacunas identificadas e tarefas

1. **Bridge GENESIS Rust → snapshots MAPA:** `read_verified_v2` exige schema v2 e materializa linhas em listas Python. Para os 5,4 milhões de registros Rust, precisamos contrato/adapter de formatos e pipeline de features com memória controlada, com equivalência funcional.
2. **Cadernos experimentais C01–C10:** especificar notebooks reexecutáveis, não somente texto, com relatórios JSON/Parquet e tabela exportável para o artigo v0.3.
3. **Versions/lock:** capturar versões reais executadas e registrar hashes do ambiente, inclusive Python e Ruby, conforme disponíveis.
4. **Separação científica:** não combinar a tarefa binária longitudinal legada e o desfecho triclasse MAPA como se fossem uma única avaliação; documentar diferenças.
5. **Segurança e dados reais:** UI local, sem autenticação ou execução pública. Implantar governança antes de importar históricos reais.
6. **Métricas:** latência, RSS, escalabilidade, paridade e checks semânticos são engenharia; macro-F1, recall por classe e calibração são avaliação preditiva; não misturar os argumentos.

## 00.9 — Mapeamento para o artigo

- **Materiais e Métodos:** arquitetura modular, dados sintéticos, bibliotecas e ambientes, persistência, splits e protocolo de auditoria.
- **Resultados de engenharia:** benchmarks Rust tipado/JSON, 25k estudantes, paridade e auditorias, com limitações de amostragem.
- **Resultados científicos separados:** MAPA em coortes independentes, comparação de modelos, SENTINEL e LUPA; apenas após gerar evidências adequadas.
- **Ameaças à validade:** gerador sintético, comparação de hardware, dependências, falta de validação em escolas reais.

## 00.10 — Fontes primárias do inventário

`pyproject.toml`; `Gemfile`; `config/database.yml`; `config/importmap.rb`; `config/routes.rb`; `engines/genesis-rs/Cargo.toml`; `engines/genesis-rs/Cargo.lock`; `epa/core_engine/mapa.py`; `epa/core_engine/lupa.py`; `epa/core_engine/student_timeline.py`; `epa/core_engine/mapa_tracking.py`; `epa/genesis/v3.py`; `epa/genesis/parquet_deep_audit.py`; `tools/compare_genesis_parquet.py`; `.github/workflows/genesis-rust-parity.yml`; `.github/workflows/rails-ui.yml`; `docs/adr/README.md`; `docs/adr/001-research-platform.md`; `docs/adr/009-rails-ui.md`; `docs/adr/010-laboratory-orchestration.md`; `README.md`.

Este inventário é uma fotografia do código consultado em `develop` em 12/11/2026. Se a branch avançar, reexecutar o caderno e atualizar a base documental.
