# GENESIS Rust — primeira etapa de escala até 100.000 estudantes

## Objetivo

Remover o limite artificial de 2.000 estudantes **do caminho Rust**, preservando geração determinística e gravação Parquet em lotes (`row_group_rows`). Isso permite medir volumes acima do limite suportado atualmente pelo benchmark comparativo Python v3. **Não significa que 100.000 estudantes já tenham sido executados ou validados.**

## Mudanças

- `engines/genesis-rs/src/records.rs`: `Config.validate()` aceita `1..=100000` estudantes; mantém limites de ano, escolas, turmas e seeds. Teste unitário aceita 100.000, rejeita 100.001/zero.
- A geração usa `generate_rows` via callback sem acumular os registros da população inteira: cada entidade possui buffer de no máximo `row_group_rows` `serde_json::Value` antes de converter para um `RecordBatch` Arrow e gravar Parquet.
- `tools/benchmark_genesis_rust_scale.py`: executa **somente o motor Rust**, medindo tempo e RSS amostrado do processo, conferindo contagens esperadas de cada entidade, hashes SHA-256 e metadados do manifesto. Preserva arquivos existentes; relatório `benchmark.json` com status `PASS/FAIL`.
- Mantém `tools/benchmark_genesis.py` com limite 2.000 para comparação justa, pois outras implementações Python têm limites próprios. Testes de paridade com Python acima de 2.000 **não fazem parte desta etapa**.

## Lotes recomendados

Após CI verde e merge, começar com uma verificação pequena e subir gradualmente:

```powershell
git switch develop
git pull origin develop
cargo test --locked --manifest-path engines/genesis-rs/Cargo.toml

python tools/benchmark_genesis_rust_scale.py --students 5000 --seed 20261029
python tools/benchmark_genesis_rust_scale.py --students 10000 --seed 20261029
```

**Não executar 100.000 estudantes antes de avaliar tempo, memória e espaço em disco nos lotes menores.** Com o catálogo de referência: cada estudante produz 216 registros bimestrais. Em 5.000 estudantes são ~1.080.000 registros bimestrais; em 10.000 são ~2.160.000; em 100.000 seriam ~21.600.000. Esses valores são **projeções pela fórmula**, não resultados medidos.

Arquivos: `data/rust-scale-<id>/benchmark.json`, diretório `dataset/` e logs de execução. O código não sobrescreve relatórios ou datasets existentes.

## Critérios de aceitação

1. CI Rust verde; teste de limites e testes golden vector existentes aprovados.
2. Escala 5k/10k com `status=PASS`, cinco arquivos Parquet, manifesto íntegro, contagens esperadas e hashes por arquivo verificados.
3. Analisar RSS amostrado, tempo por registro, tamanho total e variação de memória entre as escalas. O processo mantém buffers limitados por entidade, mas **não garante RSS constante**: encoder Parquet, alocações internas, caches e sistema operacional influenciam.
4. Antes de ampliar para 50k/100k, conferir espaço livre, tempo estimado e integridade dos dados em SQL DuckDB com consultas agregadas (não materializar dezenas de milhões de linhas como listas Python).
5. A validação inicial acima de 2k comprova **integridade de saída** (hash/contagem), não paridade linha a linha nem correção estatística do gerador. Construir teste de prefixo determinístico contra 2k e ensaios cruzados posteriormente.

## Próximas melhorias de desempenho

- Separar fase de geração matemática e fase de compressão/escrita, com profiling para identificar gargalo efetivo.
- Reduzir alocações removendo `serde_json::Value` no caminho nativo, mantendo JSONL somente para interoperabilidade.
- Testar codec ZSTD, dictionary encoding e diferentes row groups com métricas de escrita **e leitura**.
- Avaliar limite de espaço, cancelamento, retomada determinística e processamento particionado antes de volumes extremos.
- Escala de dados sintéticos não implica validade externa ou maior qualidade preditiva do MAPA.

## Reprodutibilidade

Fixar a seed 20261029, o SHA256 do catálogo e o commit do código; registrar Windows, Python/Rust, versão Cargo e capacidade de hardware. Compilação release acontece **fora** do tempo do processo gerador. Uma rodada por escala é um teste exploratório, não comparação com intervalo de confiança.

**Escopo estrito:** não mexer em MAPA, LUPA ou na rotina de treinamento nesta etapa.
