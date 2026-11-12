# GENESIS-RS — etapa de otimização do caminho nativo (callback de linhas)

## Objetivo técnico

A implementação anterior executava `records::generate() → JSONL serializado → parser JSON → ArrowWriter` dentro do mesmo processo Rust. O novo caminho é `records::generate_rows() → valores estruturados → ArrowWriter`. O comando `generate-jsonl` permanece compatível com a saída anterior.

**Limite importante:** esta etapa elimina a serialização textual, o buffer JSONL e o parsing de volta ao Rust, mas **ainda materializa linhas em `serde_json::Value`**. Não confundir com um writer inteiramente tipado. Os cálculos aleatórios, as fórmulas e a estrutura dos datasets permanecem inalterados.

## Validação geral de release antes de aceitar mudanças

Na raiz do repositório, depois que este PR passar no CI e for integrado:

```powershell
git switch develop
git pull origin develop
cargo test --locked --manifest-path engines/genesis-rs/Cargo.toml
python -m pytest -q
python -m pip install -e ".[dev,research,streaming,benchmark]"
python tools/check_genesis_rust_stream.py --students 10 --seed 42
python tools/check_genesis_rust_stream.py --students 10 --seed 20261029
python tools/benchmark_genesis.py --students 120 --seed 20261029 --warmups 1 --repeats 5
```

A suíte do GitHub executa a equivalência dos arquivos Parquet do Rust nativo e da v3 Python, em Windows e Linux, com hashes, contagens e `EXCEPT ALL`. **Não fazer merge se houver erro de paridade.** Os testes locais acima devem gerar novos diretórios `data/bench-...` e não modificam os datasets anteriores.

## Baseline observada antes desta otimização

`docs/research/genesis-benchmark-campaign-120-2026-11-12.md`: Rust nativo mediana **1,0054583 s**, RSS máximo amostrado **19.365.888 bytes**, total Parquet **288.755 bytes** para 120 estudantes, seed 20261029, 1 aquecimento e 3 rodadas medidas.

A nova implementação **ainda não tem speedup medido no hardware do usuário**. Comparações com a baseline histórica são exploratórias: variar número de repetições, temperatura, carga e estado de cache altera os resultados.

## Próxima campanha mais ampla

Executar em sequência, após comprovar sucesso da campanha de 120 alunos e verificar recursos locais:

```powershell
python tools/benchmark_genesis.py --students 500 --seed 20261029 --warmups 1 --repeats 5
python tools/benchmark_genesis.py --students 1000 --seed 20261029 --warmups 1 --repeats 5
python tools/benchmark_genesis.py --students 2000 --seed 20261029 --warmups 1 --repeats 5
```

**Observação:** o benchmark completo roda quatro motores, inclusive Python v2 com DuckDB, e pode ficar bastante demorado em 2000 alunos. Avaliar espaço e duração antes de iniciar; `--engines python_v3_pyarrow rust_native_parquet` permite um teste focado com a mesma verificação de paridade. A opção Python v3 deve aparecer primeiro.

Enviar `benchmark.json` (de cada tamanho) para revisão antes de registrar novos resultados acadêmicos. Também comparar bytes Parquet e RSS; a meta é reduzir trabalho sem degradar integridade, leitura ou custo de armazenamento.

## Critérios de aceite e ADR futuro

- Paridade cruzada dos dados, em múltiplas seeds e Windows/Linux.
- Nenhuma alteração dos contratos de saída ou manifesto sem versionamento.
- Medição antes/depois de tempo, RSS e bytes, com parâmetros rastreáveis.
- Investigar `serde_json::Value` / construção de batches Arrow; adicionar caminho integralmente tipado apenas depois de comprovar ganho.
- Em paralelo, executar profiling das consultas Rails/SQLite e DuckDB.
- A escolha de Rust nativo como motor principal do GENESIS é uma **decisão de projeto baseada na campanha disponível**, não uma afirmação de velocidade universal.
