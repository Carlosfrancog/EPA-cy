# GENESIS — Protocolo de benchmark reproduzível (v1)

**Situação:** instrumento implementado; nenhum ganho de desempenho é afirmado sem execução registrada no hardware-alvo.

## Motores avaliados

| Identificador | Gerador | Persistência | Possível sobrecarga |
| --- | --- | --- | --- |
| `python_v2_duckdb` | Python MT19937 | inserções DuckDB + COPY Parquet | criação de linhas em memória; inserção via `executemany` |
| `python_v3_pyarrow` | Python MT19937 | PyArrow streaming + ZSTD | Python e serialização de registros |
| `rust_pyarrow_bridge` | Rust MT19937 | JSONL subprocesso → Python/PyArrow | IPC, parsing JSON, processo Python |
| `rust_native_parquet` | Rust MT19937 | ArrowWriter Parquet em Rust | adaptação JSON intra-processo |

O comparador de referência é sempre **Python v3**. A versão 2 permanece limitada a até 2.000 alunos para este estudo. Todos os motores usam o mesmo catálogo, seed e estudantes. São produzidos cinco arquivos Parquet; a igualdade é verificada com SHA-256 por arquivo e `EXCEPT ALL` em ambas as direções, sem exigir hashes físicos idênticos.

## Execução no Windows — PowerShell

Na raiz do repositório:

```powershell
python -m pip install -e ".[dev,research,streaming,benchmark]"
cargo build --locked --release --manifest-path engines/genesis-rs/Cargo.toml
python tools/benchmark_genesis.py --students 120 --seed 20261029 --warmups 1 --repeats 3
```

O instrumento compila o Rust antes de medir, excluindo o build das amostras. Cria novo diretório sob `data/bench-<id>` para cada execução e **nunca apaga ou sobrescreve** resultados. A saída inclui `benchmark.json`, datasets Parquet e logs de `stdout`/`stderr`.

Cenários comparáveis sugeridos: 30, 120, 500, 1.000 e 2.000 alunos. Não executar uma campanha enorme de uma vez sem verificar RAM e espaço livre. Os resultados devem registrar modelo de CPU, RAM, sistema, disco, Python, Rust, dependências, concorrência e consumo de recursos externos. Não declarar produtividade relativa a partir de uma única rodada.

## O que é medido

- Tempo total real (`perf_counter_ns`) do processo gerador, incluindo inicialização e I/O, excluindo compilação prévia e verificação de paridade.
- Memória RSS observada por amostragem de 25 ms, somando processo e filhos vivos. **Amostragem não é pico absoluto garantido.**
- Tamanho físico de cada Parquet e total, com hashes conferidos.
- Mediana, mínimo, máximo e p95 interpolado; aquecimentos ficam fora das estatísticas.
- `PASS` somente se todas as entidades forem logicamente idênticas à referência.

Pontos não medidos nesta versão: consumo de energia, CPU por processo, tempo exclusivo de escrita, velocidade de armazenamento, confiança estatística, temperatura, cache de sistema e throughput de rede. Compressão/row group não são idênticos entre os quatro motores; diferenças de tamanho não provam superioridade intrínseca do algoritmo.

### Fórmulas

Para tempos observados `t_i` de uma implementação, com `n` repetições:

```text
mediana = median(t_1, ..., t_n)
speedup(A sobre B) = mediana(B) / mediana(A)
throughput = registros bimestrais / tempo_total
p95 = quantil linear interpolado da amostra
```

Um fator de aceleração só pode ser apresentado com unidade, definição explícita das operações comparadas, hardware, quantidade de estudantes, seed e número de rodadas. Não comparar somente tempo de computação de uma implementação contra tempo completo de geração/gravação de outra.

## Próximas consultas e estratégia de investigação

- Instrumentar o SQLite/Rails com contagem de queries, log e `EXPLAIN QUERY PLAN`, inspecionando possíveis N+1 e filtros sem índice.
- Analisar o `SELECT * FROM read_parquet(?)` do leitor GENESIS/MAPA, separando filtragem seletiva, projeção de colunas, scan total e materialização.
- Investigar os custos de `duckdb.executemany` da v2 e uso do `EXPLAIN ANALYZE`.
- Correlacionar consultas, volumes de linhas/bytes, custo do banco e custo de preparação do MAPA antes de decidir índices ou reescritas.

## Integridade científica

Somente **dados sintéticos**. O benchmark não é prova de que modelos predizem evasão ou aprovação em escolas reais. Registrar separadamente evidências de engenharia, validade interna do experimento e validade externa.
