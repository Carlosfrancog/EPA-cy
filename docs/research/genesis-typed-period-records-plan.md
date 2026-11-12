# GENESIS Rust — Typed Period Records (fase 1)

## Objetivo

Remover a construção de `serde_json::Value` do caminho de geração e escrita nativa da entidade **`period_records`**, responsável por 5,4 milhões de linhas no benchmark de 25.000 estudantes. As demais entidades permanecem como `serde_json::Value` nesta fase, por terem participação muito menor no volume. `generate-jsonl` mantém saída JSON pela conversão tipada no adaptador de interoperabilidade.

## Alterações

- `records.rs`: `PeriodRecord` com 16 campos tipados, `GeneratedRow` e `generate_typed_rows`; RNG, ordenação, arredondamento e fórmulas mantidos. `generate_rows` compatibiliza o caminho legado convertendo o registro tipado somente quando JSONL é solicitado.
- `native_parquet.rs`: caminho rápido para `period_records`, com buffers de `PeriodRecord` e construção de arrays Arrow diretamente, sem `serde_json::Value` para os registros bimestrais; os demais arquivos seguem usando conversão JSON → Arrow.
- Não modifica ATLAS, Python, MAPA, LUPA, manifesto ou formato lógico esperado dos cinco arquivos Parquet.

## Gates antes do merge

1. Cargo `test --locked` + compilação `--release` e CI verde.
2. Paridade **EXCEPT ALL** com Python v3 em 120/500/2000 estudantes e ao menos duas seeds, conforme recursos locais; nunca comparar hashes dos próprios Parquet como substituto de conteúdo lógico.
3. Comparação antes/depois com mesma máquina, seed `20261029`, catálogo, `row_group_rows=4096`: 5k/10k/25k, com três repetições quando possível, capturando mediana de tempo, RSS amostrado e tamanho.
4. Auditoria DuckDB (17 checks) em qualquer novo dataset de 25k; a versão antiga já passou nesses checks.
5. Checar saída JSONL por seed e formato sem regressões.

## Precauções

- A nova representação não garante speedup; a cópia de strings por linha e formação dos arrays ainda possui custos. Medir antes de afirmar benefício.
- Não comparar tempos entre builds de debug e release nem diretórios gerados em armazenamento diferente.
- Somente `period_records` é livre de `serde_json::Value` no caminho nativo nesta fase. O restante virá depois da paridade.
- Não executar treino ML como parte desta alteração; são trilhas independentes.
